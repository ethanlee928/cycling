import argparse
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tcxreader.tcxreader import TCXReader, TCXTrackPoint
from tqdm import tqdm

MPS_TO_KPH = 3.6
MPS_TO_MPH = 2.23694


def get_font(fontsize: int, name: str = "american-captain"):
    available_fonts = {
        "american-captain": "fonts/american-captain-font/AmericanCaptain-MdEY.ttf",
        "damion": "/Users/ethanlee/Desktop/projects/cycling/fonts/damion-font/Damion-8gnD.ttf",
    }
    return ImageFont.truetype(available_fonts[name], fontsize)


class Colors:
    """Colors in BGRA"""

    WHITE = (255, 255, 255, 1)
    RED = (0, 0, 255, 1)
    GREEN = (0, 255, 0, 1)
    BLUE = (255, 0, 0, 1)
    BLACK = (0, 0, 0, 1)


@dataclass
class TextDrawInstruction:
    text: str
    xy: Tuple[int, int]
    color: Tuple = Colors.WHITE
    font: Optional[ImageFont.FreeTypeFont] = None


def draw_text(frame: np.ndarray, instructions: List[TextDrawInstruction]) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)
    for instruction in instructions:
        draw.text(instruction.xy, instruction.text, fill=instruction.color, font=instruction.font)
    return np.array(image)


def draw_text_rows(
    text_rows: List[Tuple[str, str]],
    start_xy: Tuple[int, int],
    fontsizes: Optional[Tuple[int, int]] = None,
    line_spacing: Optional[Tuple[int, int]] = None,
    color: Tuple = Colors.WHITE,
) -> List[TextDrawInstruction]:
    _fontsizes = (100, 200) if fontsizes is None else fontsizes
    _line_spacing = (90, 200) if line_spacing is None else line_spacing

    instructions = []
    x, y = start_xy
    for desc, value in text_rows:
        desc_instruction = TextDrawInstruction(desc, (x, y), color=color, font=get_font(_fontsizes[0]))
        y += _line_spacing[0]
        value_instruction = TextDrawInstruction(value, (x, y), color=color, font=get_font(_fontsizes[1]))
        y += _line_spacing[1]
        instructions += [desc_instruction, value_instruction]
    return instructions


def tcx_to_df(tcx_file: Path, timezone: int, kph: bool) -> pd.DataFrame:
    reader = TCXReader()
    data = reader.read(str(tcx_file))
    trackpoint_data = []
    trackpoint: TCXTrackPoint
    timezone_offset = timedelta(hours=timezone)

    for trackpoint in tqdm(data.trackpoints):
        time_adjusted = trackpoint.time + timezone_offset
        speed = trackpoint.tpx_ext.get("Speed")
        power = trackpoint.tpx_ext.get("Watts")

        speed = speed * (MPS_TO_KPH if kph else MPS_TO_MPH)
        trackpoint_data.append(
            {
                "Time": time_adjusted,
                "Speed": speed,
                "Elevation": trackpoint.elevation,
                "Power": power,
            }
        )
    df = pd.DataFrame(trackpoint_data)
    df.set_index("Time", inplace=True)
    return df


def play_video(args):
    print("Loading TCX file")
    input_video = Path(args.input_video)
    df = tcx_to_df(Path(args.input_file), args.timezone, args.kph)
    print("Loading TCX file [DONE]")

    start_time = pd.to_datetime("2024-11-21 13:35:02")
    end_time = pd.to_datetime("2024-11-21 13:42:41")
    filtered_df = df[(df.index >= start_time) & (df.index <= end_time)]

    df_iter = filtered_df.iterrows()
    cap = cv2.VideoCapture(args.input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    output_filename = input_video.stem + "-output.mp4" if args.output_path is None else args.output_path
    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

    idx = 0
    process_fps = 0
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
                power = power if not np.isnan(power) else 0.0
                print(f"{timestamp}: Process {idx}/{total_frames} frames, process FPS {process_fps:.1f}")
            else:
                speed, elevation, power = 0, 0, 0

        if not ret:
            print("End of video")
            break

        height, width, _ = frame.shape
        text_overlay = frame.copy()

        text_rows = [("KMH", str(round(speed))), ("PWR", str(round(power))), ("ALT", str(round(elevation)))]
        instructions = draw_text_rows(text_rows, start_xy=(300, 350))
        instructions.append(
            TextDrawInstruction("Chillriders Production", (width - 500, height - 100), font=get_font(50, "damion"))
        )
        text_overlay = draw_text(text_overlay, instructions=instructions)

        # Blend the text overlay with the original frame with transparency level (alpha)
        alpha = 0.8
        output_frame = cv2.addWeighted(text_overlay, alpha, frame, 1 - alpha, 0)
        if args.debug:
            cv2.imshow("Video Playback", output_frame)
            if cv2.waitKey(25) & 0xFF == ord("q"):
                break
        else:
            out.write(output_frame)
        idx += 1
        t2 = time.monotonic()
        process_fps = 1 / (t2 - t1)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process TCX files for ride data visualization.")
    parser.add_argument("--input-file", type=str, required=True, help="Path to the TCX file to process.")
    parser.add_argument("--input-video", type=str, required=True, help="Patht to video file")
    parser.add_argument("--output-path", type=str, default=None, help="Path of output video")
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
