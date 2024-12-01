import argparse
from datetime import timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from tcxreader.tcxreader import TCXReader, TCXTrackPoint
from tqdm import tqdm

# Constants
MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694


def main(args):
    # Initialize TCXReader and read data from the provided file path
    reader = TCXReader()
    input_file = Path(args.input_file)
    activity_name = input_file.stem
    data = reader.read(str(input_file))

    trackpoint_data = []
    trackpoint: TCXTrackPoint

    # Adjust timezone based on user input
    timezone_offset = timedelta(hours=args.timezone)

    for trackpoint in tqdm(data.trackpoints):
        time_adjusted = trackpoint.time + timezone_offset
        speed = trackpoint.tpx_ext.get("Speed")

        # Convert speed based on the flag
        if args.kph:
            speed_kph = speed * MPS_TO_KPH
        else:
            speed_kph = speed * MPS_TO_MPH

        trackpoint_data.append(
            {
                "Time": time_adjusted,
                "Speed": speed_kph,
                "Elevation": trackpoint.elevation,
            }
        )

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(trackpoint_data)
    df.set_index("Time", inplace=True)

    # Create a figure and two subplots
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # Plot the speed on the first y-axis
    ax1.plot(df.index, df["Speed"], label="Speed", color="blue")
    ax1.set_ylabel("Speed (km/h)" if args.kph else "Speed (mph)")
    ax1.legend(loc="upper left")

    # Plot the elevation on the second y-axis
    ax2.plot(df.index, df["Elevation"], label="Elevation", color="red")
    ax2.set_ylabel("Elevation (m)")
    ax2.legend(loc="upper right")

    plt.xlabel("Time")
    plt.title(activity_name)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process TCX files for ride data visualization.")
    parser.add_argument("input_file", type=str, help="Path to the TCX file to process.")
    parser.add_argument("--kph", action="store_true", help="Convert speed from mph to kph.")
    parser.add_argument(
        "--timezone",
        type=int,
        default=8,
        help="Timezone offset in hours (default is 8 for HKT).",
    )
    args = parser.parse_args()
    main(args)
