import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


def load_cached_data():
    """Load all Parquet files from the cache directory as a dictionary."""
    parquet_files = list(CACHE_DIR.glob("*.parquet"))
    logger.info("Loading cached data from %s", CACHE_DIR)
    logger.info("Found Parquet files: %s", [file.name for file in parquet_files])
    activity_id_to_df = {int(file.stem): pd.read_parquet(file) for file in parquet_files}
    return activity_id_to_df
