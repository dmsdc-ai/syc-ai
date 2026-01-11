"""
DeliveryOptimizerAgent - 배송 경로 최적화 에이전트

세영화학 배송 비용 최소화를 담당합니다.

목적함수:
- 총 비용 최소화 (인건비 + 연료비 + 차량 감가상각)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# 프레임워크 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.framework.agents import BaseAgent, AgentResponse
from scripts.optimizers.delivery_router import (
    DeliveryRouter,
    Shipment,
    RoutePlan,
    load_shipments_from_csv,
    create_sample_shipments,
    format_plan_markdown,
    format_plan_json,
)


class DeliveryOptimizerAgent(BaseAgent):
    """
    배송 경로 최적화 에이전트

    출하 데이터를 분석하여 최적의 배송 경로와 배차를 계획합니다.
    PyVRP 연동 전 프로토타입으로 최근접 이웃 알고리즘을 사용합니다.

    사용법:
        agent = DeliveryOptimizerAgent()
        result = await agent.invoke({
            'shipments_file': 'data/shipments.csv',
            'target_date': '2026-01-12',
            'output_dir': 'outputs/routes'
        })
    """

    def __init__(self):
        super().__init__(name="DeliveryOptimizer")
        self.router = DeliveryRouter()

    async def invoke(self, input_data: dict) -> AgentResponse:
        """
        배송 경로 최적화

        Args:
            input_data: {
                'shipments_file': str (CSV 파일 경로, 없으면 demo),
                'shipments': list[dict] (직접 출하 데이터),
                'target_date': str (YYYY-MM-DD, 없으면 오늘),
                'output_dir': str (출력 디렉토리),
                'output_format': str ('md', 'json', 'both')
            }

        Returns:
            AgentResponse: 최적화된 경로 결과
        """
        job_id = input_data.get('job_id', f"route-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.log_start(job_id, "배송 경로 최적화 시작")

        try:
            # 1. 입력 파싱
            shipments_file = input_data.get('shipments_file')
            shipments_data = input_data.get('shipments')
            target_date_str = input_data.get('target_date')
            output_dir = input_data.get('output_dir', 'outputs/routes')
            output_format = input_data.get('output_format', 'both')

            # 2. 날짜 파싱
            if target_date_str:
                target_date = datetime.fromisoformat(target_date_str)
            else:
                target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            self.log_progress(job_id, f"배송 날짜: {target_date.strftime('%Y-%m-%d')}")

            # 3. 출하 로드
            if shipments_data:
                # 직접 전달된 출하 데이터
                shipments = [
                    Shipment(
                        shipment_id=s['shipment_id'],
                        customer=s['customer'],
                        address=s['address'],
                        weight_kg=float(s['weight_kg']),
                        pallets=int(s.get('pallets', 1)),
                        time_window=s.get('time_window', 'ANY'),
                        lat=float(s.get('lat', 0)),
                        lon=float(s.get('lon', 0)),
                    )
                    for s in shipments_data
                ]
                self.log_progress(job_id, f"직접 전달된 출하: {len(shipments)}건")
            elif shipments_file:
                shipments = load_shipments_from_csv(shipments_file)
                self.log_progress(job_id, f"CSV 로드 완료: {len(shipments)}건")
            else:
                shipments = create_sample_shipments()
                self.log_progress(job_id, f"데모 모드: 샘플 출하 {len(shipments)}건")

            # 4. 라우터 초기화 및 실행
            self.router = DeliveryRouter()
            self.router.add_shipments(shipments)

            plan = self.router.create_plan(target_date)
            plan = self.router.optimize_plan(plan)

            summary = plan.summary()
            self.log_progress(job_id, f"경로 생성 완료: {summary['total_shipments']}건 배송, {summary['vehicles_used']}대 차량")

            # 5. 결과 저장
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            date_str = target_date.strftime("%Y%m%d")
            saved_files = []

            if output_format in ['md', 'both']:
                md_path = output_path / f"route-{date_str}.md"
                md_path.write_text(format_plan_markdown(plan), encoding='utf-8')
                saved_files.append(str(md_path))

            if output_format in ['json', 'both']:
                json_path = output_path / f"route-{date_str}.json"
                json_path.write_text(
                    json.dumps(format_plan_json(plan), ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                saved_files.append(str(json_path))

            # 6. 결과 반환
            result_data = {
                'plan_date': target_date.strftime('%Y-%m-%d'),
                'total_shipments': summary['total_shipments'],
                'unassigned_shipments': summary['unassigned_shipments'],
                'vehicles_used': summary['vehicles_used'],
                'total_distance_km': summary['total_distance_km'],
                'total_cost': summary['total_cost'],
                'saved_files': saved_files,
                'plan_json': format_plan_json(plan),
            }

            # 비용 절감 추정 (기준선: 단순 왕복)
            baseline_cost = len(shipments) * 100000  # 개별 배송 시 평균 10만원 가정
            savings = baseline_cost - summary['total_cost']
            savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

            result_data['baseline_cost'] = baseline_cost
            result_data['savings'] = savings
            result_data['savings_pct'] = round(savings_pct, 1)

            if savings > 0:
                self.log_progress(job_id, f"💰 예상 절감: {savings:,}원 ({savings_pct:.1f}%)")

            if summary['unassigned_shipments'] > 0:
                self.log_progress(
                    job_id,
                    f"⚠️ 미배정 출하 {summary['unassigned_shipments']}건 - 용량 초과"
                )

            self.log_success(
                job_id,
                f"배송 {summary['total_shipments']}건, 비용 {summary['total_cost']:,}원"
            )

            return AgentResponse.success(
                data=result_data,
                duration=self._get_duration()
            )

        except FileNotFoundError as e:
            self.log_error(job_id, str(e))
            return AgentResponse.error(
                message=f"출하 파일을 찾을 수 없습니다: {e}",
                duration=self._get_duration()
            )

        except Exception as e:
            self.log_error(job_id, str(e))
            return AgentResponse.error(
                message=f"경로 최적화 실패: {e}",
                duration=self._get_duration()
            )

    def get_plan_summary(self, plan_json: dict) -> str:
        """배송 계획 요약 문자열"""
        summary = plan_json.get('summary', {})
        return (
            f"📅 {plan_json.get('plan_date', 'N/A')}\n"
            f"📦 배송: {summary.get('total_shipments', 0)}건\n"
            f"🚚 차량: {summary.get('vehicles_used', 0)}대\n"
            f"🛣️ 거리: {summary.get('total_distance_km', 0)}km\n"
            f"💰 비용: {summary.get('total_cost', 0):,}원"
        )


# ============================================================
# CLI 인터페이스
# ============================================================

async def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="배송 경로 최적화 에이전트")
    parser.add_argument("--shipments", type=str, help="출하 CSV 파일")
    parser.add_argument("--date", type=str, help="배송 날짜 (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="outputs/routes", help="출력 디렉토리")
    parser.add_argument("--format", choices=["md", "json", "both"], default="both")
    parser.add_argument("--demo", action="store_true", help="데모 모드")

    args = parser.parse_args()

    agent = DeliveryOptimizerAgent()

    input_data = {
        'output_dir': args.output,
        'output_format': args.format,
    }

    if args.date:
        input_data['target_date'] = args.date

    if not args.demo and args.shipments:
        input_data['shipments_file'] = args.shipments

    result = await agent.invoke(input_data)

    print("\n" + "="*60)
    if result.status == "success":
        print("✅ 경로 최적화 성공!")
        print(agent.get_plan_summary(result.data.get('plan_json', {})))

        if result.data.get('savings', 0) > 0:
            print(f"\n💰 예상 절감: {result.data['savings']:,}원 ({result.data['savings_pct']}%)")

        print(f"\n📁 저장된 파일:")
        for f in result.data.get('saved_files', []):
            print(f"   - {f}")
    else:
        print(f"❌ 실패: {result.error_message}")

    print(f"\n⏱️ 소요 시간: {result.duration}초")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
