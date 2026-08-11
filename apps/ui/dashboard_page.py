"""Analytics Dashboard Streamlit page."""

from typing import Any

import pandas as pd
import streamlit as st

from apps.ui.client import APIError, ITSupportAPIClient


def render_dashboard_page(client: ITSupportAPIClient) -> None:
    st.title("Analytics Dashboard")
    st.caption("All metrics are calculated by FastAPI from PostgreSQL and Evaluation artifacts")
    with st.sidebar:
        st.subheader("Dashboard access")
        actor_id = st.text_input("Support Actor ID", value="support-demo")
        user_role = st.selectbox(
            "Support Role",
            options=["it_support", "project_maintainer", "employee"],
        )
        days = st.slider("Window (days)", min_value=1, max_value=365, value=30)
    try:
        payload = client.analytics(actor_id=actor_id.strip(), user_role=user_role, days=days)
    except APIError as exception:
        st.error(f"{exception.code}: {exception}")
        return

    first = st.columns(5)
    first[0].metric("Tickets", payload["total_tickets"])
    first[1].metric("Self-service", _percent(payload["self_service_resolution_rate"]))
    first[2].metric("Human transfer", _percent(payload["human_transfer_rate"]))
    first[3].metric("Tool success", _percent(payload["tool_success_rate"]))
    first[4].metric("Satisfaction", _number(payload["average_satisfaction"], suffix=" / 5"))

    second = st.columns(3)
    second[0].metric("Avg Agent steps", _number(payload["average_agent_steps"]))
    second[1].metric("Avg tool calls", _number(payload["average_tool_calls"]))
    second[2].metric(
        "Avg response time",
        _number(payload["average_response_time_ms"], suffix=" ms"),
    )

    left, right = st.columns(2)
    with left:
        _bar_chart("Ticket category distribution", payload["ticket_categories"])
        _bar_chart("Issue volume", payload["issue_counts"])
    with right:
        _bar_chart("Satisfaction distribution", payload["satisfaction_distribution"])
        _bar_chart("Frequent failure reasons", payload["frequent_failure_reasons"])

    st.subheader("Recent evaluation results")
    evaluations = payload["recent_evaluations"]
    if evaluations:
        st.dataframe(pd.DataFrame(evaluations), hide_index=True, width="stretch")
    else:
        st.info("No Evaluation JSON artifacts found.")


def _percent(metric: dict[str, Any]) -> str:
    value = metric["value"]
    return "N/A" if value is None else f"{value:.1%}"


def _number(metric: dict[str, Any], *, suffix: str = "") -> str:
    value = metric["value"]
    return "N/A" if value is None else f"{value:.1f}{suffix}"


def _bar_chart(title: str, items: list[dict[str, Any]]) -> None:
    st.subheader(title)
    if not items:
        st.info("No data in this window.")
        return
    frame = pd.DataFrame(items).set_index("label")
    st.bar_chart(frame["count"], horizontal=True)
