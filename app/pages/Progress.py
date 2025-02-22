import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import stqdm

from common import get_tcx_data, tcx_to_df, Colors
from collections import defaultdict

# History directory containing all the TCX files
HISTORY_DIR = Path("history")


def list_tcx_files():
    """Load all the TCX files in the history directory, sorted by date prefix"""
    return sorted(HISTORY_DIR.glob("*.tcx"))


@st.cache_data()
def get_history_dfs() -> list[pd.DataFrame]:
    tcx_files = list_tcx_files()
    return [
        tcx_to_df(get_tcx_data(file), kph=True)
        for file in stqdm.stqdm(tcx_files, desc="Loading TCX files")
    ]


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
df_tss = pd.DataFrame(
    {"Week": [week.date() for week in weeks], "TSS": weekly_tss}
).set_index("Week")


st.header("Weekly Training Stress Score (TSS)")
st.bar_chart(df_tss, color=Colors.PURPLE, use_container_width=True)

TRAINING_LOAD_TIMEFRAME = 365

# --- Chronic Training Load ---
a_ctl = 2 / (42 + 1)
a_atl = 2 / (7 + 1)

st.header("Chronic Training Load (CTL)")
st.write("Proxy for fitness")

date_to_tss = defaultdict(lambda: 0.0)
for tss, start_time in zip(l_tss, start_times):
    date = start_time.date()
    date_to_tss[date] += tss


# loop last 365 days of date
start_date = today - timedelta(days=TRAINING_LOAD_TIMEFRAME)

ctl = {"Date": [], "CTL": [], "ATL": [], "TSB": []}
for i in range(TRAINING_LOAD_TIMEFRAME + 1):
    date = start_date + timedelta(days=i)
    ctl["Date"].append(date)
    last_ctl = ctl["CTL"][-1] if ctl["CTL"] else 0
    last_atl = ctl["ATL"][-1] if ctl["ATL"] else 0
    current_ctl = last_ctl * (1 - a_ctl) + date_to_tss.get(date.date(), 0) * a_ctl
    current_atl = last_atl * (1 - a_atl) + date_to_tss.get(date.date(), 0) * a_atl
    ctl["TSB"].append(current_ctl - current_atl)
    ctl["CTL"].append(current_ctl)
    ctl["ATL"].append(current_atl)

df_ctl = pd.DataFrame(ctl).set_index("Date")
st.line_chart(df_ctl, y=["CTL", "TSB"], color=[Colors.YELLOW, Colors.PURPLE], use_container_width=True)

# --- Acute Training Load ---
a_ctl = 2 / (7 + 1)
st.header("Acute Training Load (ATL)")
st.write("Proxy for fatigue")

atl = {"Date": [], "ATL": []}
for i in range(TRAINING_LOAD_TIMEFRAME + 1):
    date = start_date + timedelta(days=i)
    atl["Date"].append(date)
    last_atl = atl["ATL"][-1] if atl["ATL"] else 0
    current_atl = last_atl * (1 - a_ctl) + date_to_tss.get(date.date(), 0) * a_ctl
    atl["ATL"].append(current_atl)

df_atl = pd.DataFrame(atl).set_index("Date")
st.line_chart(df_atl, color=Colors.DARK_ORANGE, use_container_width=True)
