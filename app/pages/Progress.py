import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import ollama
import pandas as pd
import stqdm
import streamlit as st
from common import Colors, get_tcx_data, tcx_to_df

# History directory containing all the TCX files
HISTORY_DIR = Path("history")
LLM = "cycling-qwen2.5:7b"

if "messages_progress" not in st.session_state:
    st.session_state["messages_progress"] = []

if "summary_progress" not in st.session_state:
    st.session_state["summary_progress"] = []


def list_tcx_files():
    """Load all the TCX files in the history directory, sorted by date prefix"""
    return sorted(HISTORY_DIR.glob("*.tcx"))


def model_res_generator():
    messages = (
        st.session_state["messages_progress"] + st.session_state["messages_progress"]
        if "messages_progress" in st.session_state
        else st.session_state["messages_progress"]
    )
    stream = ollama.chat(
        model=LLM,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]


@st.cache_data
def model_res(messages):
    response = ollama.chat(
        model=LLM,
        messages=messages,
    )
    # remove <think></think> tags and contents within them
    cleaned_content = re.sub(r"<think>.*?</think>", "", response["message"]["content"], flags=re.DOTALL)
    return cleaned_content


@st.cache_data()
def get_history_dfs() -> list[pd.DataFrame]:
    tcx_files = list_tcx_files()
    return [tcx_to_df(get_tcx_data(file), kph=True) for file in stqdm.stqdm(tcx_files, desc="Loading TCX files")]


def get_tss(df: pd.DataFrame, ftp: float) -> float:
    moving_time_seconds = df[df["speed"] > 0].shape[0]
    pwr_rollings = df["power"].rolling(window=30).mean().dropna()
    normalized_power = (pwr_rollings**4).mean() ** 0.25
    intensity_factor = normalized_power / ftp
    tss = intensity_factor**2 * moving_time_seconds / 3600 * 100
    return tss


def get_start_time(df: pd.DataFrame) -> datetime:
    return df.index[0].to_pydatetime()


# --- Page Contents ---

st.title("Fitness Score")

st.write("Number of activities:", len(list_tcx_files()))
dfs = get_history_dfs()
ftp = st.number_input("Functional Threshold Power (FTP)", 0, 1000, 200)


# --- Weekly TSS ---
today = datetime.today()
weeks = pd.date_range(end=today, periods=52, freq="W-MON").to_pydatetime()

start_times = [get_start_time(df) for df in dfs]
l_tss = [get_tss(df, ftp) for df in dfs]
weekly_tss = [0.0] * len(weeks)

# Create mapping from week date to index
index_map = {week.date(): idx for idx, week in enumerate(weeks)}

# Accumulate TSS values into appropriate weeks
for start_time, tss in zip(start_times, l_tss):
    # Calculate Monday of the week for this activity
    activity_date = start_time.date()
    days_since_monday = activity_date.weekday()  # Monday = 0
    week_monday = activity_date - timedelta(days=days_since_monday)

    # Add TSS to corresponding week
    if week_monday in index_map:
        weekly_tss[index_map[week_monday]] += tss

# Create DataFrame for visualization
df_tss = pd.DataFrame({"Week": [week.date() for week in weeks], "TSS": weekly_tss}).set_index("Week")


st.header("Weekly Training Stress Score (TSS)")
st.bar_chart(df_tss, color=Colors.ORANGE, use_container_width=True)

TRAINING_LOAD_TIMEFRAME = 120  # 1 Quarter

# --- Training Load ---
st.header("Training Load")

st.write(
    "Calculate Chronic Training Load (CTL), Acute Training Load (ATL), and Training Stress Balance (TSB) for 1 quarter (120 days)"
)

a_ctl = 2 / (42 + 1)
a_atl = 2 / (7 + 1)

date_to_tss = defaultdict(lambda: 0.0)
for tss, start_time in zip(l_tss, start_times):
    date = start_time.date()
    date_to_tss[date] += tss

start_date = today - timedelta(days=TRAINING_LOAD_TIMEFRAME)
training_load = {"Date": [], "CTL": [], "ATL": [], "TSB": []}
for i in range(TRAINING_LOAD_TIMEFRAME + 1):
    date = start_date + timedelta(days=i)
    training_load["Date"].append(date)
    last_ctl = training_load["CTL"][-1] if training_load["CTL"] else 0
    last_atl = training_load["ATL"][-1] if training_load["ATL"] else 0
    current_ctl = last_ctl * (1 - a_ctl) + date_to_tss.get(date.date(), 0) * a_ctl
    current_atl = last_atl * (1 - a_atl) + date_to_tss.get(date.date(), 0) * a_atl
    training_load["TSB"].append(current_ctl - current_atl)
    training_load["CTL"].append(current_ctl)
    training_load["ATL"].append(current_atl)

training_load_df = pd.DataFrame(training_load).set_index("Date")

st.subheader("Chronic Training Load (CTL)")
st.line_chart(training_load_df, y="CTL", color=Colors.BLUE, use_container_width=True)
st.caption("CTL is the proxy for fitness")

st.subheader("Acute Training Load (ATL)")
st.line_chart(training_load_df, y="ATL", color=Colors.YELLOW, use_container_width=True)
st.caption("ATL is the proxy for fatigue")

st.subheader("Training Stress Balance (TSB)")
st.line_chart(training_load_df, y="TSB", color=Colors.PINK, use_container_width=True)
st.caption("TSB is the proxy for form")

st.subheader("Performance Management Chart")

training_load_df.reset_index(inplace=True)
base = (
    alt.Chart(training_load_df)
    .transform_fold(["CTL", "ATL", "TSB"], as_=["Metric", "Value"])
    .encode(
        x="Date:T",
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(domain=["CTL", "ATL", "TSB"], range=[Colors.BLUE, Colors.YELLOW, Colors.PINK]),
        ),
    )
)

line_ctl = base.transform_filter(alt.datum.Metric == "CTL").mark_line().encode(alt.Y("CTL:Q"))
line_atl = base.transform_filter(alt.datum.Metric == "ATL").mark_line().encode(alt.Y("ATL:Q"))
line_tsb = base.transform_filter(alt.datum.Metric == "TSB").mark_line().encode(alt.Y("TSB:Q"))

combined_chart = alt.layer(line_tsb, line_ctl + line_atl).resolve_scale(y="independent")
st.altair_chart(combined_chart, use_container_width=True)
st.caption("- Overly negative TSB can indicate overtraining.")
st.caption("- Most coaches generally guide towards maintaining TSB value above -30.")
st.caption("- Closer to 0 TSB indicates peak performance, recommended for race day.")


# --- Performance Coach ---
st.header("Performance Coach")

col1, col2, col3 = st.columns(3)
current_ctl, curremt_atl, current_tsb = (
    training_load_df["CTL"].iloc[-1],
    training_load_df["ATL"].iloc[-1],
    training_load_df["TSB"].iloc[-1],
)
delta_ctl, delta_atl, delta_tsb = (
    current_ctl - training_load_df["CTL"].iloc[-2],
    curremt_atl - training_load_df["ATL"].iloc[-2],
    current_tsb - training_load_df["TSB"].iloc[-2],
)

current_ctl = round(current_ctl, 1)
curremt_atl = round(curremt_atl, 1)
current_tsb = round(current_tsb, 1)
delta_ctl = round(delta_ctl, 1)
delta_atl = round(delta_atl, 1)
delta_tsb = round(delta_tsb, 1)

col1.metric("CTL", current_ctl, delta=delta_ctl)
col2.metric("ATL", curremt_atl, delta=delta_atl)
col3.metric("TSB", current_tsb, delta=delta_tsb)

st.write(
    f"Today is {today.date()}, here's my training load: CTL={current_ctl}, ATL={curremt_atl}, TSB={current_tsb}.\nDo you recommend training or resting?"
)

# --- Summary ---
if not st.session_state["summary_progress"]:
    user_message = {
        "role": "user",
        "content": f"Today is {today.date()}, here's my training load: CTL={current_ctl}, ATL={curremt_atl}, TSB={current_tsb}.\nDo you recommend training or resting?\nPlease answer in under 100 words.",
    }
    debrief = model_res(messages=[user_message])
    st.session_state["summary_progress"] = [
        user_message,
        {"role": "assistant", "content": debrief},
    ]

for message in st.session_state["summary_progress"]:
    if message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])

# --- Chat ---
for message in st.session_state["messages_progress"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Chat with the performance coach"):
    st.session_state["messages_progress"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message = st.write_stream(model_res_generator())
        st.session_state["messages_progress"].append({"role": "assistant", "content": message})

if st.button("Clear chat"):
    st.session_state["messages_progress"] = []
    st.session_state["summary_progress"] = []
