"""Versioned, strictly validated Agent evaluation dataset contracts."""

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationCategory(StrEnum):
    """Phase 10 dataset categories with explicit reporting boundaries."""

    KNOWLEDGE_QUESTION = "knowledge_question"
    VPN_DIAGNOSIS = "vpn_diagnosis"
    OUTLOOK_DIAGNOSIS = "outlook_diagnosis"
    ACCOUNT_DIAGNOSIS = "account_diagnosis"
    TICKET_REQUEST = "ticket_request"
    HIGH_RISK_PERMISSION = "high_risk_permission"


class ExpectedDocument(BaseModel):
    """Stable human-maintainable identity for one expected knowledge document."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=500)


class ExpectedToolCall(BaseModel):
    """Exact registered tool name and deterministic argument contract."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any]


class EvaluationUserContext(BaseModel):
    """Only the bounded request context supplied to the local evaluation subject."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(default="employee-demo", min_length=1, max_length=128)
    user_role: str = Field(default="employee", min_length=1, max_length=100)
    business_justification: str | None = Field(default=None, min_length=10, max_length=2000)


class EvaluationCase(BaseModel):
    """One deterministic expected-versus-observed Agent behavior contract."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=100)
    category: EvaluationCategory
    user_query: str = Field(min_length=1, max_length=2000)
    user_context: EvaluationUserContext
    expected_intent: str = Field(min_length=1, max_length=100)
    expected_documents: list[ExpectedDocument] = Field(max_length=20)
    expected_tool_calls: list[ExpectedToolCall] = Field(max_length=20)
    expected_final_status: str = Field(min_length=1, max_length=100)
    prohibited_actions: list[str] = Field(min_length=1, max_length=30)
    reference_answer: str = Field(min_length=1, max_length=8000)
    expected_refusal: bool = False


class EvaluationDataset(BaseModel):
    """A versioned dataset whose declared category allocation is enforced."""

    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    category_requirements: dict[EvaluationCategory, int]
    cases: list[EvaluationCase] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def validate_dataset_integrity(self) -> "EvaluationDataset":
        case_ids = [case.case_id for case in self.cases]
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("Evaluation dataset case IDs must be unique")
        if not self.category_requirements:
            raise ValueError("Evaluation dataset must declare category requirements")
        if any(required < 0 for required in self.category_requirements.values()):
            raise ValueError("Evaluation category requirements cannot be negative")

        actual_counts = {
            category: sum(case.category is category for case in self.cases)
            for category in self.category_requirements
        }
        if actual_counts != self.category_requirements:
            raise ValueError(
                "Evaluation dataset category counts do not match requirements: "
                f"expected={self.category_requirements}, actual={actual_counts}"
            )
        if sum(self.category_requirements.values()) != len(self.cases):
            raise ValueError("Evaluation category requirements must account for every case")
        return self


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    """Load UTF-8 JSON and fail closed on malformed or incomplete cases."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise ValueError(f"Unable to load evaluation dataset: {path}") from exception
    return EvaluationDataset.model_validate(raw)


def dataset_sha256(path: Path) -> str:
    """Return the exact dataset artifact digest recorded in every run."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
