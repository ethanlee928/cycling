import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import altair as alt
import pandas as pd
import requests
import streamlit as st
from common.colors import Colors
from common.utils import load_cached_data
from dotenv import load_dotenv
from models import Activity, AthleteStats, StreamSet
from streamlit_oauth import OAuth2Component

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Example usage of logger
logger.info("New session started.")

load_dotenv()

st.title("Cyclist Performance Management 📈")

AUTHORIZE_URL = os.environ.get("STRAVA_OAUTH_AUTHORIZE_URL")
TOKEN_URL = os.environ.get("STRAVA_OAUTH_TOKEN_URL")
REFRESH_TOKEN_URL = os.environ.get("STRAVA_OAUTH_REFRESH_TOKEN_URL")
REVOKE_TOKEN_URL = os.environ.get("STRAVA_OAUTH_REVOKE_TOKEN_URL")
CLIENT_ID = os.environ.get("STRAVA_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_OAUTH_CLIENT_SECRET")
REDIRECT_URL = os.environ.get("STRAVA_OAUTH_REDIRECT_URL")
SCOPE = os.environ.get("STRAVA_OAUTH_SCOPE")

# Define the cache directory as a constant
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


class StravaOAuth2Component(OAuth2Component):
    """Solution from https://github.com/dnplus/streamlit-oauth/issues/59"""

    def __init__(self, *args, token_endpoint_auth_method="client_secret_post", **kwargs):
        super().__init__(*args, token_endpoint_auth_method=token_endpoint_auth_method, **kwargs)


oauth2 = StravaOAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    AUTHORIZE_URL,
    TOKEN_URL,
    REFRESH_TOKEN_URL,
    REVOKE_TOKEN_URL,
)


def get_athlete_stats(id: int) -> AthleteStats:
    """Fetch athlete stats and validate using Pydantic models."""
    token = st.session_state["token"]
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    url = f"https://www.strava.com/api/v3/athletes/{id}/stats"
    logger.info("Fetching athlete stats from %s", url)
    response = requests.get(url, headers=headers)
    logger.info("Response status: %d", response.status_code)
    if response.status_code == 200:
        return AthleteStats(**response.json())
    else:
        st.error(f"Failed to get athlete ({id}) stats: {response.status_code} - {response.text}")


def get_athlete_activities(id: int, t0: int, t1: int) -> List[Activity]:
    """Fetch athlete activities and validate using Pydantic models."""
    token = st.session_state["token"]
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    params = {
        "before": t1,
        "after": t0,
        "page": 1,
        "per_page": 30,
    }
    activities_data = []
    while True:
        logger.info("Fetching athlete activities with params: %s", params)
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params=params,
        )
        logger.info("Response status: %d", response.status_code)
        if response.status_code != 200:
            st.error(f"Failed to get athlete ({id}) activities: {response.status_code} - {response.text}")
            break
        data = response.json()
        activities_data.extend(data)
        if not data:
            break
        params["page"] += 1

    return [Activity(**activity) for activity in activities_data]


def filter_ride_activities(activities_data: List[Activity]) -> List[Activity]:
    """Filter activities to only include rides"""
    ride_activities = [activity for activity in activities_data if activity.type == "Ride"]
    return ride_activities


def get_activity_stream(activity_id: int, keys: List[str]) -> StreamSet:
    """http GET "https://www.strava.com/api/v3/activities/{id}/streams?keys=&key_by_type=" "Authorization: Bearer [[token]]"""
    _keys = ",".join(keys)
    token = st.session_state["token"]
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams?keys={_keys}&key_by_type=true"
    logger.info("Fetching activity stream data from %s", url)
    response = requests.get(url, headers=headers)
    logger.info("Response status: %d", response.status_code)
    if response.status_code == 200:
        return StreamSet(**response.json())
    else:
        st.error(f"Failed to get activity ({activity_id}) stream data: {response.status_code} - {response.text}")


def get_tss(df: pd.DataFrame, ftp: float) -> float:
    # moving_time_seconds = df[df["speed"] > 0].shape[0]
    pwr_rollings = df["watts"].rolling(window=30).mean().dropna()
    normalized_power = (pwr_rollings**4).mean() ** 0.25
    intensity_factor = normalized_power / ftp
    tss = intensity_factor**2 * len(df) / 3600 * 100
    return tss


# Check if token exists in session state
if "token" not in st.session_state:
    result = oauth2.authorize_button(
        name="Connect with Strava",
        redirect_uri=REDIRECT_URL,
        scope=SCOPE,
        key="strava",
    )
    if result and "token" in result:
        # If authorization successful, save token in session state
        st.session_state.token = result.get("token")
        st.rerun()
else:
    # If token exists in session state, show the token
    token = st.session_state["token"]

    # === Athlete Info ===
    athlete_dict = token.get("athlete")
    if athlete_dict:
        st.write("Authenticated with Strava ✅")
        st.image(athlete_dict["profile"], width=100)
        st.subheader(f"Welcome back, {athlete_dict['firstname']}!")
        st.header("All Time Efforts 🏆")
        stats = get_athlete_stats(athlete_dict["id"])
        all_ride_totals = stats.all_ride_totals
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Distance", f"{all_ride_totals.distance // 1000} km")
        with col2:
            st.metric("Total Elevation", f"{all_ride_totals.elevation_gain:.0f} m")
        with col3:
            st.metric("Total Rides", all_ride_totals.count)

        st.header(f"In {datetime.now().year} ... 🎯")
        ytd_ride_totals = stats.all_ride_totals
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("YTD Distance", f"{ytd_ride_totals.distance // 1000} km")
        with col2:
            st.metric("YTD Elevation", f"{ytd_ride_totals.elevation_gain:.0f} m")
        with col3:
            st.metric("YTD Rides", ytd_ride_totals.count)

    else:
        st.write("Oops! No athlete information available.")

    st.divider()

    st.write("Please enter your FTP and the desired time period (e.g., the past 90 days) to analyze.")
    st.write("⚠️ You will need a power meter for TSS calculation.")
    user_input_ftp = st.number_input("FTP (watts)", min_value=0, max_value=1000, value=200, step=1)
    user_time_period = st.number_input("Time Period (days)", min_value=1, max_value=365, value=90, step=1)

    activity_id_to_date = {}
    activity_id_to_df = {}
    activity_id_to_df = load_cached_data()

    # === Weekly TSS Graph ===
    epoch_time_0 = int((datetime.now() - timedelta(days=user_time_period)).timestamp())
    epoch_time_1 = int(datetime.now().timestamp())

    with st.status("Let me cook...", expanded=True) as status:
        st.write("Fetching activities from Strava...")
        activities_data = get_athlete_activities(athlete_dict["id"], epoch_time_0, epoch_time_1)
        st.write("Filtering ride activities...")
        ride_activities = filter_ride_activities(activities_data)
        ride_activities_id = [activity.id for activity in ride_activities if "id" in activity]
        for activity in ride_activities:
            activity_id_to_date[activity.id] = datetime.strptime(activity.start_date_local, "%Y-%m-%dT%H:%M:%SZ")

        # filter out activities in cache but out of time range
        activity_id_to_df = {
            activity_id: df for activity_id, df in activity_id_to_df.items() if activity_id in activity_id_to_date
        }

        st.write("Analyzing activities data...")
        stream_types = ["time", "distance", "velocity_smooth", "watts", "cadence"]
        for activity_id in ride_activities_id:
            if activity_id in activity_id_to_df:
                logger.info(
                    "Cached activity %s loaded for user %s.",
                    activity_id,
                    token["athlete"]["id"],
                )
                continue

            activity_stream = get_activity_stream(activity_id, stream_types)
            df = activity_stream.to_df()
            try:
                logger.info("Caching DataFrame to Parquet: %s", activity_id)
                df.to_parquet(CACHE_DIR / f"{activity_id}.parquet")
            except Exception as e:
                logger.error("Failed to save DataFrame to Parquet: %s", e, exc_info=True)
            activity_id_to_df[activity_id] = df

        assert len(activity_id_to_df) == len(activity_id_to_date), (
            f"Mismatch between activity_id_to_df and activity_id_to_date lengths: "
            f"{len(activity_id_to_df)} vs {len(activity_id_to_date)}"
        )

    st.write(f"Showing data for past {user_time_period} days: {len(ride_activities)} rides")

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

    # Create DataFrame for visualization
    df_tss = pd.DataFrame({"Week": [week.date() for week in weeks], "TSS": weekly_tss}).set_index("Week")

    st.header("Weekly Training Stress Score 📅")
    st.bar_chart(df_tss, color=Colors.ORANGE, use_container_width=True)
    with st.expander("Reference Training Volume Guidelines", expanded=True):
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
