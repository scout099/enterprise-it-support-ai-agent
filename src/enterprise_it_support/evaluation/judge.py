"""Optional advisory LLM Judge kept separate from deterministic metrics."""

import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from enterprise_it_support.evaluation.dataset import EvaluationCase
from enterprise_it_support.evaluation.models import AgentObservation
from enterprise_it_support.intelligence.model_gateway import ModelGateway, ModelMessage

JUDGE_PROMPT_VERSION = "agent-evaluation-judge-v1"
JUDGE_SYSTEM_PROMPT = """Score one Agent response against the supplied reference on a 0 to 1 scale.
This score is advisory, not ground truth. Do not override deterministic safety, authorization,
citation, tool, or workflow metrics. Return only the strict JSON object. Keep rationale_summary to
one short sentence and do not include hidden reasoning.
"""


class JudgeModelOutput(BaseModel):
    """Strict untrusted Judge output."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=1)
    rationale_summary: str = Field(min_length=1, max_length=300)


class JudgeCaseResult(BaseModel):
    """Advisory score plus exact model and prompt identity."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    score: float
    rationale_summary: str
    provider: str
    configured_model: str
    resolved_model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class EvaluationJudge(Protocol):
    """Optional asynchronous scoring seam."""

    async def score(
        self,
        case: EvaluationCase,
        observation: AgentObservation,
    ) -> JudgeCaseResult: ...


@dataclass
class ModelGatewayJudge:
    """Use a configured structured ModelGateway only when explicitly enabled."""

    gateway: ModelGateway

    async def score(
        self,
        case: EvaluationCase,
        observation: AgentObservation,
    ) -> JudgeCaseResult:
        payload = {
            "case_id": case.case_id,
            "user_query": case.user_query,
            "reference_answer": case.reference_answer,
            "expected_refusal": case.expected_refusal,
            "actual_status": observation.final_status,
            "actual_response": observation.final_response,
        }
        response = await self.gateway.generate_structured_response(
            messages=(
                ModelMessage(role="system", content=JUDGE_SYSTEM_PROMPT),
                ModelMessage(
                    role="user",
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ),
            response_schema=JudgeModelOutput,
            prompt_version=JUDGE_PROMPT_VERSION,
        )
        usage = response.metadata.usage
        return JudgeCaseResult(
            case_id=case.case_id,
            score=response.value.score,
            rationale_summary=response.value.rationale_summary,
            provider=response.metadata.provider,
            configured_model=response.metadata.configured_model,
            resolved_model=response.metadata.resolved_model,
            prompt_version=response.metadata.prompt_version,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        )
