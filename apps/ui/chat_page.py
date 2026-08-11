"""IT Support Chat Streamlit page."""

from typing import Any

import pandas as pd
import streamlit as st

from apps.ui.client import APIError, ITSupportAPIClient


def render_chat_page(client: ITSupportAPIClient) -> None:
    st.title("IT Support Chat")
    st.caption("Local Mock demo · answers, diagnostics, tools, confirmation, ticket and feedback")
    _initialize_state()

    with st.sidebar:
        st.subheader("Simulated identity")
        actor_id = st.text_input("Actor ID", value=st.session_state.actor_id)
        role_options = ["employee", "it_support", "project_maintainer", "guest"]
        user_role = st.selectbox(
            "Role",
            options=role_options,
            index=role_options.index(st.session_state.user_role),
        )
        normalized_actor = actor_id.strip()
        if normalized_actor != st.session_state.actor_id or user_role != st.session_state.user_role:
            st.session_state.actor_id = normalized_actor
            st.session_state.user_role = user_role
            _reset_conversation()
            st.rerun()
        if st.button("New conversation"):
            _reset_conversation()
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_trace(message["payload"])

    pending = st.session_state.pending_confirmation
    waiting_for_action = bool(pending and pending.get("status") == "pending")
    if waiting_for_action:
        st.caption("Confirm or cancel the pending action before sending another message.")
    prompt = st.chat_input("Describe your IT issue", disabled=waiting_for_action)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            payload = client.respond(
                user_message=prompt,
                actor_id=st.session_state.actor_id,
                user_role=st.session_state.user_role,
                conversation_id=st.session_state.conversation_id,
            )
        except APIError as exception:
            st.error(f"{exception.code}: {exception}")
        else:
            run = payload["run"]
            for key, value in _response_state_updates(payload).items():
                st.session_state[key] = value
            content = _answer_text(run)
            st.session_state.messages.append(
                {"role": "assistant", "content": content, "payload": payload}
            )
            st.rerun()

    _render_pending_action(client)
    _render_feedback(client)


def _initialize_state() -> None:
    defaults = {
        "actor_id": "employee-demo",
        "user_role": "employee",
        "conversation_id": None,
        "messages": [],
        "latest_run": None,
        "pending_confirmation": None,
        "ticket_number": None,
        "feedback_submitted_for": None,
        "trace_refresh_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_conversation() -> None:
    for key, value in {
        "conversation_id": None,
        "messages": [],
        "latest_run": None,
        "pending_confirmation": None,
        "ticket_number": None,
        "feedback_submitted_for": None,
        "trace_refresh_error": None,
    }.items():
        st.session_state[key] = value


def _answer_text(run: dict[str, Any]) -> str:
    response = run.get("final_response") or {}
    for key in ("answer", "summary"):
        value = response.get(key)
        if value:
            return str(value)
    if run.get("missing_information"):
        return "Please provide: " + ", ".join(run["missing_information"])
    if run.get("escalation_reason"):
        return f"Escalated safely: {run['escalation_reason']}"
    error = run.get("error") or {}
    if error:
        return f"The request ended safely: {error.get('code', 'agent_error')}"
    return f"Agent finished with status: {run['status']}"


def _response_state_updates(payload: dict[str, Any]) -> dict[str, Any]:
    """Start a new run-scoped UI state without leaking an older Ticket."""
    run = payload["run"]
    return {
        "conversation_id": run.get("conversation_id"),
        "latest_run": run,
        "pending_confirmation": payload.get("pending_confirmation"),
        "ticket_number": None,
        "trace_refresh_error": None,
    }


def _answer_citations(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only citations selected by the validated final answer."""
    final_response = run.get("final_response") or {}
    citations = final_response.get("citations") or []
    return [item for item in citations if isinstance(item, dict)]


def _render_trace(payload: dict[str, Any]) -> None:
    run = payload["run"]
    status_columns = st.columns(4)
    status_columns[0].metric("Status", run["status"])
    status_columns[1].metric("Intent", run.get("intent") or "unknown")
    status_columns[2].metric("Steps", run["node_count"])
    status_columns[3].metric("Tool calls", run["tool_call_count"])

    citations = _answer_citations(run)
    if citations:
        with st.expander("Cited sources", expanded=True):
            for citation in citations:
                title = citation.get("document_title") or "Source"
                version = citation.get("document_version")
                section = citation.get("section_title") or "Unsectioned"
                chunk_id = citation.get("chunk_id")
                st.markdown(f"- **{title}** · version {version} · {section} · chunk `{chunk_id}`")

    tools = run.get("tool_executions") or []
    if tools:
        with st.expander("Executed tools and audit", expanded=True):
            frame = pd.DataFrame(
                [
                    {
                        "tool": item["tool_name"],
                        "status": item["status"],
                        "attempts": item["attempts"],
                        "latency_ms": item["latency_ms"],
                        "risk": item.get("risk_level"),
                        "side_effect": item.get("has_side_effect", False),
                        "error": item.get("error_code"),
                    }
                    for item in tools
                ]
            )
            st.dataframe(frame, hide_index=True, width="stretch")

    with st.expander("Agent state and node trace"):
        st.write(run.get("reasoning_summary"))
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "sequence": step["sequence_number"],
                        "node": step["node_name"],
                        "status": step["status"],
                        "latency_ms": step["latency_ms"],
                    }
                    for step in run.get("steps", [])
                ]
            ),
            hide_index=True,
            width="stretch",
        )


def _render_pending_action(client: ITSupportAPIClient) -> None:
    pending = st.session_state.pending_confirmation
    if not pending or pending.get("status") != "pending":
        if pending and pending.get("status") == "cancelled":
            st.info("Pending action cancelled. No change was executed.")
        elif pending and pending.get("status") == "failed":
            st.error(
                f"Pending action failed safely: {pending.get('error_code') or 'action_failed'}"
            )
        elif st.session_state.ticket_number:
            st.success(f"Ticket Number: {st.session_state.ticket_number}")
        elif pending and pending.get("status") == "executed":
            st.success("Confirmed action completed")
        if st.session_state.trace_refresh_error:
            st.warning(
                "Action completed, but its latest tool audit could not be refreshed: "
                f"{st.session_state.trace_refresh_error}"
            )
        return
    st.warning(pending["impact_summary"])
    st.json(pending["parameters_summary"], expanded=False)
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button("Confirm action", type="primary"):
        try:
            result = client.confirm(
                confirmation_id=pending["id"],
                actor_id=st.session_state.actor_id,
                user_role=st.session_state.user_role,
            )
        except APIError as exception:
            st.error(f"{exception.code}: {exception}")
        else:
            st.session_state.pending_confirmation = result
            observation = result.get("result") or {}
            st.session_state.ticket_number = observation.get("ticket_number")
            run = st.session_state.latest_run
            if run is not None:
                try:
                    refreshed_run = client.agent_run(
                        run_id=run["run_id"],
                        user_role=st.session_state.user_role,
                    )
                except APIError as exception:
                    st.session_state.trace_refresh_error = exception.code
                else:
                    st.session_state.latest_run = refreshed_run
                    _replace_message_run(st.session_state.messages, refreshed_run)
            st.rerun()
    if cancel_column.button("Cancel action"):
        try:
            result = client.cancel(
                confirmation_id=pending["id"],
                actor_id=st.session_state.actor_id,
                user_role=st.session_state.user_role,
            )
        except APIError as exception:
            st.error(f"{exception.code}: {exception}")
        else:
            st.session_state.pending_confirmation = result
            st.session_state.ticket_number = None
            st.rerun()


def _replace_message_run(messages: list[dict[str, Any]], run: dict[str, Any]) -> bool:
    """Refresh the matching assistant trace after a confirmed tool execution."""
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        payload = message.get("payload") or {}
        stored_run = payload.get("run") or {}
        if stored_run.get("run_id") == run.get("run_id"):
            payload["run"] = run
            return True
    return False


def _render_feedback(client: ITSupportAPIClient) -> None:
    run = st.session_state.latest_run
    pending = st.session_state.pending_confirmation
    if (
        not run
        or (pending and pending.get("status") == "pending")
        or st.session_state.feedback_submitted_for == run["run_id"]
    ):
        return
    st.subheader("Was this issue resolved?")
    with st.form("feedback-form"):
        resolved = st.radio("Resolution", ["Resolved", "Not resolved"], horizontal=True)
        rating = st.slider("Satisfaction", min_value=1, max_value=5, value=4)
        comment = st.text_area("Optional feedback", max_chars=2000)
        submitted = st.form_submit_button("Submit feedback")
    if submitted:
        try:
            client.submit_feedback(
                agent_run_id=run["run_id"],
                actor_id=st.session_state.actor_id,
                user_role=st.session_state.user_role,
                resolved=resolved == "Resolved",
                satisfaction_rating=rating,
                comment=comment.strip() or None,
                ticket_number=st.session_state.ticket_number,
            )
        except APIError as exception:
            st.error(f"{exception.code}: {exception}")
        else:
            st.session_state.feedback_submitted_for = run["run_id"]
            st.success("Feedback saved")
