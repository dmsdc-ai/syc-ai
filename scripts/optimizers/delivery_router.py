"""
세영화학 배송 경로 최적화 프로토타입

목적함수:
- 총 비용 최소화 (인건비 + 연료비 + 차량 감가상각)

입력:
- 출하 목록 (배송지, 중량, 시간 제약)
- 차량 정보 (적재량, 비용)

출력:
- 최적 경로 및 배차 계획
"""

import math
import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from collections import defaultdict


# ============================================================
# 데이터 모델
# ============================================================

@dataclass
class Location:
    """위치 정보"""
    name: str
    address: str
    lat: float = 0.0
    lon: float = 0.0

    def distance_to(self, other: 'Location') -> float:
        """다른 위치까지 거리 (km) - Haversine 공식"""
        if self.lat == 0 or other.lat == 0:
            # 좌표가 없으면 임의 거리 반환 (테스트용)
            return 10.0

        R = 6371  # 지구 반경 (km)
        lat1, lon1 = math.radians(self.lat), math.radians(self.lon)
        lat2, lon2 = math.radians(other.lat), math.radians(other.lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c


@dataclass
class Shipment:
    """출하 정보"""
    shipment_id: str
    customer: str
    address: str
    weight_kg: float
    pallets: int = 1
    time_window: str = "ANY"  # AM, PM, ANY
    lat: float = 0.0
    lon: float = 0.0

    @property
    def location(self) -> Location:
        return Location(self.customer, self.address, self.lat, self.lon)


@dataclass
class Vehicle:
    """차량 정보"""
    vehicle_id: str
    name: str
    capacity_kg: float
    capacity_pallets: int
    cost_per_km: float = 200  # 원/km
    hourly_rate: float = 15000  # 시급
    fixed_cost: float = 50000  # 차량 사용 시 고정 비용 (감가상각)
    available: bool = True


@dataclass
class Route:
    """경로 정보"""
    vehicle_id: str
    stops: list = field(default_factory=list)  # List of Shipment
    total_distance_km: float = 0.0
    total_weight_kg: float = 0.0
    total_pallets: int = 0
    estimated_time_hours: float = 0.0

    @property
    def cost(self) -> float:
        """총 비용 계산"""
        vehicle = VEHICLES.get(self.vehicle_id)
        if not vehicle:
            return 0.0

        fuel_cost = self.total_distance_km * vehicle.cost_per_km
        labor_cost = self.estimated_time_hours * vehicle.hourly_rate
        fixed_cost = vehicle.fixed_cost if self.stops else 0

        return fuel_cost + labor_cost + fixed_cost


@dataclass
class RoutePlan:
    """배송 계획"""
    date: datetime
    routes: list = field(default_factory=list)
    unassigned: list = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(r.cost for r in self.routes)

    @property
    def total_distance(self) -> float:
        return sum(r.total_distance_km for r in self.routes)

    def summary(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "total_shipments": sum(len(r.stops) for r in self.routes),
            "unassigned_shipments": len(self.unassigned),
            "vehicles_used": len([r for r in self.routes if r.stops]),
            "total_distance_km": round(self.total_distance, 1),
            "total_cost": int(self.total_cost),
        }


# ============================================================
# 설정
# ============================================================

# 공장 위치 (세영화학 - 가상 좌표)
DEPOT = Location("세영화학", "경기도 화성시", 37.2, 127.0)

# 차량 설정
VEHICLES = {
    "V1": Vehicle("V1", "5톤_1", 5000, 10, 200, 15000, 50000),
    "V2": Vehicle("V2", "5톤_2", 5000, 10, 200, 15000, 50000),
    "V3": Vehicle("V3", "11톤", 11000, 20, 350, 18000, 80000),
}

# 평균 속도 (km/h)
AVERAGE_SPEED = 40

# 배송당 평균 하차 시간 (분)
UNLOAD_TIME_MIN = 15


# ============================================================
# 라우터
# ============================================================

class DeliveryRouter:
    """배송 경로 최적화"""

    def __init__(self, depot: Location = None, vehicles: dict = None):
        self.depot = depot or DEPOT
        self.vehicles = vehicles or VEHICLES
        self.shipments: list[Shipment] = []

    def add_shipments(self, shipments: list[Shipment]):
        """출하 추가"""
        self.shipments.extend(shipments)

    def calculate_distance_matrix(self) -> dict:
        """거리 매트릭스 계산"""
        locations = [self.depot] + [s.location for s in self.shipments]
        matrix = {}

        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                key = (i, j)
                if i == j:
                    matrix[key] = 0
                else:
                    matrix[key] = loc1.distance_to(loc2)

        return matrix

    def nearest_neighbor(self, shipments: list[Shipment], vehicle: Vehicle) -> Route:
        """최근접 이웃 알고리즘으로 경로 생성"""
        route = Route(vehicle_id=vehicle.vehicle_id)
        remaining = shipments.copy()
        current_location = self.depot

        while remaining:
            # 적재 가능한 shipment 필터
            feasible = [
                s for s in remaining
                if (route.total_weight_kg + s.weight_kg <= vehicle.capacity_kg and
                    route.total_pallets + s.pallets <= vehicle.capacity_pallets)
            ]

            if not feasible:
                break

            # 가장 가까운 shipment 선택
            nearest = min(feasible, key=lambda s: current_location.distance_to(s.location))
            route.stops.append(nearest)
            route.total_weight_kg += nearest.weight_kg
            route.total_pallets += nearest.pallets
            route.total_distance_km += current_location.distance_to(nearest.location)

            current_location = nearest.location
            remaining.remove(nearest)

        # 공장으로 복귀 거리 추가
        if route.stops:
            route.total_distance_km += current_location.distance_to(self.depot)
            route.estimated_time_hours = (
                route.total_distance_km / AVERAGE_SPEED +
                len(route.stops) * UNLOAD_TIME_MIN / 60
            )

        return route

    def create_plan(self, target_date: datetime) -> RoutePlan:
        """배송 계획 생성

        알고리즘:
        1. 시간 제약이 있는 shipment 우선 처리 (AM > PM > ANY)
        2. 무거운 shipment 우선 (큰 차량에 할당)
        3. 최근접 이웃 알고리즘으로 경로 생성
        """
        plan = RoutePlan(date=target_date)

        # 시간 제약으로 정렬 (AM 먼저)
        sorted_shipments = sorted(
            self.shipments,
            key=lambda s: (
                0 if s.time_window == "AM" else (1 if s.time_window == "PM" else 2),
                -s.weight_kg  # 무거운 것 먼저
            )
        )

        remaining = sorted_shipments.copy()

        # 차량별 경로 생성
        for vehicle_id, vehicle in sorted(
            self.vehicles.items(),
            key=lambda x: -x[1].capacity_kg  # 큰 차량 먼저
        ):
            if not vehicle.available or not remaining:
                continue

            route = self.nearest_neighbor(remaining, vehicle)

            if route.stops:
                plan.routes.append(route)
                # 할당된 shipment 제거
                for stop in route.stops:
                    if stop in remaining:
                        remaining.remove(stop)

        # 미할당 shipment
        plan.unassigned = remaining

        return plan

    def optimize_plan(self, plan: RoutePlan) -> RoutePlan:
        """계획 최적화 (2-opt 등)

        TODO: 고급 최적화 알고리즘 구현
        - 2-opt: 경로 내 교차 제거
        - Or-opt: 연속 노드 이동
        - 차량 간 shipment 교환
        """
        return plan


# ============================================================
# 출력 포맷터
# ============================================================

def format_plan_markdown(plan: RoutePlan) -> str:
    """계획을 마크다운으로 포맷"""
    lines = [
        f"# 배송 계획 - {plan.date.strftime('%Y-%m-%d')}",
        "",
        "## 요약",
        "",
        "| 항목 | 값 |",
        "|------|-----|",
    ]

    summary = plan.summary()
    lines.append(f"| 총 배송 | {summary['total_shipments']}건 |")
    lines.append(f"| 미배정 | {summary['unassigned_shipments']}건 |")
    lines.append(f"| 사용 차량 | {summary['vehicles_used']}대 |")
    lines.append(f"| 총 거리 | {summary['total_distance_km']}km |")
    lines.append(f"| 총 비용 | {summary['total_cost']:,}원 |")

    lines.extend(["", "## 차량별 경로", ""])

    for route in plan.routes:
        if not route.stops:
            continue

        vehicle = VEHICLES.get(route.vehicle_id)
        vehicle_name = vehicle.name if vehicle else route.vehicle_id

        lines.append(f"### {vehicle_name}")
        lines.append("")
        lines.append(f"- **총 거리**: {route.total_distance_km:.1f}km")
        lines.append(f"- **적재량**: {route.total_weight_kg:.0f}kg / {route.total_pallets}파렛트")
        lines.append(f"- **예상 시간**: {route.estimated_time_hours:.1f}시간")
        lines.append(f"- **비용**: {route.cost:,.0f}원")
        lines.append("")
        lines.append("| 순서 | 고객 | 주소 | 중량 |")
        lines.append("|:----:|------|------|-----:|")

        for i, stop in enumerate(route.stops, 1):
            lines.append(f"| {i} | {stop.customer} | {stop.address} | {stop.weight_kg:.0f}kg |")

        lines.append("")

    if plan.unassigned:
        lines.extend(["## ⚠️ 미배정 배송", ""])
        for shipment in plan.unassigned:
            lines.append(f"- {shipment.shipment_id}: {shipment.customer} ({shipment.weight_kg}kg)")

    return "\n".join(lines)


def format_plan_json(plan: RoutePlan) -> dict:
    """계획을 JSON으로 포맷"""
    return {
        "plan_date": plan.date.strftime("%Y-%m-%d"),
        "summary": plan.summary(),
        "routes": [
            {
                "vehicle_id": r.vehicle_id,
                "vehicle_name": VEHICLES.get(r.vehicle_id, Vehicle(r.vehicle_id, r.vehicle_id, 0, 0)).name,
                "total_distance_km": round(r.total_distance_km, 1),
                "total_weight_kg": r.total_weight_kg,
                "total_pallets": r.total_pallets,
                "estimated_time_hours": round(r.estimated_time_hours, 1),
                "cost": int(r.cost),
                "stops": [
                    {
                        "shipment_id": s.shipment_id,
                        "customer": s.customer,
                        "address": s.address,
                        "weight_kg": s.weight_kg,
                        "pallets": s.pallets,
                        "time_window": s.time_window,
                    }
                    for s in r.stops
                ]
            }
            for r in plan.routes if r.stops
        ],
        "unassigned": [
            {
                "shipment_id": s.shipment_id,
                "customer": s.customer,
                "reason": "capacity_exceeded"
            }
            for s in plan.unassigned
        ]
    }


# ============================================================
# 샘플 데이터
# ============================================================

def create_sample_shipments() -> list[Shipment]:
    """샘플 출하 데이터"""
    return [
        Shipment("SHP-001", "A사", "서울시 강남구", 800, 2, "AM", 37.5, 127.05),
        Shipment("SHP-002", "B사", "경기도 성남시", 500, 1, "AM", 37.4, 127.1),
        Shipment("SHP-003", "C사", "서울시 송파구", 1200, 3, "ANY", 37.5, 127.1),
        Shipment("SHP-004", "D사", "경기도 용인시", 2000, 4, "PM", 37.2, 127.2),
        Shipment("SHP-005", "E사", "인천시 남동구", 1500, 3, "ANY", 37.4, 126.7),
        Shipment("SHP-006", "F사", "경기도 안양시", 600, 1, "AM", 37.4, 126.9),
        Shipment("SHP-007", "G사", "서울시 영등포구", 900, 2, "ANY", 37.5, 126.9),
        Shipment("SHP-008", "H사", "경기도 수원시", 1800, 4, "PM", 37.3, 127.0),
        Shipment("SHP-009", "I사", "경기도 평택시", 2500, 5, "ANY", 37.0, 127.1),
        Shipment("SHP-010", "J사", "경기도 화성시", 400, 1, "AM", 37.2, 126.8),
    ]


def load_shipments_from_csv(filepath: str) -> list[Shipment]:
    """CSV에서 출하 로드"""
    shipments = []
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"출하 파일을 찾을 수 없습니다: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            shipment = Shipment(
                shipment_id=row['shipment_id'],
                customer=row['customer'],
                address=row['address'],
                weight_kg=float(row['weight_kg']),
                pallets=int(row.get('pallets', 1)),
                time_window=row.get('time_window', 'ANY'),
                lat=float(row.get('lat', 0)),
                lon=float(row.get('lon', 0)),
            )
            shipments.append(shipment)

    return shipments


# ============================================================
# 메인
# ============================================================

def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="세영화학 배송 경로 최적화")
    parser.add_argument("--date", type=str, help="배송 날짜 (YYYY-MM-DD)")
    parser.add_argument("--shipments", type=str, help="출하 CSV 파일")
    parser.add_argument("--output", type=str, default="outputs/routes", help="출력 디렉토리")
    parser.add_argument("--format", choices=["md", "json", "both"], default="both")
    parser.add_argument("--demo", action="store_true", help="데모 모드")

    args = parser.parse_args()

    # 날짜 설정
    if args.date:
        target_date = datetime.fromisoformat(args.date)
    else:
        target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 라우터 초기화
    router = DeliveryRouter()

    # 출하 로드
    if args.demo or not args.shipments:
        print("📦 데모 모드: 샘플 출하 데이터 사용")
        shipments = create_sample_shipments()
    else:
        print(f"📦 출하 파일 로드: {args.shipments}")
        shipments = load_shipments_from_csv(args.shipments)

    router.add_shipments(shipments)
    print(f"📦 총 {len(shipments)}건 출하 로드됨")

    # 계획 생성
    print(f"\n🚚 경로 최적화 중... (날짜: {target_date.strftime('%Y-%m-%d')})")
    plan = router.create_plan(target_date)
    plan = router.optimize_plan(plan)

    # 결과 출력
    summary = plan.summary()
    print(f"\n✅ 배송 계획 완료!")
    print(f"   - 배송: {summary['total_shipments']}건")
    print(f"   - 미배정: {summary['unassigned_shipments']}건")
    print(f"   - 사용 차량: {summary['vehicles_used']}대")
    print(f"   - 총 거리: {summary['total_distance_km']}km")
    print(f"   - 총 비용: {summary['total_cost']:,}원")

    # 파일 저장
    import os
    os.makedirs(args.output, exist_ok=True)

    date_str = target_date.strftime("%Y%m%d")

    if args.format in ["md", "both"]:
        md_path = os.path.join(args.output, f"route-{date_str}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(format_plan_markdown(plan))
        print(f"\n📄 마크다운 저장: {md_path}")

    if args.format in ["json", "both"]:
        json_path = os.path.join(args.output, f"route-{date_str}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(format_plan_json(plan), f, ensure_ascii=False, indent=2)
        print(f"📄 JSON 저장: {json_path}")

    # 콘솔 출력
    print("\n" + "="*60)
    print(format_plan_markdown(plan))


if __name__ == "__main__":
    main()
