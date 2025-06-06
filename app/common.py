import logging
from pathlib import Path
from typing import List

import pandas as pd
from stravalib import model

logger = logging.getLogger(__name__)


class Colors:
    GREY = "#3f3f3f"
    YELLOW = "#FEDD00"
    PURPLE = "#6A0DAD"
    ORANGE = "#F3742B"
    DARK_ORANGE = "#B83A14"
    BLUE_PURPLE = "#231650"
    PINK = "#B52F9C"
    BLUE = "#1D1BF9"


def load_cached_data(cache_dir: Path, user_id: int):
    """Load all Parquet files from the cache directory as a dictionary."""
    user_cache_dir = cache_dir / str(user_id)
    if not user_cache_dir.exists():
        logger.info("Cache directory %s does not exist for user %d", user_cache_dir, user_id)
        return {}
    parquet_files = list(user_cache_dir.glob("*.parquet"))
    logger.info("Loading cached data from %s", user_cache_dir)
    activity_id_to_df = {int(file.stem): pd.read_parquet(file) for file in parquet_files}
    return activity_id_to_df


def filter_ride_activities(activities_data: List[model.SummaryActivity]) -> List[model.SummaryActivity]:
    """Filter activities to only include rides"""
    ride_activities = [activity for activity in activities_data if activity.type == "Ride"]
    return ride_activities


def get_tss(df: pd.DataFrame, ftp: float) -> float:
    # moving_time_seconds = df[df["speed"] > 0].shape[0]
    pwr_rollings = df["watts"].rolling(window=30).mean().dropna()
    normalized_power = (pwr_rollings**4).mean() ** 0.25
    intensity_factor = normalized_power / ftp
    tss = intensity_factor**2 * len(df) / 3600 * 100
    return tss
