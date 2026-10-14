from typing import Any
from uuid import uuid4

import httpx
import pandas as pd
import pydeck as pdk
import streamlit as st

from earthquake_rag.application.agent_runtime import invoke_agent
from earthquake_rag.application.ingestion import synchronize_usgs_feed
from earthquake_rag.application.temporal import (
    get_latest_events,
    get_latest_ingestions,
)
from earthquake_rag.core.config import get_settings
from earthquake_rag.domain.entities import AgentContext
from earthquake_rag.presentation.cli import parse_datetime

settings = get_settings()


def calculate_metrics(events: list[dict]) -> dict[str, Any]:
    if not events:
        return {"count": 0, "maximum": None, "average": None, "deepest": None}
    magnitudes = [float(event["magnitude"]) for event in events]
    return {
        "count": len(events),
        "maximum": max(magnitudes),
        "average": sum(magnitudes) / len(magnitudes),
        "deepest": max(float(event["depth_km"]) for event in events),
    }


def render_metrics(events: list[dict]) -> None:
    metrics = calculate_metrics(events)
    columns = st.columns(4)
    columns[0].metric("Events", metrics["count"])
    columns[1].metric(
        "Maximum magnitude",
        "—" if metrics["maximum"] is None else f"{metrics['maximum']:.1f}",
    )
    columns[2].metric(
        "Average magnitude",
        "—" if metrics["average"] is None else f"{metrics['average']:.2f}",
    )
    columns[3].metric(
        "Maximum depth",
        "—" if metrics["deepest"] is None else f"{metrics['deepest']:.1f} km",
    )


def render_comparison(historical: list[dict], current: list[dict]) -> None:
    rows = []
    for label, events in [("Selected snapshot", historical), ("Now", current)]:
        metrics = calculate_metrics(events)
        rows.append(
            {
                "Snapshot": label,
                "Events": metrics["count"],
                "Maximum magnitude": metrics["maximum"],
                "Average magnitude": metrics["average"],
                "Maximum depth (km)": metrics["deepest"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_map(events: list[dict]) -> None:
    if not events:
        st.info("No earthquake events are available for this time window.")
        return
    data = pd.DataFrame(events)
    data["radius"] = data["magnitude"].clip(lower=0.1).pow(2) * 18_000
    data["color"] = data["magnitude"].apply(
        lambda value: (
            [220, 38, 38, 180]
            if value >= 5
            else ([249, 115, 22, 170] if value >= 3 else [14, 165, 233, 150])
        )
    )
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position="[longitude, latitude]",
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )
    view = pdk.ViewState(
        latitude=float(data["latitude"].mean()),
        longitude=float(data["longitude"].mean()),
        zoom=1,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={
                "html": (
                    "<b>{place}</b><br/>Magnitude: {magnitude}<br/>"
                    "Depth: {depth_km} km<br/>{occurred_at}"
                )
            },
        ),
        use_container_width=True,
    )


def render_evidence(tools: list[dict]) -> None:
    if not tools:
        st.caption("The model answered without calling a tool.")
        return
    for evidence in tools:
        st.markdown(f"**{evidence['name']}**")
        st.json(evidence["arguments"])
        if evidence.get("output"):
            st.code(evidence["output"][:5_000], language="json")


def endpoint_available(url: str) -> bool:
    try:
        return httpx.get(url, timeout=2).is_success
    except httpx.HTTPError:
        return False


st.set_page_config(page_title="Earthquake Research Agent", page_icon="🌍", layout="wide")
st.session_state.setdefault("thread_id", f"streamlit-{uuid4()}")
st.session_state.setdefault("messages", [])

st.title("Earthquake Research Agent")
st.caption(
    "Temporal and agentic RAG with real USGS data, PostgreSQL, Qdrant, "
    "Ollama, LangChain and LangGraph."
)

with st.sidebar:
    st.header("Research context")
    hours = st.select_slider(
        "Time window",
        options=[1, 6, 12, 24, 72, 168],
        value=24,
        format_func=lambda value: f"{value} hours",
    )
    user_id = st.text_input("User ID", value="student-1")
    user_name = st.text_input("Name", value="Student")
    expertise = st.selectbox(
        "Expertise", ["beginner", "intermediate", "advanced"], index=1
    )

    if st.button("Synchronize USGS", use_container_width=True):
        try:
            with st.spinner("Downloading the current USGS feed..."):
                summary = synchronize_usgs_feed(settings.feed.url)
            st.success(f"Stored {summary.inserted_versions} new event versions.")
            st.rerun()
        except Exception as exc:
            st.error(f"USGS synchronization failed: {exc}")

    if st.button("New conversation", use_container_width=True):
        st.session_state.thread_id = f"streamlit-{uuid4()}"
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Services")
    services = {
        "Ollama": endpoint_available(f"{settings.ai.ollama_base_url}/api/version"),
        "Qdrant": endpoint_available(settings.qdrant.url),
    }
    for name, available in services.items():
        st.write(f"{'Available' if available else 'Unavailable'} · {name}")

try:
    current_events = get_latest_events(hours=hours, limit=2_000)
    ingestions = get_latest_ingestions(50)
    database_available = True
except Exception as exc:
    current_events, ingestions = [], []
    database_available = False
    st.error(f"PostgreSQL is unavailable: {exc}")

with st.sidebar:
    st.write(f"{'Available' if database_available else 'Unavailable'} · PostgreSQL")
    if ingestions:
        st.caption(f"Latest ingestion: {ingestions[0]['fetched_at']}")

snapshot_options = {"Now": None}
for ingestion in ingestions:
    label = f"Ingestion #{ingestion['id']} · {ingestion['fetched_at']}"
    snapshot_options[label] = ingestion["fetched_at"]

selected_label = st.selectbox("Knowledge snapshot", options=list(snapshot_options))
selected_as_of = snapshot_options[selected_label]
selected_events = current_events
if selected_as_of:
    selected_events = get_latest_events(
        hours=hours,
        limit=2_000,
        as_of=parse_datetime(selected_as_of),
    )
    st.subheader("Selected snapshot compared with now")
    render_comparison(selected_events, current_events)
else:
    render_metrics(selected_events)

map_tab, events_tab, chat_tab = st.tabs(["Map", "Events", "AI research"])

with map_tab:
    render_map(selected_events)

with events_tab:
    if selected_events:
        visible_columns = [
            "magnitude",
            "place",
            "occurred_at",
            "depth_km",
            "status",
            "url",
        ]
        st.dataframe(
            pd.DataFrame(selected_events)[visible_columns],
            hide_index=True,
            use_container_width=True,
            column_config={"url": st.column_config.LinkColumn("USGS event")},
        )
    else:
        st.info("No events are available.")

with chat_tab:
    st.caption(
        f"Thread: `{st.session_state.thread_id}` · "
        f"Knowledge cutoff: `{selected_as_of or 'now'}`"
    )
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("tools"):
                with st.expander("Evidence and tool calls"):
                    render_evidence(message["tools"])

    if prompt := st.chat_input("Ask about recent earthquakes or seismology"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Researching data and educational sources..."):
                    run = invoke_agent(
                        settings,
                        question=prompt,
                        thread_id=st.session_state.thread_id,
                        context=AgentContext(
                            user_id=user_id,
                            user_name=user_name,
                            expertise=expertise,
                            default_hours=hours,
                            as_of=selected_as_of,
                        ),
                    )
                st.markdown(run.answer)
                tools = [
                    {
                        "name": evidence.name,
                        "arguments": evidence.arguments,
                        "output": evidence.output,
                    }
                    for evidence in run.tools
                ]
                with st.expander("Evidence and tool calls"):
                    render_evidence(tools)
                st.session_state.messages.append(
                    {"role": "assistant", "content": run.answer, "tools": tools}
                )
            except Exception as exc:
                st.error(
                    "The agent could not run. Check Ollama, PostgreSQL and "
                    f"Qdrant. Details: {exc}"
                )
