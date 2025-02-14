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


def model_res_generator(messages):
    stream = ollama.chat(
        model="cycling-qwen2.5:7b",
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]


st.title("Cycling Workout Analysis")
uploaded_file = st.file_uploader("Choose a TCX file", type=["tcx"], accept_multiple_files=False)
ftp = st.number_input("FTP", 0, 1000, 200)

if uploaded_file is not None:
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

    st.header("Speed")
    df["distance"] = df["distance"] / 1000
    df["elevation_scaled"] = df["elevation"] * (df["speed"].max() / df["elevation"].max())
    st.area_chart(
        df,
        x="distance",
        y=["elevation_scaled", "speed"],
        x_label="Distance (km)",
        y_label="Speed (km/h)",
        color=["#3f3f3f", "#fedd00"],
        use_container_width=True,
    )

    st.header("Cadence")

    st.header("Power")

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

    st.subheader("AI coach")
    messages = [
        {
            "role": "user",
            "content": f"Debrief the user's workout in 50 words:\n{zone_counts_df}\n.",
        }
    ]
