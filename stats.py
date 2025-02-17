import argparse
from datetime import timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from tcxreader.tcxreader import TCXReader, TCXTrackPoint
from tqdm import tqdm

MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694


def main(args):
    reader = TCXReader()
    input_file = Path(args.input_file)
    activity_name = input_file.stem
    data = reader.read(str(input_file))

    trackpoint_data = []
    trackpoint: TCXTrackPoint

    timezone_offset = timedelta(hours=args.timezone)

    for trackpoint in tqdm(data.trackpoints):
        time_adjusted = trackpoint.time + timezone_offset
        speed = trackpoint.tpx_ext.get("Speed")
        speed = speed * (MPS_TO_KPH if args.kph else MPS_TO_MPH)

        trackpoint_data.append(
            {
                "time": time_adjusted,
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

    if args.save_csv:
        output_file = input_file.with_suffix(".csv")
        df.to_csv(output_file)
        print(f"Processed data saved to {output_file}")

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # Plot the speed on the first y-axis
    ax1.plot(df.index, df["speed"], label="Speed", color="blue")
    ax1.set_ylabel("Speed (km/h)" if args.kph else "Speed (mph)")
    ax1.legend(loc="upper left")

    # Plot the elevation on the second y-axis
    ax2.plot(df.index, df["elevation"], label="Elevation", color="red")
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
    parser.add_argument("--save-csv", action="store_true", help="Save the processed data to a CSV file.")
    args = parser.parse_args()
    main(args)
