"""
FactorySupervisorAgent - 스마트팩토리 총괄 에이전트

생산 스케줄링과 배송 최적화를 통합 관리합니다.

아키텍처:
    FactorySupervisor
    └── OperationsCluster [PARALLEL]
        ├── ProductionPlannerSubAgent  # 생산 일정
        └── DeliveryOptimizerSubAgent  # 배송 경로
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.framework.agents import (
    BaseAgent,
    AgentResponse,
    ParallelExecutor,
    ExecutionStrategy,
    ExecutionPlan,
    SubAgentContext,
    SubAgentRegistry,
    ClusterResult,
)
from scripts.project.subagents import (
    ProductionPlannerSubAgent,
    DeliveryOptimizerSubAgent,
)


class FactorySupervisorAgent(BaseAgent):
    """
    스마트팩토리 총괄 에이전트

    생산과 배송을 병렬로 최적화하고 결과를 통합합니다.

    사용법:
        supervisor = FactorySupervisorAgent()
        result = await supervisor.invoke({
            'target_date': '2026-01-12',
            'orders_file': 'data/orders.csv',
            'shipments_file': 'data/shipments.csv',
        })
    """

    def __init__(self):
        super().__init__(name="FactorySupervisor")
        self.executor = ParallelExecutor(max_concurrent=2)
        self._init_subagents()

    def _init_subagents(self):
        """서브에이전트 초기화 및 등록"""
        self.production_subagent = ProductionPlannerSubAgent()
        self.delivery_subagent = DeliveryOptimizerSubAgent()

        SubAgentRegistry.clear()
        SubAgentRegistry.register(self.production_subagent)
        SubAgentRegistry.register(self.delivery_subagent)

    async def invoke(self, input_data: dict) -> AgentResponse:
        """
        통합 최적화 실행

        Args:
            input_data: {
                'target_date': str (YYYY-MM-DD),
                'orders_file': str (생산 주문 CSV),
                'orders': list[dict] (직접 주문 데이터),
                'shipments_file': str (출하 CSV),
                'shipments': list[dict] (직접 출하 데이터),
                'output_dir': str (출력 디렉토리),
                'mode': str ('all', 'production', 'delivery')
            }

        Returns:
            AgentResponse: 통합 결과
        """
        job_id = input_data.get('job_id', f"supervisor-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.log_start(job_id, "스마트팩토리 통합 최적화 시작")

        try:
            mode = input_data.get('mode', 'all')
            output_dir = input_data.get('output_dir', 'outputs')

            # 날짜 파싱
            target_date_str = input_data.get('target_date')
            if target_date_str:
                target_date = datetime.fromisoformat(target_date_str)
            else:
                target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            date_str = target_date.strftime('%Y-%m-%d')
            self.log_progress(job_id, f"대상 날짜: {date_str}")

            # 컨텍스트 생성
            ctx = SubAgentContext(
                job_id=job_id,
                parent_agent=self.name,
                cluster="operations"
            )

            # 실행할 서브에이전트 결정
            subagent_names = []
            if mode in ['all', 'production']:
                subagent_names.append("ProductionPlanner")
            if mode in ['all', 'delivery']:
                subagent_names.append("DeliveryOptimizer")

            # 병렬 실행 계획
            plan = ExecutionPlan(
                strategy=ExecutionStrategy.PARALLEL,
                subagents=subagent_names
            )

            self.log_progress(job_id, f"실행 모드: {mode} ({len(subagent_names)}개 서브에이전트)")

            # 병렬 실행
            cluster_result: ClusterResult = await self.executor.execute_plan(
                ctx=ctx,
                plan=plan,
                input_data=input_data
            )

            self.log_progress(
                job_id,
                f"클러스터 완료: 성공 {cluster_result.success_count}, 실패 {cluster_result.error_count}"
            )

            # 결과 수집
            result_data = {
                'target_date': date_str,
                'mode': mode,
                'execution_time': cluster_result.total_duration,
                'success_count': cluster_result.success_count,
                'error_count': cluster_result.error_count,
            }

            # 생산 결과
            production_result = cluster_result.results.get("ProductionPlanner")
            if production_result and production_result.status == "success":
                result_data['production'] = production_result.data
                self.log_progress(
                    job_id,
                    f"📦 생산: {production_result.data.get('total_orders', 0)}건 배정"
                )

            # 배송 결과
            delivery_result = cluster_result.results.get("DeliveryOptimizer")
            if delivery_result and delivery_result.status == "success":
                result_data['delivery'] = delivery_result.data
                self.log_progress(
                    job_id,
                    f"🚚 배송: {delivery_result.data.get('total_shipments', 0)}건, "
                    f"비용 {delivery_result.data.get('total_cost', 0):,}원"
                )

            # 통합 리포트 저장
            saved_files = await self._save_integrated_report(
                result_data, output_dir, target_date
            )
            result_data['saved_files'] = saved_files

            # 최종 상태 결정
            if cluster_result.error_count > 0:
                if cluster_result.success_count > 0:
                    self.log_success(job_id, "부분 성공")
                    return AgentResponse.partial_success(
                        data=result_data,
                        message=f"{cluster_result.error_count}개 실패",
                        duration=self._get_duration()
                    )
                else:
                    self.log_error(job_id, "모든 서브에이전트 실패")
                    return AgentResponse.error(
                        message="모든 서브에이전트 실패",
                        duration=self._get_duration(),
                        data=result_data
                    )

            self.log_success(job_id, "통합 최적화 완료")
            return AgentResponse.success(
                data=result_data,
                duration=self._get_duration()
            )

        except Exception as e:
            self.log_error(job_id, str(e))
            return AgentResponse.error(
                message=f"통합 최적화 실패: {e}",
                duration=self._get_duration()
            )

    async def _save_integrated_report(
        self,
        result_data: dict,
        output_dir: str,
        target_date: datetime
    ) -> list:
        """통합 리포트 저장"""
        saved_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        date_str = target_date.strftime("%Y%m%d")

        # JSON 리포트
        json_path = output_path / f"integrated-report-{date_str}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
        saved_files.append(str(json_path))

        # 마크다운 요약
        md_path = output_path / f"integrated-report-{date_str}.md"
        md_content = self._format_markdown_report(result_data)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        saved_files.append(str(md_path))

        return saved_files

    def _format_markdown_report(self, result_data: dict) -> str:
        """마크다운 리포트 생성"""
        lines = [
            f"# 스마트팩토리 통합 리포트",
            f"",
            f"**날짜**: {result_data.get('target_date', 'N/A')}",
            f"**실행 시간**: {result_data.get('execution_time', 0)}초",
            f"",
            "---",
            "",
        ]

        # 생산 요약
        production = result_data.get('production', {})
        if production:
            summary = production.get('summary', {})
            lines.extend([
                "## 📦 생산 스케줄",
                "",
                "| 항목 | 값 |",
                "|------|-----|",
                f"| 배정 주문 | {summary.get('total_orders', 0)}건 |",
                f"| 미배정 | {summary.get('unscheduled_orders', 0)}건 |",
                f"| 사용 기계 | {summary.get('machines_used', 0)}대 |",
                f"| 총 셋업 시간 | {summary.get('total_setup_time_min', 0)}분 |",
                "",
            ])

        # 배송 요약
        delivery = result_data.get('delivery', {})
        if delivery:
            summary = delivery.get('summary', {})
            lines.extend([
                "## 🚚 배송 계획",
                "",
                "| 항목 | 값 |",
                "|------|-----|",
                f"| 배송 건수 | {summary.get('total_shipments', 0)}건 |",
                f"| 사용 차량 | {summary.get('vehicles_used', 0)}대 |",
                f"| 총 거리 | {summary.get('total_distance_km', 0)}km |",
                f"| 총 비용 | {summary.get('total_cost', 0):,}원 |",
                "",
            ])

        # 통합 KPI
        lines.extend([
            "---",
            "",
            "## 📊 통합 KPI",
            "",
        ])

        prod_orders = production.get('summary', {}).get('total_orders', 0)
        prod_unscheduled = production.get('summary', {}).get('unscheduled_orders', 0)
        delivery_cost = delivery.get('summary', {}).get('total_cost', 0)

        if prod_orders + prod_unscheduled > 0:
            schedule_rate = prod_orders / (prod_orders + prod_unscheduled) * 100
            lines.append(f"- **생산 배정률**: {schedule_rate:.1f}%")

        if delivery_cost > 0:
            lines.append(f"- **배송 비용**: {delivery_cost:,}원")

        lines.extend([
            "",
            "---",
            f"*Generated by FactorySupervisorAgent*",
        ])

        return "\n".join(lines)


# ============================================================
# CLI 인터페이스
# ============================================================

async def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="스마트팩토리 통합 에이전트")
    parser.add_argument("--date", type=str, help="대상 날짜 (YYYY-MM-DD)")
    parser.add_argument("--orders", type=str, help="주문 CSV 파일")
    parser.add_argument("--shipments", type=str, help="출하 CSV 파일")
    parser.add_argument("--output", type=str, default="outputs", help="출력 디렉토리")
    parser.add_argument("--mode", choices=["all", "production", "delivery"], default="all")
    parser.add_argument("--demo", action="store_true", help="데모 모드")

    args = parser.parse_args()

    supervisor = FactorySupervisorAgent()

    input_data = {
        'output_dir': args.output,
        'mode': args.mode,
    }

    if args.date:
        input_data['target_date'] = args.date

    if not args.demo:
        if args.orders:
            input_data['orders_file'] = args.orders
        if args.shipments:
            input_data['shipments_file'] = args.shipments

    result = await supervisor.invoke(input_data)

    print("\n" + "="*70)
    print("🏭 스마트팩토리 통합 최적화 결과")
    print("="*70)

    if result.status == "success":
        print("✅ 성공!")
    elif result.status == "partial_success":
        print(f"⚠️ 부분 성공: {result.error_message}")
    else:
        print(f"❌ 실패: {result.error_message}")

    print(f"\n📅 날짜: {result.data.get('target_date', 'N/A')}")
    print(f"⏱️ 실행 시간: {result.data.get('execution_time', 0)}초")

    # 생산 결과
    production = result.data.get('production', {})
    if production:
        summary = production.get('summary', {})
        print(f"\n📦 생산 스케줄:")
        print(f"   - 배정: {summary.get('total_orders', 0)}건")
        print(f"   - 미배정: {summary.get('unscheduled_orders', 0)}건")
        print(f"   - 기계: {summary.get('machines_used', 0)}대")

    # 배송 결과
    delivery = result.data.get('delivery', {})
    if delivery:
        summary = delivery.get('summary', {})
        print(f"\n🚚 배송 계획:")
        print(f"   - 배송: {summary.get('total_shipments', 0)}건")
        print(f"   - 차량: {summary.get('vehicles_used', 0)}대")
        print(f"   - 비용: {summary.get('total_cost', 0):,}원")

    # 저장된 파일
    saved_files = result.data.get('saved_files', [])
    if saved_files:
        print(f"\n📁 저장된 파일:")
        for f in saved_files:
            print(f"   - {f}")

    print(f"\n⏱️ 총 소요 시간: {result.duration}초")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
