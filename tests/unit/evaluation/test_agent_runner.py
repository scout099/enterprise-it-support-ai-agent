"""Full dataset runner tests using a deterministic in-process subject."""

from pathlib import Path
from uuid import UUID

from enterprise_it_support.evaluation.dataset import (
    EvaluationCase,
    EvaluationCategory,
    load_evaluation_dataset,
)
from enterprise_it_support.evaluation.fixtures import EvaluationCorpusRetriever
from enterprise_it_support.evaluation.judge import JUDGE_PROMPT_VERSION, ModelGatewayJudge
from enterprise_it_support.evaluation.models import (
    AgentObservation,
    TokenUsageObservation,
    ToolCallObservation,
)
from enterprise_it_support.evaluation.runner import observed_tool_actions, run_evaluation
from enterprise_it_support.intelligence.model_gateway import FakeModelGateway
from enterprise_it_support.knowledge.retrieval import SearchFilters, UserContext
from enterprise_it_support.tools.contracts import ToolExecutionStatus


class PerfectFakeSubject:
    """Return contract-shaped observations without any external provider or database."""

    async def execute(self, case: EvaluationCase) -> AgentObservation:
        expected_titles = [document.title for document in case.expected_documents]
        chunk_ids = [f"chunk-{case.case_id}-{index}" for index, _ in enumerate(expected_titles)]
        evidence = [case.reference_answer for _ in expected_titles]
        citations = [] if case.expected_refusal else expected_titles
        citation_chunks = [] if case.expected_refusal else chunk_ids
        actual_actions = [f"tool:{tool.tool_name}" for tool in case.expected_tool_calls]
        if case.expected_final_status == "confirmation_required":
            actual_actions.append("proposed:create_ticket")
        return AgentObservation(
            case_id=case.case_id,
            category=case.category,
            actual_intent=case.expected_intent,
            retrieved_document_titles=expected_titles,
            retrieved_chunk_ids=chunk_ids,
            evidence_texts=evidence,
            citation_document_titles=citations,
            citation_chunk_ids=citation_chunks,
            tool_calls=[
                ToolCallObservation(
                    tool_name=tool.tool_name,
                    arguments=tool.arguments,
                    status="succeeded",
                    latency_ms=1,
                )
                for tool in case.expected_tool_calls
            ],
            final_status=case.expected_final_status,
            final_response={"answer": case.reference_answer},
            refused=(
                case.expected_refusal
                if case.category is EvaluationCategory.KNOWLEDGE_QUESTION
                else None
            ),
            claims=(
                [] if case.expected_refusal or not expected_titles else [case.reference_answer]
            ),
            actual_actions=actual_actions,
            steps=["intake", "finalize"],
            latency_ms=5,
            token_usage=TokenUsageObservation(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                model_calls=1,
            ),
            prompt_versions=["fake-prompt-v1"],
            model_names=["fake-model-v1"],
        )


async def test_complete_30_case_dataset_runs_without_real_api() -> None:
    dataset = load_evaluation_dataset(Path("data/evaluation/agent_cases.json"))

    execution = await run_evaluation(dataset, PerfectFakeSubject())

    assert len(execution.cases) == 30
    assert execution.metrics.agent["intent_accuracy"].value == 1
    assert execution.metrics.agent["tool_selection_accuracy"].value == 1
    assert execution.metrics.agent["tool_argument_accuracy"].value == 1
    assert execution.metrics.agent["workflow_completion_rate"].value == 1
    assert execution.metrics.agent["prohibited_action_rate"].value == 0
    assert execution.metrics.retrieval["recall_at_3"].value == 1
    assert execution.metrics.generation["citation_validity"].value == 1
    assert execution.metrics.system.token_usage.total_tokens == 450
    assert set(execution.category_metrics) == {category.value for category in EvaluationCategory}


async def test_optional_judge_is_separate_and_records_model_and_prompt_versions() -> None:
    dataset = load_evaluation_dataset(Path("data/evaluation/agent_cases.json"))
    gateway = FakeModelGateway(
        [],
        model_name="fake-judge-v2",
        response_factory=lambda _call: {
            "score": 0.6,
            "rationale_summary": "Advisory comparison only.",
        },
    )

    execution = await run_evaluation(
        dataset,
        PerfectFakeSubject(),
        judge=ModelGatewayJudge(gateway),
    )

    assert execution.metrics.agent["intent_accuracy"].value == 1
    assert len(execution.judge_results) == 30
    result = execution.judge_results[0]
    assert result.score == 0.6
    assert result.provider == "fake"
    assert result.resolved_model == "fake-judge-v2"
    assert result.prompt_version == JUDGE_PROMPT_VERSION


def test_observed_tool_actions_use_canonical_safety_vocabulary() -> None:
    actions = observed_tool_actions(
        tool_name="run_shell_command",
        status=ToolExecutionStatus.SUCCEEDED,
        has_side_effect=True,
    )

    assert set(actions) >= {
        "run_shell_command",
        "tool:run_shell_command",
        "shell_execution",
        "executed:run_shell_command",
        "side_effect_executed",
        "external_system_modified",
    }


async def test_evaluation_corpus_filter_is_applied_before_retrieval_ranking() -> None:
    allowed_id = UUID("10000000-0000-0000-0000-000000000001")

    class CapturingRetriever:
        received_filters: SearchFilters | None = None

        async def search(self, query, top_k, filters, user_context):
            self.received_filters = filters
            return ()

    wrapped = CapturingRetriever()
    retriever = EvaluationCorpusRetriever(wrapped, frozenset({allowed_id}))  # type: ignore[arg-type]

    await retriever.search("vpn", 5, SearchFilters(), UserContext(role="employee"))

    assert wrapped.received_filters is not None
    assert wrapped.received_filters.document_ids == frozenset({allowed_id})
