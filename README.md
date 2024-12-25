# Cycling

## Extract Stats from Strava

Common formats of sports: `TCX`, `GCX`, `FIT`

Steps to export `TCX` from Strava:

1. Login to [strava](https://www.strava.com/dashboard).
2. Click the activity you want to export.
3. "Simply add "/export_tcx" - without quotes - to the end of your activity page URL. For example, if your activity page is www.strava.com/activities/2865391236 - just add the text to give you www.strava.com/activities/2865391236/export_tcx and hit enter."

Reference:

- [Export tcx from Strava](https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export)
- [About file extension for sport activity](https://medium.com/decathlondigital/gpx-tcx-fit-how-to-choose-the-best-file-extension-for-sport-activity-transfer-403487337c04)

## Dependencies

```bash
python3 -m venv .venv
source .venv/bin/bash
pip3 install -r requirements.txt
```

## Basic Stats

Run the `stats.py` with the exported `.tcx` file as input.

```bash
python3 stats.py -i <your-activity>.tcx
```

![basic-stats](./images/afternoon_ride.png)


## Match Stats with Video

Run the `match_video.py` with the start time and end time of the video

```bash
python3 match_video.py --input-video <input.mp4> --input-file <input.tcx> --output-path <output.mp4> --kph --start-time <YYYY-MM-DD HH:MM:SS> --end-time <YYYY-MM-DD HH:MM:SS> --timezone <X>
```

![video-preview](./images/video-preview.jpg)

## Extract and Combine Audio

Use ffmpeg to extract the audio from original video:

```bash
docker run -it --rm -v ${PWD}:/app/ -w /app/ jrottenberg/ffmpeg -i <input-video> -vn -acodec copy <output-audio>.aac
```

Use ffmpeg to combine audio to output video:

```bash
docker run -it --rm -v ${PWD}:/app/ -w /app/ jrottenberg/ffmpeg -i <input-video> -i <input-audio>.aac -c:v copy -c:a aac <output-video>
```

## Fonts

`PIL` allows drawing texts with `.ttf` fonts. The [fonts](./fonts/) are downloaded from [fontspace](https://www.fontspace.com).
