from pydantic import BaseModel

from .athlete import Athlete


class Token(BaseModel):
    token_type: str
    expires_at: int
    expires_in: int
    refresh_token: str
    access_token: str
    athlete: Athlete
