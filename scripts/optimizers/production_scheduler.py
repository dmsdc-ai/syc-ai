"""
세영화학 생산 스케줄링 프로토타입

목적함수:
1. 납기 지연 최소화 (최우선)
2. 셋업/교체 횟수 최소화
3. 폭 활용률 최대화

제약조건:
- 기계별 생산 가능 폭
- 1사이클 = 2롤
- 혼합생산 우선
- 기계별 조합 품목 수 제한 (최대 4개)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
import json
import csv
from pathlib import Path


# ============================================================
# 데이터 모델
# ============================================================

@dataclass
class Order:
    """주문 정보"""
    order_id: str
    product_code: str
    width_mm: int
    quantity_rolls: int
    due_date: datetime
    color: str = "CLEAR"  # CLEAR, COLOR
    priority: int = 1  # 1: 일반, 2: 급함, 3: 매우급함

    def __post_init__(self):
        if isinstance(self.due_date, str):
            self.due_date = datetime.fromisoformat(self.due_date)


@dataclass
class Machine:
    """기계 정보"""
    machine_id: str
    name: str
    width_min: int
    width_max: int
    speed_m_per_min: float = 30.0
    max_items_per_cycle: int = 4
    available: bool = True
    current_setup: Optional[str] = None  # 현재 셋업된 제품 코드


@dataclass
class ScheduleSlot:
    """스케줄 슬롯"""
    machine_id: str
    orders: list
    start_time: datetime
    end_time: datetime
    setup_time_min: int = 0

    @property
    def duration_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600


@dataclass
class Schedule:
    """일일 스케줄"""
    date: datetime
    slots: list = field(default_factory=list)
    unscheduled_orders: list = field(default_factory=list)

    def add_slot(self, slot: ScheduleSlot):
        self.slots.append(slot)

    def summary(self) -> dict:
        total_orders = sum(len(s.orders) for s in self.slots)
        total_setup_time = sum(s.setup_time_min for s in self.slots)
        machines_used = len(set(s.machine_id for s in self.slots))

        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "total_orders": total_orders,
            "unscheduled_orders": len(self.unscheduled_orders),
            "machines_used": machines_used,
            "total_setup_time_min": total_setup_time,
            "slots": len(self.slots)
        }


# ============================================================
# 설정
# ============================================================

# 기계 설정 (세영화학 기준 - 추후 .knowledge/machines/에서 로드)
MACHINES = [
    Machine("M1", "1호기", width_min=400, width_max=600),
    Machine("M2", "2호기", width_min=500, width_max=800),
    Machine("M3", "3호기", width_min=700, width_max=1200),
]

# 셋업 시간 매트릭스 (분)
SETUP_TIME_MATRIX = {
    ("CLEAR", "CLEAR"): 10,
    ("CLEAR", "COLOR"): 30,
    ("COLOR", "CLEAR"): 45,  # 세척 필요
    ("COLOR", "COLOR"): 20,
}

# 운영 시간
WORK_START_HOUR = 8
WORK_END_HOUR = 20
HOURS_PER_DAY = WORK_END_HOUR - WORK_START_HOUR


# ============================================================
# 스케줄러
# ============================================================

class ProductionScheduler:
    """생산 스케줄러"""

    def __init__(self, machines: list[Machine] = None):
        self.machines = machines or MACHINES
        self.orders: list[Order] = []

    def add_orders(self, orders: list[Order]):
        """주문 추가"""
        self.orders.extend(orders)

    def get_compatible_machines(self, order: Order) -> list[Machine]:
        """주문에 호환되는 기계 목록"""
        return [
            m for m in self.machines
            if m.available and m.width_min <= order.width_mm <= m.width_max
        ]

    def calculate_setup_time(self, from_color: str, to_color: str) -> int:
        """셋업 시간 계산"""
        return SETUP_TIME_MATRIX.get((from_color, to_color), 30)

    def estimate_production_time(self, order: Order, machine: Machine) -> float:
        """생산 시간 추정 (시간)"""
        # 1롤 = 약 1000m 가정, 1사이클 = 2롤
        meters_per_roll = 1000
        total_meters = order.quantity_rolls * meters_per_roll
        minutes = total_meters / machine.speed_m_per_min
        return minutes / 60

    def group_orders_by_width(self) -> dict:
        """폭 그룹별 주문 그룹핑"""
        groups = defaultdict(list)

        for order in self.orders:
            # 폭 그룹 결정 (100mm 단위)
            width_group = (order.width_mm // 100) * 100
            groups[width_group].append(order)

        return dict(groups)

    def sort_orders_for_scheduling(self, orders: list[Order]) -> list[Order]:
        """스케줄링을 위한 주문 정렬

        정렬 기준:
        1. 우선순위 (높을수록 먼저)
        2. 납기일 (빠를수록 먼저)
        3. 색상 (CLEAR → COLOR, 셋업 최소화)
        """
        return sorted(orders, key=lambda o: (
            -o.priority,
            o.due_date,
            0 if o.color == "CLEAR" else 1
        ))

    def create_schedule(self, target_date: datetime) -> Schedule:
        """스케줄 생성

        알고리즘:
        1. 납기일/우선순위로 정렬
        2. 폭 그룹별로 묶기
        3. 호환 기계에 할당
        4. 셋업 시간 고려하여 순서 최적화
        """
        schedule = Schedule(date=target_date)

        # 기계별 현재 상태 추적
        machine_states = {
            m.machine_id: {
                "current_time": datetime.combine(target_date, datetime.min.time().replace(hour=WORK_START_HOUR)),
                "current_color": m.current_setup or "CLEAR",
                "orders_today": []
            }
            for m in self.machines
        }

        # 주문 정렬
        sorted_orders = self.sort_orders_for_scheduling(self.orders)

        for order in sorted_orders:
            scheduled = False
            compatible_machines = self.get_compatible_machines(order)

            if not compatible_machines:
                schedule.unscheduled_orders.append(order)
                continue

            # 가장 적합한 기계 선택 (셋업 시간 최소화)
            best_machine = None
            best_setup_time = float('inf')

            for machine in compatible_machines:
                state = machine_states[machine.machine_id]
                setup_time = self.calculate_setup_time(state["current_color"], order.color)

                # 기계별 조합 품목 수 제한 확인
                if len(state["orders_today"]) >= machine.max_items_per_cycle:
                    continue

                if setup_time < best_setup_time:
                    best_setup_time = setup_time
                    best_machine = machine

            if best_machine is None:
                schedule.unscheduled_orders.append(order)
                continue

            # 스케줄 할당
            state = machine_states[best_machine.machine_id]
            production_time = self.estimate_production_time(order, best_machine)

            start_time = state["current_time"] + timedelta(minutes=best_setup_time)
            end_time = start_time + timedelta(hours=production_time)

            # 근무 시간 초과 확인
            work_end = datetime.combine(target_date, datetime.min.time().replace(hour=WORK_END_HOUR))
            if end_time > work_end:
                schedule.unscheduled_orders.append(order)
                continue

            # 슬롯 생성
            slot = ScheduleSlot(
                machine_id=best_machine.machine_id,
                orders=[order],
                start_time=start_time,
                end_time=end_time,
                setup_time_min=best_setup_time
            )
            schedule.add_slot(slot)

            # 상태 업데이트
            state["current_time"] = end_time
            state["current_color"] = order.color
            state["orders_today"].append(order.order_id)
            scheduled = True

        return schedule

    def optimize_schedule(self, schedule: Schedule) -> Schedule:
        """스케줄 최적화 (휴리스틱)

        - 같은 기계의 연속 슬롯 병합
        - 셋업 시간 최소화를 위한 순서 조정
        """
        # TODO: 추후 고급 최적화 알고리즘 구현
        # - 2-opt, 3-opt 지역 탐색
        # - 시뮬레이티드 어닐링
        # - 유전 알고리즘
        return schedule


# ============================================================
# 출력 포맷터
# ============================================================

def format_schedule_markdown(schedule: Schedule) -> str:
    """스케줄을 마크다운으로 포맷"""
    lines = [
        f"# 생산 스케줄 - {schedule.date.strftime('%Y-%m-%d')}",
        "",
        "## 요약",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
    ]

    summary = schedule.summary()
    lines.append(f"| 총 주문 | {summary['total_orders']}건 |")
    lines.append(f"| 미배정 | {summary['unscheduled_orders']}건 |")
    lines.append(f"| 사용 기계 | {summary['machines_used']}대 |")
    lines.append(f"| 총 셋업 시간 | {summary['total_setup_time_min']}분 |")

    lines.extend(["", "## 상세 스케줄", ""])

    # 기계별 그룹핑
    by_machine = defaultdict(list)
    for slot in schedule.slots:
        by_machine[slot.machine_id].append(slot)

    for machine_id, slots in sorted(by_machine.items()):
        machine_name = next((m.name for m in MACHINES if m.machine_id == machine_id), machine_id)
        lines.append(f"### {machine_name}")
        lines.append("")
        lines.append("| 시작 | 종료 | 주문ID | 제품 | 수량 | 셋업 |")
        lines.append("|------|------|--------|------|------|------|")

        for slot in sorted(slots, key=lambda s: s.start_time):
            for order in slot.orders:
                lines.append(
                    f"| {slot.start_time.strftime('%H:%M')} "
                    f"| {slot.end_time.strftime('%H:%M')} "
                    f"| {order.order_id} "
                    f"| {order.product_code} "
                    f"| {order.quantity_rolls}롤 "
                    f"| {slot.setup_time_min}분 |"
                )
        lines.append("")

    if schedule.unscheduled_orders:
        lines.extend(["## ⚠️ 미배정 주문", ""])
        for order in schedule.unscheduled_orders:
            lines.append(f"- {order.order_id}: {order.product_code} ({order.quantity_rolls}롤, 납기: {order.due_date.strftime('%Y-%m-%d')})")

    return "\n".join(lines)


def format_schedule_json(schedule: Schedule) -> dict:
    """스케줄을 JSON으로 포맷"""
    return {
        "schedule_date": schedule.date.strftime("%Y-%m-%d"),
        "summary": schedule.summary(),
        "slots": [
            {
                "machine_id": slot.machine_id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "setup_time_min": slot.setup_time_min,
                "orders": [
                    {
                        "order_id": o.order_id,
                        "product_code": o.product_code,
                        "width_mm": o.width_mm,
                        "quantity_rolls": o.quantity_rolls,
                        "color": o.color
                    }
                    for o in slot.orders
                ]
            }
            for slot in schedule.slots
        ],
        "unscheduled": [
            {
                "order_id": o.order_id,
                "product_code": o.product_code,
                "reason": "capacity_exceeded"
            }
            for o in schedule.unscheduled_orders
        ]
    }


# ============================================================
# 샘플 데이터 생성
# ============================================================

def create_sample_orders() -> list[Order]:
    """샘플 주문 데이터 생성"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return [
        Order("ORD-001", "PE-FILM-500", 500, 10, today + timedelta(days=1), "CLEAR", 2),
        Order("ORD-002", "PE-FILM-600", 600, 8, today + timedelta(days=1), "CLEAR", 1),
        Order("ORD-003", "PE-FILM-500", 500, 12, today + timedelta(days=2), "COLOR", 1),
        Order("ORD-004", "PE-FILM-800", 800, 6, today + timedelta(days=1), "CLEAR", 3),
        Order("ORD-005", "PE-FILM-1000", 1000, 4, today + timedelta(days=2), "CLEAR", 1),
        Order("ORD-006", "PE-FILM-600", 600, 15, today + timedelta(days=1), "COLOR", 2),
        Order("ORD-007", "PE-FILM-700", 700, 5, today + timedelta(days=3), "CLEAR", 1),
        Order("ORD-008", "PE-FILM-500", 500, 8, today + timedelta(days=1), "CLEAR", 1),
    ]


def load_orders_from_csv(filepath: str) -> list[Order]:
    """CSV 파일에서 주문 로드

    CSV 형식:
    order_id,product_code,width_mm,quantity_rolls,due_date,color,priority
    """
    orders = []
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"주문 파일을 찾을 수 없습니다: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            order = Order(
                order_id=row['order_id'],
                product_code=row['product_code'],
                width_mm=int(row['width_mm']),
                quantity_rolls=int(row['quantity_rolls']),
                due_date=row['due_date'],
                color=row.get('color', 'CLEAR'),
                priority=int(row.get('priority', 1))
            )
            orders.append(order)

    return orders


# ============================================================
# 메인
# ============================================================

def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="세영화학 생산 스케줄러")
    parser.add_argument("--date", type=str, help="스케줄 날짜 (YYYY-MM-DD)")
    parser.add_argument("--orders", type=str, help="주문 CSV 파일 경로")
    parser.add_argument("--output", type=str, default="outputs/schedules", help="출력 디렉토리")
    parser.add_argument("--format", choices=["md", "json", "both"], default="both", help="출력 포맷")
    parser.add_argument("--demo", action="store_true", help="데모 모드 (샘플 데이터)")

    args = parser.parse_args()

    # 날짜 설정
    if args.date:
        target_date = datetime.fromisoformat(args.date)
    else:
        target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 스케줄러 초기화
    scheduler = ProductionScheduler()

    # 주문 로드
    if args.demo or not args.orders:
        print("📦 데모 모드: 샘플 주문 데이터 사용")
        orders = create_sample_orders()
    else:
        print(f"📦 주문 파일 로드: {args.orders}")
        orders = load_orders_from_csv(args.orders)

    scheduler.add_orders(orders)
    print(f"📦 총 {len(orders)}건 주문 로드됨")

    # 스케줄 생성
    print(f"\n🔧 스케줄 생성 중... (날짜: {target_date.strftime('%Y-%m-%d')})")
    schedule = scheduler.create_schedule(target_date)

    # 최적화
    schedule = scheduler.optimize_schedule(schedule)

    # 결과 출력
    summary = schedule.summary()
    print(f"\n✅ 스케줄 생성 완료!")
    print(f"   - 배정: {summary['total_orders']}건")
    print(f"   - 미배정: {summary['unscheduled_orders']}건")
    print(f"   - 사용 기계: {summary['machines_used']}대")
    print(f"   - 총 셋업 시간: {summary['total_setup_time_min']}분")

    # 파일 저장
    import os
    os.makedirs(args.output, exist_ok=True)

    date_str = target_date.strftime("%Y%m%d")

    if args.format in ["md", "both"]:
        md_path = os.path.join(args.output, f"schedule-{date_str}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(format_schedule_markdown(schedule))
        print(f"\n📄 마크다운 저장: {md_path}")

    if args.format in ["json", "both"]:
        json_path = os.path.join(args.output, f"schedule-{date_str}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(format_schedule_json(schedule), f, ensure_ascii=False, indent=2)
        print(f"📄 JSON 저장: {json_path}")

    # 콘솔 출력
    print("\n" + "="*60)
    print(format_schedule_markdown(schedule))


if __name__ == "__main__":
    main()
