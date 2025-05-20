from typing import Optional

from pydantic import BaseModel


class RideTotals(BaseModel):
    distance: float
    elevation_gain: float
    count: int


class AthleteStats(BaseModel):
    all_ride_totals: RideTotals
    ytd_ride_totals: RideTotals


class Athlete(BaseModel):
    """There're more fields in the API, but we only need these for now.
    https://developers.strava.com/docs/reference/#api-models-DetailedAthlete"""

    id: int
    firstname: str
    lastname: str
    profile: str  # URL to profile picture
    premium: bool
    weight: Optional[float]
