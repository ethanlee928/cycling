import pandas as pd
from tcxreader.tcxreader import TCXReader, TCXTrackPoint

MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694

ZONES = [
    "Active Recovery",
    "Endurance",
    "Tempo",
    "Threshold",
    "VO2",
    "Anaerobic Capacity",
    "Neuromuscular Power",
]

ZONE_COLORS = ["gray", None, "blue", "green", "orange", "red", "violet"]


class Colors:
    GREY = "#3f3f3f"
    YELLOW = "#FEDD00"
    PURPLE = "#6A0DAD"
    ORANGE = "#F3742B"
    DARK_ORANGE = "#B83A14"
    BLUE_PURPLE = "#231650"


def get_tcx_data(tcx_file):
    reader = TCXReader()
    return reader.read(tcx_file)

def tcx_to_df(tcx_data, kph: bool) -> pd.DataFrame:
    trackpoint_data = []
    trackpoint: TCXTrackPoint

    for trackpoint in tcx_data.trackpoints:
        speed = trackpoint.tpx_ext.get("Speed")
        speed = speed * (MPS_TO_KPH if kph else MPS_TO_MPH)
        trackpoint_data.append(
            {
                "time": trackpoint.time,
                "distance": trackpoint.distance,
                "speed": speed,
                "power": trackpoint.tpx_ext.get("Watts"),
                "cadence": trackpoint.cadence,
                "latitude": trackpoint.latitude,
                "longitude": trackpoint.longitude,
                "elevation": trackpoint.elevation,
                "heart_rate": trackpoint.hr_value,
            }
        )
    df = pd.DataFrame(trackpoint_data)
    df.set_index("time", inplace=True)
    return df


def get_zone(power: float, ftp: float) -> int:
    zones_upper_thresh = [0.55, 0.75, 0.9, 1.05, 1.2, 1.5]
    percentage = power / ftp
    for idx, thresh in enumerate(zones_upper_thresh):
        if percentage < thresh:
            return idx
    return len(zones_upper_thresh)
