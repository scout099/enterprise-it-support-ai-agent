"""Pure state-transition checks for the Streamlit chat page."""

from apps.ui.chat_page import (
    _answer_citations,
    _replace_message_run,
    _response_state_updates,
)


def test_answer_citations_exclude_uncited_retrieval_candidates() -> None:
    cited = {
        "document_title": "VPN SOP",
        "document_version": 2,
        "section_title": "Client setup",
        "chunk_id": "cited-chunk",
    }
    run = {
        "final_response": {"citations": [cited]},
        "retrieved_evidence": [
            {"citation": cited},
            {"citation": {"document_title": "Uncited candidate", "chunk_id": "other"}},
        ],
    }

    assert _answer_citations(run) == [cited]


def test_new_response_clears_stale_ticket_and_refreshes_matching_trace() -> None:
    new_run = {"run_id": "run-2", "conversation_id": "conversation-1"}
    updates = _response_state_updates(
        {"run": new_run, "pending_confirmation": {"id": "confirmation-2"}}
    )
    messages = [
        {"role": "assistant", "payload": {"run": {"run_id": "run-1"}}},
        {"role": "assistant", "payload": {"run": {"run_id": "run-2", "tool_call_count": 0}}},
    ]
    refreshed = {"run_id": "run-2", "tool_call_count": 1}

    assert updates["ticket_number"] is None
    assert updates["latest_run"] == new_run
    assert _replace_message_run(messages, refreshed) is True
    assert messages[1]["payload"]["run"] == refreshed
    assert messages[0]["payload"]["run"]["run_id"] == "run-1"
