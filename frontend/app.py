"""Streamlit has no SQL credentials or execution capability; all actions use the API."""

import os
from contextlib import suppress
from typing import Any

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="SQL Intelligence Agent", page_icon="🔎", layout="wide")


def api(path: str, body: dict[str, Any] | None = None, method: str | None = None) -> dict[str, Any] | None:
    token = os.environ.get("LOCAL_API_TOKEN", "")
    # Cloud UI identity propagation is an M2 deployment gate; no shared cloud token fallback.
    if os.environ.get("APP_ENV", "local") == "cloud":
        st.error("Cloud UI requires the approved delegated Entra sign-in integration (M2).")
        return None
    try:
        with httpx.Client(
            base_url=os.environ.get("API_URL", "http://127.0.0.1:8000"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=65.0,
        ) as client:
            response = client.request(method or ("GET" if body is None else "POST"), path, json=body)
        data = response.json()
        if response.is_error:
            st.error(data.get("detail", "The request could not be completed."))
            return None
        return dict(data)
    except (httpx.HTTPError, ValueError):
        st.error("The backend is unavailable. Start the local API and check its database connection.")
        return None


def dataframe(result: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(result["rows"], columns=result["columns"])
    for column in frame.columns:
        with suppress(ValueError, TypeError):
            frame[column] = pd.to_numeric(frame[column])
    return frame


st.caption("OPERATIONS INTELLIGENCE / SQL LEARNING LAB")
st.title("Ask the data. Understand the SQL.")
st.write("Explore synthetic operations data with validated T-SQL and a transparent path to every answer.")

catalog = api("/catalog")
if catalog is None:
    st.stop()

with st.sidebar:
    st.subheader("SQL Intelligence Agent")
    st.caption("Read-only • Synthetic data • CAD")
    st.info(
        "Mock mode uses 27 reproducible questions."
        if catalog["mode"] == "mock"
        else "Live Azure OpenAI · Each question uses billable inference. Every query is validated."
    )
    if catalog["mode"] == "azure":
        st.caption(f"Deployment: {catalog['model_deployment']}")
    if st.button("New conversation", use_container_width=True):
        conversation_id = st.session_state.get("conversation_id")
        if conversation_id:
            api(f"/conversations/{conversation_id}", method="DELETE")
        st.session_state.history = []
        st.session_state.conversation_id = None
        st.rerun()
    st.caption("Context: up to 12 turns; expires after 30 minutes idle or an API restart.")
    questions = [e["question"] for e in catalog["examples"]]
    selected = st.selectbox("Try a verified question", questions, index=9)
    run_example = st.button("Ask this question", type="primary", use_container_width=True)
    learning_mode = st.toggle("SQL Learning Mode", value=True)
    st.divider()
    with st.expander("Metric definitions"):
        for name, definition in catalog["metrics"].items():
            st.markdown(f"**{name}**")
            st.text(definition)
    with st.expander("Table grain"):
        for name, grain in catalog["grains"].items():
            st.markdown(f"**{name}** — {grain}")
    st.caption(
        f"Limits: {catalog['limits']['rows']} rows · "
        f"{catalog['limits']['timeout_seconds']} seconds per statement"
    )

left, middle, right = st.columns(3)
left.metric("Data source", "SQL Server")
middle.metric("Synthetic source records", "1,548")
right.metric("Execution policy", "Read-only")
st.divider()

if "history" not in st.session_state:
    st.session_state.history = []

question = st.chat_input("Ask about contract value, invoicing, expenses or job performance…")
if run_example:
    question = selected
if question:
    with st.spinner("Proposing SQL, validating policy and reading the approved views…"):
        answer = api(
            "/questions",
            {
                "question": question,
                "conversation_id": st.session_state.get("conversation_id"),
            },
        )
    if answer:
        st.session_state.conversation_id = answer["conversation_id"]
        st.session_state.history.append({"question": question, "answer": answer})
        st.session_state.history = st.session_state.history[-12:]

if not st.session_state.history:
    st.subheader("Start with a business question")
    st.write(
        "Choose a verified example in the sidebar, or ask a question below. "
        "Each answer includes the SQL, full bounded result and a lesson you can practice."
    )

for message in st.session_state.history:
    answer = message["answer"]
    index = answer["request_id"]
    with st.chat_message("user"):
        st.text(message["question"])
    with st.chat_message("assistant"):
        # Plain text rendering keeps returned data inert, including prompt/HTML injection strings.
        st.text(answer["answer"])
        if answer["status"] == "clarification":
            continue
        tabs = st.tabs(["Results", "Generated SQL", "Learn & practice"])
        with tabs[0]:
            frame = dataframe(answer["result"])
            st.dataframe(frame, hide_index=True, use_container_width=True)
            st.caption(
                f"{answer['result']['row_count']} rows · "
                f"{answer['result']['elapsed_ms']} ms · No hidden row truncation"
            )
            numeric = list(frame.select_dtypes(include="number").columns)
            if (
                len(frame) > 1
                and numeric
                and len(frame.columns) >= 2
                and st.checkbox("Show chart", key=f"chart_{index}")
            ):
                metric = st.selectbox("Measure", numeric, key=f"metric_{index}")
                st.bar_chart(frame.set_index(frame.columns[0])[[metric]])
        with tabs[1]:
            st.code(answer["sql"], language="sql")
            if answer["parameters"]:
                st.json({p["name"]: p["value"] for p in answer["parameters"]})
            st.caption("Validated against the approved view and column policy before execution.")
        with tabs[2]:
            if not learning_mode:
                st.info("Turn on SQL Learning Mode in the sidebar to explore this query.")
                continue
            lesson = answer["learning"]
            st.markdown("**Input grain**")
            st.text(lesson["grain"])
            st.caption(" · ".join(lesson["concepts"]))
            for text in lesson["explanation"]:
                st.write(text)
            with st.expander("Correctness and performance notes"):
                for text in lesson["cautions"]:
                    st.write(text)
            exercise_id = lesson["exercise_id"]
            if exercise_id:
                st.markdown("**Your turn: write an alternative query with the same result.**")
                with st.form(f"practice_{index}"):
                    alternative = st.text_area(
                        "Alternative T-SQL", value=answer["sql"], height=180, key=f"sql_{index}"
                    )
                    st.caption("Uses the displayed parameter values, if any.")
                    submit = st.form_submit_button("Validate & compare")
                if submit:
                    comparison = api(
                        "/practice",
                        {
                            "exercise_id": exercise_id,
                            "sql": alternative,
                            "parameters": answer["parameters"],
                        },
                    )
                    if comparison:
                        st.session_state[f"comparison_{index}"] = comparison
                        st.toast(comparison["feedback"])
                comparison = st.session_state.get(f"comparison_{index}")
                if comparison:
                    (st.success if comparison["matches"] else st.warning)(comparison["feedback"])
                    st.caption(comparison["comparison"])
                    with st.expander("Independent reference"):
                        st.code(comparison["reference_sql"], language="sql")
                        st.dataframe(dataframe(comparison["reference"]), hide_index=True)
            else:
                st.info("Practice comparison is available for the verified example questions.")
