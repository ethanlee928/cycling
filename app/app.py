import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import stravalib
import stravalib.client
import streamlit as st
from common import Colors, filter_ride_activities, get_tss, load_cached_data
from PIL import Image
from streamlit_oauth import OAuth2Component

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("app")

# Example usage of logger
logger.info("New session started.")

with Image.open("logos/ferociter.ico") as logo_ico:
    ferociter_logo = logo_ico.copy()
with Image.open("logos/ferociter_2x.jpg") as logo_png:
    ferociter_logo_png = logo_png.copy()
st.set_page_config(page_title="Ferociter", page_icon=ferociter_logo)

# Define the cache directory as a constant
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


class StravaOAuth2Component(OAuth2Component):
    """Solution from https://github.com/dnplus/streamlit-oauth/issues/59"""

    def __init__(self, *args, token_endpoint_auth_method="client_secret_post", **kwargs):
        super().__init__(*args, token_endpoint_auth_method=token_endpoint_auth_method, **kwargs)


oauth2 = StravaOAuth2Component(
    st.secrets.strava.client_id,
    st.secrets.strava.client_secret,
    st.secrets.strava.authorize_url,
    st.secrets.strava.token_url,
    st.secrets.strava.refresh_token_url,
    st.secrets.strava.revoke_token_url,
)


# Check if token exists in session state
if "token" not in st.session_state:
    st.image(ferociter_logo_png, width=250)
    st.title("Ferociter")
    st.markdown(
        "***Ferociter*** is a Latin word meaning *to be fierce* or *to be brave*. This platform helps you track and analyze your cycling performance, empowering you to push your limits with ferocity."
    )
    st.markdown("*Never Settle.*")
    result = oauth2.authorize_button(
        name="Connect with Strava",
        icon="btn_strava_connect_with_orange_x2.png",
        redirect_uri=st.secrets.strava.redirect_url,
        scope=st.secrets.strava.scope,
        key="strava",
    )
    if result and "token" in result:
        # If authorization successful, save token in session state
        st.session_state.token = result.get("token")
        st.rerun()
else:
    st.header("Cycling Performance Management", divider="orange")
    os.environ["STRAVA_CLIENT_ID"] = st.secrets.strava.client_id
    os.environ["STRAVA_CLIENT_SECRET"] = st.secrets.strava.client_secret
    client = stravalib.client.Client(access_token=st.session_state["token"]["access_token"])
    athlete = client.get_athlete()
    st.write("Authenticated with Strava ✅")
    st.image(athlete.profile, width=100)
    st.subheader(f"Welcome back, {athlete.firstname}!")
    st.header("All Time Efforts 🏆")
    stats = client.get_athlete_stats(athlete.id)
    all_ride_totals = stats.all_ride_totals
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Distance", f"{all_ride_totals.distance // 1000} km")
    with col2:
        st.metric("Total Elevation", f"{all_ride_totals.elevation_gain:.0f} m")
    with col3:
        st.metric("Total Rides", all_ride_totals.count)

    st.header(f"In {datetime.now().year} ... 🎯")
    ytd_ride_totals = stats.ytd_ride_totals
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("YTD Distance", f"{ytd_ride_totals.distance // 1000} km")
    with col2:
        st.metric("YTD Elevation", f"{ytd_ride_totals.elevation_gain:.0f} m")
    with col3:
        st.metric("YTD Rides", ytd_ride_totals.count)

    st.divider()

    st.write("Please enter your FTP and the desired time period (e.g., the past 90 days) to analyze.")
    st.write("⚠️ You will need a power meter for TSS calculation.")
    user_input_ftp = st.number_input("FTP (watts)", min_value=0, max_value=1000, value=200, step=1)
    user_time_period = st.number_input("Time Period (days)", min_value=1, max_value=365, value=90, step=1)

    activity_id_to_date = {}
    activity_id_to_df = load_cached_data(CACHE_DIR, athlete.id)

    # === Weekly TSS Graph ===
    epoch_time_0 = int((datetime.now() - timedelta(days=user_time_period)).timestamp())
    epoch_time_1 = int(datetime.now().timestamp())

    with st.spinner("Loading activities data...", show_time=True):
        activities_data = client.get_activities(
            before=datetime.now(), after=datetime.now() - timedelta(days=user_time_period)
        )
        ride_activities = filter_ride_activities(activities_data)
        ride_activities_id = [activity.id for activity in ride_activities]
        for activity in ride_activities:
            activity_id_to_date[activity.id] = activity.start_date_local
        # filter out activities in cache but out of time range
        activity_id_to_df = {
            activity_id: df for activity_id, df in activity_id_to_df.items() if activity_id in activity_id_to_date
        }

        stream_types = ["time", "distance", "velocity_smooth", "watts", "cadence"]
        for activity_id in ride_activities_id:
            if activity_id in activity_id_to_df:
                logger.info("Cached activity %s loaded for user %s.", activity_id, athlete.id)
                continue
            activity_stream = client.get_activity_streams(activity_id, types=stream_types)
            df = pd.DataFrame(
                {stream_type: stream.data for stream_type, stream in activity_stream.items() if stream is not None}
            )
            try:
                user_cache_dir = CACHE_DIR / str(athlete.id)
                user_cache_dir.mkdir(exist_ok=True, parents=True)
                cache_path = user_cache_dir / f"{activity_id}.parquet"
                logger.info("Caching DataFrame to Parquet @ %s", cache_path)
                df.to_parquet(cache_path)
            except Exception as e:
                logger.error("Failed to save DataFrame to Parquet: %s", e, exc_info=True)
            activity_id_to_df[activity_id] = df

        assert len(activity_id_to_df) == len(activity_id_to_date), (
            f"Mismatch between activity_id_to_df and activity_id_to_date lengths: "
            f"{len(activity_id_to_df)} vs {len(activity_id_to_date)}"
        )
        st.toast("Activities data loaded successfully!", icon="✅")
    st.success(f"Showing data for past {user_time_period} days: {len(ride_activities)} rides")

    # --- Weekly TSS ---
    today = datetime.today()
    weeks = pd.date_range(end=today, periods=52, freq="W-MON").to_pydatetime()

    # Use activity_id_to_date and activity_id_to_df
    start_times = [activity_id_to_date[activity_id] for activity_id in activity_id_to_df.keys()]
    l_tss = [get_tss(activity_id_to_df[activity_id], user_input_ftp) for activity_id in activity_id_to_df.keys()]
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
            weekly_tss[index_map[week_monday]] += round(tss, 1)

    df_tss = pd.DataFrame({"Week": [week.date() for week in weeks], "TSS": weekly_tss}).set_index("Week")

    st.header("Weekly Training Stress Score 📅")
    st.bar_chart(df_tss, color=Colors.ORANGE, use_container_width=True)
    with st.expander("Reference Training Volume Guidelines", expanded=True):
        training_volume_guidelines = {
            "CATEGORY": ["1/2", "3", "4", "5", "Masters"],
            "ANNUAL HOURS": [
                "700 - 1000",
                "500 - 700",
                "350 - 500",
                "220 - 350",
                "350 - 650",
            ],
            "AVG. HRS/WEEK": ["14 - 20", "9 - 14", "6 - 10", "3 - 8", "8 - 12"],
            "ANNUAL TSS": [
                "40,000 - 50,000",
                "25,000 - 35,000",
                "20,000 - 30,000",
                "10,000 - 20,000",
                "15,000 - 25,000",
            ],
            "AVG. TSS/WEEK": [
                "770 - 960",
                "480 - 673",
                "385 - 577",
                "192 - 385",
                "288 - 480",
            ],
            "TARGET CTL": ["105 - 120", "85 - 95", "70 - 85", "50 - 70", "60 - 100"],
        }
        st.table(pd.DataFrame(training_volume_guidelines).set_index("CATEGORY"))
        st.page_link(
            "https://www.trainingpeaks.com/learn/articles/how-to-plan-your-season-with-training-stress-score/",
            label="Extracted from trainingpeaks.com. Click to read more.",
            icon="ℹ️",
        )

    # === Performance Management Chart ===
    st.header("Performance Management Chart 📊")

    a_ctl = 2 / (42 + 1)
    a_atl = 2 / (7 + 1)

    date_to_tss = defaultdict(lambda: 0.0)
    for tss, start_time in zip(l_tss, start_times):
        date = start_time.date()
        date_to_tss[date] += tss

    start_date = datetime.today() - timedelta(days=user_time_period)
    training_load = {"Date": [], "CTL": [], "ATL": [], "TSB": []}
    for i in range(user_time_period + 1):
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
    training_load_df.reset_index(inplace=True)
    base = (
        alt.Chart(training_load_df)
        .transform_fold(["CTL", "ATL", "TSB"], as_=["Metric", "Value"])
        .encode(
            x="Date:T",
            color=alt.Color(
                "Metric:N",
                scale=alt.Scale(
                    domain=["CTL", "ATL", "TSB"],
                    range=[Colors.BLUE, Colors.YELLOW, Colors.PINK],
                ),
            ),
        )
    )

    line_ctl = base.transform_filter(alt.datum.Metric == "CTL").mark_line().encode(alt.Y("CTL:Q"))
    line_atl = base.transform_filter(alt.datum.Metric == "ATL").mark_line().encode(alt.Y("ATL:Q"))
    line_tsb = base.transform_filter(alt.datum.Metric == "TSB").mark_line().encode(alt.Y("TSB:Q"))

    combined_chart = alt.layer(line_tsb, line_ctl + line_atl).resolve_scale(y="independent")
    st.altair_chart(combined_chart, use_container_width=True)

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

    with st.expander("How to interpret the chart?", expanded=True):
        st.caption("- Overly negative TSB can indicate overtraining.")
        st.caption("- Most coaches generally guide towards maintaining TSB value above -30.")
        st.caption("- Closer to 0 TSB indicates peak performance, recommended for race day.")

# === Copyright Footer ====
st.divider()
st.image("logos/api_logo_pwrdBy_strava_stack_white.png", width=100)
st.caption("Copyright © 2025 Ethan S.C. Lee.")
