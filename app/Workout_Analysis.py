import re
from datetime import timedelta

import altair as alt
import ollama
import pandas as pd
import streamlit as st
from common import ZONE_COLORS, ZONES, Colors, get_tcx_data, get_zone, tcx_to_df

# Custom model built with Ollama Modelfile
LLM = "cycling-qwen2.5:7b"


def set_colors(value: str, color: str = None) -> str:
    if color is None:
        return value
    return f":{color}[{value}]"


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


st.set_page_config(page_title="Cycling Workout Analysis", page_icon=":bicyclist:")

st.title("Workout Analysis")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "summary" not in st.session_state:
    st.session_state["summary"] = []

uploaded_file = st.file_uploader("Choose a TCX file", type=["tcx"], accept_multiple_files=False)
ftp = st.number_input("Functional Threshold Power (FTP)", 0, 1000, 200)
st.caption("FTP is the highest average power you can sustain for approximately an hour, measured in watts.")

st.divider()

if uploaded_file is not None:
    # ----------------- SUMMARY -----------------
    st.header("Workout Summary")
    tcx_data = get_tcx_data(uploaded_file)
    df = tcx_to_df(tcx_data, kph=True)
    df["zone"] = df["power"].apply(lambda x: get_zone(x, ftp))

    st.map(df, latitude="latitude", longitude="longitude", size=1, use_container_width=True)

    moving_time_seconds = df[df["speed"] > 0].shape[0]
    power_avg = df["power"].mean()
    calories = power_avg * moving_time_seconds / 1000

    col1, col2, col3 = st.columns(3)
    col1.metric("Distance", f"{tcx_data.distance / 1000:.2f} km")
    col2.metric("Duration", f"{timedelta(seconds=tcx_data.duration)}")
    col3.metric("Moving Time", f"{timedelta(seconds=moving_time_seconds)}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Average Speed", f"{df['speed'].mean():.2f} km/h")
    col2.metric("Calories", f"{calories:.0f} kcal")
    col3.metric("Average Power", f"{power_avg:.0f} W")

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
    if df["cadence"].notna().sum() > len(df) / 2:
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
    if df["power"].notna().sum() > len(df) / 2:
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

        st.subheader("Max Power Effort")
        rolling_avg_durations = [
            "5s",
            "10s",
            "30s",
            "1m",
            "5m",
            "10m",
            "20m",
            "30m",
            "1h",
        ]
        rolling_avg_series = {}
        for duration in rolling_avg_durations:
            duration_seconds = int(pd.to_timedelta(duration).total_seconds())
            rolling_avg_series[duration] = df["power"].rolling(window=duration_seconds).mean().dropna()
        df_rolling_avg = pd.DataFrame(rolling_avg_series)
        df_rolling_avg_max = df_rolling_avg.max()
        df_rolling_avg_max = pd.DataFrame(df_rolling_avg_max).reset_index()
        df_rolling_avg_max.columns = ["Duration", "Max"]
        chart = (
            alt.Chart(df_rolling_avg_max)
            .mark_bar()
            .encode(y=alt.Y("Duration", sort=None), x=alt.X("Max", title="Max Power (W)"))
        )
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Training Intensity")
        col1, col2, col3 = st.columns(3)
        normalized_power = (rolling_avg_series["30s"] ** 4).mean() ** 0.25
        intensity_factor = normalized_power / ftp
        tss = intensity_factor**2 * moving_time_seconds / 3600 * 100
        col1.metric("NP", f"{normalized_power:.0f} W")
        col2.metric("IF", f"{intensity_factor:.2f}")
        col3.metric("TSS", f"{tss:.0f}")

        with st.expander("See how to calculate", expanded=True):
            st.write("NP = Normalized Power")
            st.latex(
                r"NP = \sqrt[4]{\frac{1}{T} \sum_{i=1}^{T} \overline{P_i}^4}, \text{where } \overline{P_i} = \text{30s moving average power}"
            )
            st.write("IF = Intensity Factor")
            st.latex(r"IF = \frac{NP}{FTP}")
            st.write("TSS = Training Stress Score")
            st.latex(r"TSS = \frac{{IF}^2 \times T}{ 3600 } \times 100, \text{where } T = \text{duration in seconds}")

            st.divider()
            st.page_link(
                "https://www.trainingpeaks.com/learn/articles/how-to-plan-your-season-with-training-stress-score/",
                label="Reference Training Volume Guidelines:",
                icon="ℹ️",
            )
            st.markdown(
                """
                | CATEGORY | ANNUAL HOURS | AVG. HRS/WEEK | ANNUAL TSS      | AVG. TSS/WEEK | TARGET CTL |
                |----------|--------------|---------------|-----------------|---------------|------------|
                | 1/2      | 700 - 1000   | 14 - 20       | 40,000 - 50,000 | 770 - 960     | 105 - 120  |
                | 3        | 500 - 700    | 9 - 14        | 25,000 - 35,000 | 480 - 673     | 85 - 95    |
                | 4        | 350 - 500    | 6 - 10        | 20,000 - 30,000 | 385 - 577     | 70 - 85    |
                | 5        | 220 - 350    | 3 - 8         | 10,000 - 20,000 | 192 - 385     | 50 - 70    |
                | Masters  | 350 - 650    | 8 - 12        | 15,000 - 25,000 | 288 - 480     | 60 - 100   |
                """
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

        # ----------------- SUMMARY -----------------
        if not st.session_state["summary"]:
            user_message = {
                "role": "user",
                "content": f"Debrief the user's workout in 50 words.\n{zone_counts_df}\nIntensity Factor = {intensity_factor}\nTraining Stress Score = {tss}.",
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

        # ----------------- CHAT -----------------
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
