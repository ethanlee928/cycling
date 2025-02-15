from datetime import timedelta

import ollama
import pandas as pd
import streamlit as st
from stqdm import stqdm
from tcxreader.tcxreader import TCXReader, TCXTrackPoint

MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694

ZONES = [
    "Active Recovery",
    "Endurance",
    "Tempo",
    "Threshold",
    "VO2",
    "Anaerobic Capacity",
    "Neuromuscular Power",
]

ZONE_COLORS = ["gray", None, "blue", "green", "orange", "red", "violet"]


class Colors:
    GREY = "#3f3f3f"
    YELLOW = "#FEDD00"
    PURPLE = "#6A0DAD"
    PALE_YELLOW = "#FED172"
    ORANGE = "#F3742B"
    DARK_ORANGE = "#B83A14"
    BLUE_PURPLE = "#231650"


def set_colors(value: str, color: str = None) -> str:
    if color is None:
        return value
    return f":{color}[{value}]"


def get_tcx_data(tcx_file):
    reader = TCXReader()
    return reader.read(tcx_file)


def tcx_to_df(tcx_data, kph: bool) -> pd.DataFrame:
    trackpoint_data = []
    trackpoint: TCXTrackPoint

    for trackpoint in stqdm(tcx_data.trackpoints):
        speed = trackpoint.tpx_ext.get("Speed")
        speed = speed * (MPS_TO_KPH if kph else MPS_TO_MPH)
        trackpoint_data.append(
            {
                "time": trackpoint.time,
                "distance": trackpoint.distance,
                "speed": speed,
                "power": trackpoint.tpx_ext.get("Watts"),
                "cadence": trackpoint.cadence,
                "latitude": trackpoint.latitude,
                "longitude": trackpoint.longitude,
                "elevation": trackpoint.elevation,
                "heart_rate": trackpoint.hr_value,
            }
        )
    df = pd.DataFrame(trackpoint_data)
    df.set_index("time", inplace=True)
    return df


def get_zone(power: float, ftp: float) -> int:
    zones_upper_thresh = [0.55, 0.75, 0.9, 1.05, 1.2, 1.5]
    percentage = power / ftp
    for idx, thresh in enumerate(zones_upper_thresh):
        if percentage < thresh:
            return idx
    return len(zones_upper_thresh)


def get_zone_range(zone: int, ftp: float) -> str:
    zones_upper_thresh = [0, 0.55, 0.75, 0.9, 1.05, 1.2, 1.5]
    if zone < len(zones_upper_thresh) - 1:
        return f"{ftp * zones_upper_thresh[zone]:.0f} - {ftp * zones_upper_thresh[zone + 1]:.0f} W"
    return f"{ftp * zones_upper_thresh[zone]:.0f}+ W"


def model_res_generator():
    messages = (
        st.session_state["summary"] + st.session_state["messages"]
        if "summary" in st.session_state
        else st.session_state["messages"]
    )
    stream = ollama.chat(
        model="cycling-qwen2.5:7b",
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]


@st.cache_data
def model_res(messages):
    response = ollama.chat(
        model="cycling-qwen2.5:7b",
        messages=messages,
    )
    return response["message"]["content"]


st.set_page_config(page_title="Cycling Workout Analysis", page_icon=":bicyclist:")

st.title("Cycling Workout Analysis")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "summary" not in st.session_state:
    st.session_state["summary"] = []

uploaded_file = st.file_uploader("Choose a TCX file", type=["tcx"], accept_multiple_files=False)
ftp = st.number_input("Functional Threshold Power (FTP)", 0, 1000, 200)

st.divider()

if uploaded_file is not None:
    # ----------------- SUMMARY -----------------
    st.header("Workout Summary")

    tcx_data = get_tcx_data(uploaded_file)
    df = tcx_to_df(tcx_data, kph=True)
    df["zone"] = df["power"].apply(lambda x: get_zone(x, ftp))

    moving_time_seconds = df[df["speed"] > 0].shape[0]
    power_avg = df["power"].mean()
    calories = power_avg * moving_time_seconds / 1000

    col1, col2, col3 = st.columns(3)
    col1.metric("Distance", f"{tcx_data.distance / 1000:.2f} km")
    col2.metric("Duration", f"{timedelta(seconds=tcx_data.duration)}")
    col3.metric("Moving Time", f"{timedelta(seconds=moving_time_seconds)}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Average Speed", f"{df['speed'].mean():.2f} km/h")
    col2.metric("Calories", f"{round(calories)} kcal")
    col3.metric("Average Power", f"{round(power_avg)} W")

    st.divider()

    # ----------------- SPEED -----------------
    st.header("Speed")
    df["distance"] = df["distance"] / 1000
    df["elevation_scaled"] = df["elevation"] * (df["speed"].max() / df["elevation"].max())
    st.area_chart(
        df,
        x="distance",
        y=["elevation_scaled", "speed"],
        x_label="Distance (km)",
        y_label="Speed (km/h)",
        color=[Colors.GREY, Colors.YELLOW],
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    col1.metric("Average Speed", f"{df['speed'].mean():.2f} km/h")
    col2.metric("Max Speed", f"{df['speed'].max():.2f} km/h")

    st.divider()

    # ----------------- ELEVATION -----------------
    st.header("Climbing")
    st.area_chart(
        df,
        x="distance",
        y="elevation",
        x_label="Distance (km)",
        y_label="Elevation (m)",
        color=Colors.DARK_ORANGE,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Max Elevation", f"{df['elevation'].max():.0f} m")
    col2.metric("Min Elevation", f"{df['elevation'].min():.0f} m")
    diff = df["elevation"].diff().clip(lower=0)
    elevation_gain = diff[diff < 10].sum()  # Ignore very big elevation changes
    col3.metric("Elevation Gain", f"{elevation_gain:.0f} m")

    st.divider()

    # ----------------- CADENCE -----------------
    st.header("Cadence")
    df["elevation_scaled"] = df["elevation"] * (df["cadence"].max() / df["elevation"].max())
    st.area_chart(
        df,
        x="distance",
        y=["elevation_scaled", "cadence"],
        x_label="Distance (km)",
        y_label="Cadence (rpm)",
        color=[Colors.PURPLE, Colors.GREY],
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    avg_cadence = df[df["cadence"] > 0]["cadence"].mean()
    col1.metric("Average Cadence", f"{avg_cadence:.0f} rpm")
    col2.metric("Max Cadence", f"{df['cadence'].max():.0f} rpm")

    st.divider()

    # ----------------- POWER -----------------

    st.header("Power")
    st.area_chart(df, x="distance", y="power", x_label="Distance (km)", y_label="Power (W)")
    zone_counts = round(df["zone"].value_counts(normalize=True).sort_index() * 100, 1)
    zone_durations = [str(timedelta(seconds=zone_count)) for zone_count in df["zone"].value_counts().sort_index()]
    zone_counts_df = pd.DataFrame(
        {
            "Description": [set_colors(zone, color) for zone, color in zip(ZONES, ZONE_COLORS)],
            "Range": [get_zone_range(zone, ftp) for zone in range(len(ZONES))],
            "Zone": zone_counts.index + 1,
            "Percent": zone_counts.values,
            "Duration": zone_durations,
        }
    )
    zone_counts_df.set_index("Zone", inplace=True)
    st.subheader("Zone Distribution")
    st.bar_chart(
        data=zone_counts_df,
        y="Percent",
        use_container_width=True,
        horizontal=True,
    )
    st.table(zone_counts_df.drop(columns=["Percent"]))

    st.divider()

    # ----------------- PERFORMANCE COACH -----------------

    st.header("Performance coach")

    if not st.session_state["summary"]:
        user_message = {
            "role": "user",
            "content": f"Debrief the user's workout in 50 words:\n{zone_counts_df}\n.",
        }
        debrief = model_res(messages=[user_message])
        st.session_state["summary"] = [
            user_message,
            {"role": "assistant", "content": debrief},
        ]

    for message in st.session_state["summary"]:
        if message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Chat with the performance coach"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message = st.write_stream(model_res_generator())
            st.session_state["messages"].append({"role": "assistant", "content": message})

    if st.button("Clear chat"):
        st.session_state["messages"] = []
        st.session_state["summary"] = []
