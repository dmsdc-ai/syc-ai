"""
ProductionPlannerAgent - 생산 스케줄링 에이전트

세영화학 생산 일정 최적화를 담당합니다.

목적함수:
1. 납기 지연 최소화
2. 셋업/교체 횟수 최소화
3. 폭 활용률 최대화
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 프레임워크 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.framework.agents import BaseAgent, AgentResponse
from scripts.optimizers.production_scheduler import (
    ProductionScheduler,
    Order,
    load_orders_from_csv,
    create_sample_orders,
    format_schedule_markdown,
    format_schedule_json,
)


class ProductionPlannerAgent(BaseAgent):
    """
    생산 스케줄링 에이전트

    주문 데이터를 분석하여 최적의 생산 일정을 수립합니다.
    frePPLe 연동 전 프로토타입으로 휴리스틱 알고리즘을 사용합니다.

    사용법:
        agent = ProductionPlannerAgent()
        result = await agent.invoke({
            'orders_file': 'data/orders.csv',
            'target_date': '2026-01-12',
            'output_dir': 'outputs/schedules'
        })
    """

    def __init__(self):
        super().__init__(name="ProductionPlanner")
        self.scheduler = ProductionScheduler()

    async def invoke(self, input_data: dict) -> AgentResponse:
        """
        생산 스케줄 생성

        Args:
            input_data: {
                'orders_file': str (CSV 파일 경로, 없으면 demo),
                'orders': list[dict] (직접 주문 데이터),
                'target_date': str (YYYY-MM-DD, 없으면 오늘),
                'output_dir': str (출력 디렉토리),
                'output_format': str ('md', 'json', 'both')
            }

        Returns:
            AgentResponse: 스케줄 결과
        """
        job_id = input_data.get('job_id', f"schedule-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.log_start(job_id, "생산 스케줄 생성 시작")

        try:
            # 1. 입력 검증
            orders_file = input_data.get('orders_file')
            orders_data = input_data.get('orders')
            target_date_str = input_data.get('target_date')
            output_dir = input_data.get('output_dir', 'outputs/schedules')
            output_format = input_data.get('output_format', 'both')

            # 2. 날짜 파싱
            if target_date_str:
                target_date = datetime.fromisoformat(target_date_str)
            else:
                target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            self.log_progress(job_id, f"대상 날짜: {target_date.strftime('%Y-%m-%d')}")

            # 3. 주문 로드
            if orders_data:
                # 직접 전달된 주문 데이터
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
                self.log_progress(job_id, f"직접 전달된 주문: {len(orders)}건")
            elif orders_file:
                orders = load_orders_from_csv(orders_file)
                self.log_progress(job_id, f"CSV 로드 완료: {len(orders)}건")
            else:
                orders = create_sample_orders()
                self.log_progress(job_id, f"데모 모드: 샘플 주문 {len(orders)}건")

            # 4. 스케줄러 초기화 및 실행
            self.scheduler = ProductionScheduler()
            self.scheduler.add_orders(orders)

            schedule = self.scheduler.create_schedule(target_date)
            schedule = self.scheduler.optimize_schedule(schedule)

            self.log_progress(job_id, f"스케줄 생성 완료: {schedule.summary()['total_orders']}건 배정")

            # 5. 결과 저장
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            date_str = target_date.strftime("%Y%m%d")
            saved_files = []

            if output_format in ['md', 'both']:
                md_path = output_path / f"schedule-{date_str}.md"
                md_path.write_text(format_schedule_markdown(schedule), encoding='utf-8')
                saved_files.append(str(md_path))

            if output_format in ['json', 'both']:
                json_path = output_path / f"schedule-{date_str}.json"
                import json
                json_path.write_text(
                    json.dumps(format_schedule_json(schedule), ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                saved_files.append(str(json_path))

            # 6. 결과 반환
            summary = schedule.summary()
            result_data = {
                'schedule_date': target_date.strftime('%Y-%m-%d'),
                'total_orders': summary['total_orders'],
                'unscheduled_orders': summary['unscheduled_orders'],
                'machines_used': summary['machines_used'],
                'total_setup_time_min': summary['total_setup_time_min'],
                'saved_files': saved_files,
                'schedule_json': format_schedule_json(schedule),
            }

            # 미배정 주문이 있으면 경고 포함
            if summary['unscheduled_orders'] > 0:
                self.log_progress(
                    job_id,
                    f"⚠️ 미배정 주문 {summary['unscheduled_orders']}건 - 용량 초과 또는 기계 비호환"
                )

            self.log_success(job_id, f"배정 {summary['total_orders']}건, 미배정 {summary['unscheduled_orders']}건")

            return AgentResponse.success(
                data=result_data,
                duration=self._get_duration()
            )

        except FileNotFoundError as e:
            self.log_error(job_id, str(e))
            return AgentResponse.error(
                message=f"주문 파일을 찾을 수 없습니다: {e}",
                duration=self._get_duration()
            )

        except Exception as e:
            self.log_error(job_id, str(e))
            return AgentResponse.error(
                message=f"스케줄 생성 실패: {e}",
                duration=self._get_duration()
            )

    def get_schedule_summary(self, schedule_json: dict) -> str:
        """스케줄 요약 문자열 생성"""
        summary = schedule_json.get('summary', {})
        return (
            f"📅 {schedule_json.get('schedule_date', 'N/A')}\n"
            f"✅ 배정: {summary.get('total_orders', 0)}건\n"
            f"❌ 미배정: {summary.get('unscheduled_orders', 0)}건\n"
            f"🏭 사용 기계: {summary.get('machines_used', 0)}대\n"
            f"⏱️ 총 셋업: {summary.get('total_setup_time_min', 0)}분"
        )


# ============================================================
# CLI 인터페이스
# ============================================================

async def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="생산 스케줄링 에이전트")
    parser.add_argument("--orders", type=str, help="주문 CSV 파일")
    parser.add_argument("--date", type=str, help="스케줄 날짜 (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="outputs/schedules", help="출력 디렉토리")
    parser.add_argument("--format", choices=["md", "json", "both"], default="both")
    parser.add_argument("--demo", action="store_true", help="데모 모드")

    args = parser.parse_args()

    agent = ProductionPlannerAgent()

    input_data = {
        'output_dir': args.output,
        'output_format': args.format,
    }

    if args.date:
        input_data['target_date'] = args.date

    if not args.demo and args.orders:
        input_data['orders_file'] = args.orders

    result = await agent.invoke(input_data)

    print("\n" + "="*60)
    if result.status == "success":
        print("✅ 스케줄 생성 성공!")
        print(agent.get_schedule_summary(result.data.get('schedule_json', {})))
        print(f"\n📁 저장된 파일:")
        for f in result.data.get('saved_files', []):
            print(f"   - {f}")
    else:
        print(f"❌ 실패: {result.error_message}")

    print(f"\n⏱️ 소요 시간: {result.duration}초")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
