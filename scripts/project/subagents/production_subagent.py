"""
ProductionPlannerSubAgent - 생산 스케줄링 서브에이전트

SupervisorAgent에서 호출되어 생산 일정을 최적화합니다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.framework.agents import BaseSubAgent, SubAgentContext, SubAgentResult
from scripts.optimizers.production_scheduler import (
    ProductionScheduler,
    Order,
    load_orders_from_csv,
    create_sample_orders,
    format_schedule_json,
)
from datetime import datetime


class ProductionPlannerSubAgent(BaseSubAgent):
    """
    생산 스케줄링 서브에이전트

    입력:
        - orders_file: CSV 파일 경로 (옵션)
        - orders: 주문 리스트 (옵션)
        - target_date: 스케줄 날짜

    출력:
        - schedule: 생성된 스케줄 JSON
        - summary: 요약 정보
    """

    def __init__(self):
        super().__init__(name="ProductionPlanner", cluster="operations")

    async def execute(self, ctx: SubAgentContext, input_data: dict) -> SubAgentResult:
        """생산 스케줄 생성"""
        try:
            # 입력 파싱
            orders_file = input_data.get('orders_file')
            orders_data = input_data.get('orders')
            target_date_str = input_data.get('target_date')

            # 날짜 파싱
            if target_date_str:
                target_date = datetime.fromisoformat(target_date_str)
            else:
                target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            self.logger.info(f"[{ctx.job_id}] 생산 스케줄 생성: {target_date.strftime('%Y-%m-%d')}")

            # 주문 로드
            if orders_data:
                orders = [
                    Order(
                        order_id=o['order_id'],
                        product_code=o['product_code'],
                        width_mm=o['width_mm'],
                        quantity_rolls=o['quantity_rolls'],
                        due_date=o['due_date'],
                        color=o.get('color', 'CLEAR'),
                        priority=o.get('priority', 1)
                    )
                    for o in orders_data
                ]
            elif orders_file:
                orders = load_orders_from_csv(orders_file)
            else:
                orders = create_sample_orders()

            # 스케줄 생성
            scheduler = ProductionScheduler()
            scheduler.add_orders(orders)

            schedule = scheduler.create_schedule(target_date)
            schedule = scheduler.optimize_schedule(schedule)

            schedule_json = format_schedule_json(schedule)
            summary = schedule.summary()

            self.logger.info(f"[{ctx.job_id}] 생산 배정: {summary['total_orders']}건")

            return SubAgentResult(
                agent_name=self.name,
                status="success",
                data={
                    'schedule': schedule_json,
                    'summary': summary,
                    'total_orders': summary['total_orders'],
                    'unscheduled': summary['unscheduled_orders'],
                }
            )

        except Exception as e:
            self.logger.error(f"[{ctx.job_id}] 생산 스케줄 실패: {e}")
            return SubAgentResult(
                agent_name=self.name,
                status="error",
                error=str(e)
            )
