from pydantic import BaseModel


class RideTotals(BaseModel):
    distance: float
    elevation_gain: float
    count: int


class AthleteStats(BaseModel):
    all_ride_totals: RideTotals
    ytd_ride_totals: RideTotals
