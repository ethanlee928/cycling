import logging
from typing import List

import requests
from models import Activity, AthleteStats, StreamSet, Token


class StravaAPI:
    def __init__(self, token: Token):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token.access_token}"}

    def get_athlete_stats(self, athlete_id: int) -> AthleteStats:
        """Fetch athlete stats and validate using Pydantic models."""
        url = f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats"
        self.logger.info("Fetching athlete stats from %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.info("Response status: %d", response.status_code)
        if response.status_code == 200:
            return AthleteStats(**response.json())
        else:
            raise Exception(f"Failed to fetch athlete stats: {response.status_code} - {response.text}")

    def get_athlete_activities(self, athlete_id: int, t0: int, t1: int) -> List[Activity]:
        """Fetch athlete activities and validate using Pydantic models."""
        url = "https://www.strava.com/api/v3/athlete/activities"
        params = {"before": t1, "after": t0, "page": 1, "per_page": 30}
        activities_data = []

        while True:
            self.logger.info("Fetching athlete activities with params: %s", params)
            response = requests.get(url, headers=self.headers, params=params)
            self.logger.info("Response status: %d", response.status_code)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch activities: {response.status_code} - {response.text}")

            data = response.json()
            activities_data.extend(data)
            if not data:
                break
            params["page"] += 1

        return [Activity(**activity) for activity in activities_data]

    def get_activity_stream(self, activity_id: int, keys: List[str]) -> StreamSet:
        """Fetch activity stream data."""
        _keys = ",".join(keys)
        url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams?keys={_keys}&key_by_type=true"
        self.logger.info("Fetching activity stream data from %s", url)
        response = requests.get(url, headers=self.headers)
        self.logger.info("Response status: %d", response.status_code)
        if response.status_code == 200:
            return StreamSet(**response.json())
        else:
            raise Exception(f"Failed to fetch activity stream: {response.status_code} - {response.text}")
