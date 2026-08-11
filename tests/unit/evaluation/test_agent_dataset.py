"""Strict validation tests for the versioned Phase 10 Agent dataset."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from enterprise_it_support.evaluation.dataset import (
    EvaluationCategory,
    EvaluationDataset,
    dataset_sha256,
    load_evaluation_dataset,
)

DATASET_PATH = Path("data/evaluation/agent_cases.json")


def test_initial_dataset_has_required_fields_and_exact_category_allocation() -> None:
    dataset = load_evaluation_dataset(DATASET_PATH)

    assert dataset.dataset_version == "phase-10-v1"
    assert len(dataset.cases) == 30
    assert dataset.category_requirements == {
        EvaluationCategory.KNOWLEDGE_QUESTION: 8,
        EvaluationCategory.VPN_DIAGNOSIS: 6,
        EvaluationCategory.OUTLOOK_DIAGNOSIS: 6,
        EvaluationCategory.ACCOUNT_DIAGNOSIS: 5,
        EvaluationCategory.TICKET_REQUEST: 3,
        EvaluationCategory.HIGH_RISK_PERMISSION: 2,
    }
    assert all(case.prohibited_actions for case in dataset.cases)
    assert len(dataset_sha256(DATASET_PATH)) == 64


def test_dataset_rejects_duplicate_case_ids_and_category_drift() -> None:
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw["cases"][1]["case_id"] = raw["cases"][0]["case_id"]

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        EvaluationDataset.model_validate(raw)

    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw["category_requirements"]["knowledge_question"] = 7
    with pytest.raises(ValidationError, match="category counts do not match"):
        EvaluationDataset.model_validate(raw)


def test_dataset_rejects_missing_required_field_and_extra_data(tmp_path: Path) -> None:
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    del raw["cases"][0]["reference_answer"]
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_evaluation_dataset(invalid_path)

    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    raw["cases"][0]["unexpected"] = "not allowed"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvaluationDataset.model_validate(raw)
