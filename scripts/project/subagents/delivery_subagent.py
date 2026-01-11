"""
DeliveryOptimizerSubAgent - 배송 최적화 서브에이전트

SupervisorAgent에서 호출되어 배송 경로를 최적화합니다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.framework.agents import BaseSubAgent, SubAgentContext, SubAgentResult
from scripts.optimizers.delivery_router import (
    DeliveryRouter,
    Shipment,
    load_shipments_from_csv,
    create_sample_shipments,
    format_plan_json,
)
from datetime import datetime


class DeliveryOptimizerSubAgent(BaseSubAgent):
    """
    배송 최적화 서브에이전트

    입력:
        - shipments_file: CSV 파일 경로 (옵션)
        - shipments: 출하 리스트 (옵션)
        - target_date: 배송 날짜

    출력:
        - plan: 배송 계획 JSON
        - summary: 요약 정보
    """

    def __init__(self):
        super().__init__(name="DeliveryOptimizer", cluster="operations")

    async def execute(self, ctx: SubAgentContext, input_data: dict) -> SubAgentResult:
        """배송 경로 최적화"""
        try:
            # 입력 파싱
            shipments_file = input_data.get('shipments_file')
            shipments_data = input_data.get('shipments')
            target_date_str = input_data.get('target_date')

            # 날짜 파싱
            if target_date_str:
                target_date = datetime.fromisoformat(target_date_str)
            else:
                target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            self.logger.info(f"[{ctx.job_id}] 배송 경로 최적화: {target_date.strftime('%Y-%m-%d')}")

            # 출하 로드
            if shipments_data:
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
            elif shipments_file:
                shipments = load_shipments_from_csv(shipments_file)
            else:
                shipments = create_sample_shipments()

            # 경로 최적화
            router = DeliveryRouter()
            router.add_shipments(shipments)

            plan = router.create_plan(target_date)
            plan = router.optimize_plan(plan)

            plan_json = format_plan_json(plan)
            summary = plan.summary()

            self.logger.info(f"[{ctx.job_id}] 배송 배정: {summary['total_shipments']}건, 비용: {summary['total_cost']:,}원")

            return SubAgentResult(
                agent_name=self.name,
                status="success",
                data={
                    'plan': plan_json,
                    'summary': summary,
                    'total_shipments': summary['total_shipments'],
                    'total_cost': summary['total_cost'],
                    'vehicles_used': summary['vehicles_used'],
                }
            )

        except Exception as e:
            self.logger.error(f"[{ctx.job_id}] 배송 최적화 실패: {e}")
            return SubAgentResult(
                agent_name=self.name,
                status="error",
                error=str(e)
            )
