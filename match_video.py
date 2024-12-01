import argparse
import time
from datetime import timedelta
from pathlib import Path

import cv2
import pandas as pd
from tcxreader.tcxreader import TCXReader, TCXTrackPoint
from tqdm import tqdm

# Constants
MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694


def play_video(args):
    # Initialize TCXReader and read data from the provided file path
    print("Loading TCX file")
    reader = TCXReader()
    input_file = Path(args.input_file)
    input_video = Path(args.input_video)
    data = reader.read(str(input_file))

    trackpoint_data = []
    trackpoint: TCXTrackPoint

    # Adjust timezone based on user input
    timezone_offset = timedelta(hours=args.timezone)

    for trackpoint in tqdm(data.trackpoints):
        time_adjusted = trackpoint.time + timezone_offset
        speed = trackpoint.tpx_ext.get("Speed")
        power = trackpoint.tpx_ext.get("Watts")

        if args.kph:
            speed_kph = speed * MPS_TO_KPH
        else:
            speed_kph = speed * MPS_TO_MPH

        trackpoint_data.append(
            {
                "Time": time_adjusted,
                "Speed": speed_kph,
                "Elevation": trackpoint.elevation,
                "Power": power,
            }
        )

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(trackpoint_data)
    df.set_index("Time", inplace=True)
    print("Loading TCX file [DONE]")
    start_time = pd.to_datetime("2024-11-21 13:35:40")
    end_time = pd.to_datetime("2024-11-21 13:36:50")
    filtered_df = df[(df.index >= start_time) & (df.index <= end_time)]

    df_iter = filtered_df.iterrows()
    cap = cv2.VideoCapture(args.input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    output_filename = input_file.stem + "-output.avi"
    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

    idx = 0
    process_time_ms, process_fps = 0, 0
    speed, elevation = 0, 0

    if not cap.isOpened():
        print("Error opening video file")
        return

    while True:
        t1 = time.monotonic()
        ret, frame = cap.read()
        if idx % fps == 0:
            timestamp, row = next(df_iter)
            if row is not None:
                speed = row["Speed"]
                elevation = row["Elevation"]
                power = row["Power"]
                print(
                    f"{timestamp}: Speed: {speed:.2f} km/h | Elevation: {elevation:.1f} m | process time (ms) {process_time_ms:.1f} | process fps {process_fps:.1f}"
                )
            else:
                speed, elevation, power = 0, 0, 0

        if not ret:
            print("End of video")
            break

        height, width, _ = frame.shape
        # speed row
        color = (255, 255, 255)
        cv2.putText(frame, "KMH", (200, 700), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 10, cv2.LINE_AA)
        cv2.putText(frame, f"{speed:.1f}", (200, 800), cv2.FONT_HERSHEY_SIMPLEX, 3, color, 15, cv2.LINE_AA)

        # pwr row
        cv2.putText(frame, "PWR", (200, 900), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 10, cv2.LINE_AA)
        cv2.putText(frame, f"{power}", (200, 1000), cv2.FONT_HERSHEY_SIMPLEX, 3, color, 15, cv2.LINE_AA)

        # elevation row
        cv2.putText(frame, "Elev", (200, 1100), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 10, cv2.LINE_AA)
        cv2.putText(frame, f"{elevation:.1f}", (200, 1200), cv2.FONT_HERSHEY_SIMPLEX, 3, color, 15, cv2.LINE_AA)

        if args.debug:
            cv2.imshow("Video Playback", frame)
            if cv2.waitKey(25) & 0xFF == ord("q"):
                break
        else:
            out.write(frame)
        idx += 1
        t2 = time.monotonic()
        process_time_ms = (t2 - t1) * 100
        process_fps = 1 / (t2 - t1)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process TCX files for ride data visualization.")
    parser.add_argument("--input-file", type=str, help="Path to the TCX file to process.")
    parser.add_argument("--input-video", type=str, help="Patht to video file")
    parser.add_argument("--kph", action="store_true", help="Convert speed from mph to kph.")
    parser.add_argument(
        "--timezone",
        type=int,
        default=8,
        help="Timezone offset in hours (default is 8 for HKT).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: use cv2.imshow instead of saving video",
    )

    args = parser.parse_args()
    play_video(args)
