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
    data: List[float]


class CadenceStream(BaseStream):
    data: List[int]


class HeartRateStream(BaseStream):
    data: List[int]


class LatLngStream(BaseStream):
    data: List[List[float]]


class StreamSet(BaseModel):
    time: Optional[TimeStream]
    distance: Optional[DistanceStream]
    velocity_smooth: Optional[SmoothVelocityStream]
    watts: Optional[PowerStream]
    cadence: Optional[CadenceStream]
    heartrate: Optional[HeartRateStream]
    latlng: Optional[LatLngStream]

    def to_df(self):
        """Convert the stream set to a DataFrame."""
        data = {}
        for stream_name, stream in self:
            if stream is not None:
                data[stream_name] = stream.data
        return pd.DataFrame(data) if data else None
