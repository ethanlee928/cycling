from typing import List, Optional

import pandas as pd
from pydantic import BaseModel


class Activity(BaseModel):
    id: int
    type: str
    start_date_local: str


class BaseStream(BaseModel):
    original_size: int
    resolution: str
    series_type: str


class TimeStream(BaseStream):
    data: List[int]


class DistanceStream(BaseStream):
    data: List[float]


class SmoothVelocityStream(BaseStream):
    data: List[float]


class PowerStream(BaseStream):
    data: List[Optional[float]]


class CadenceStream(BaseStream):
    data: List[int]


class HeartRateStream(BaseStream):
    data: List[Optional[int]]


class LatLngStream(BaseStream):
    data: List[List[float]]


class StreamSet(BaseModel):
    time: Optional[TimeStream] = None
    distance: Optional[DistanceStream] = None
    velocity_smooth: Optional[SmoothVelocityStream] = None
    watts: Optional[PowerStream] = None
    cadence: Optional[CadenceStream] = None
    heartrate: Optional[HeartRateStream] = None
    latlng: Optional[LatLngStream] = None

    def to_df(self):
        """Convert the stream set to a DataFrame."""
        data = {}
        for stream_name, stream in self:
            if stream is not None:
                data[stream_name] = stream.data
        return pd.DataFrame(data) if data else None
