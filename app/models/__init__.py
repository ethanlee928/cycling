# This file will contain all Pydantic models for the app_v2 module.
from .activity import (
    Activity,
    BaseStream,
    CadenceStream,
    DistanceStream,
    HeartRateStream,
    LatLngStream,
    PowerStream,
    SmoothVelocityStream,
    StreamSet,
    TimeStream,
)
from .athlete import AthleteStats
from .token import Token
