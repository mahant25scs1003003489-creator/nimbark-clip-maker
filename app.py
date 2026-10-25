import os
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# FFmpeg ka path
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# yt-dlp ko FFmpeg ka path batana
os.environ["PATH"] = str(Path(FFMPEG).parent) + os.pathsep + os.environ.get("PATH", "")


def time_to_seconds(value):
    parts = value.strip().split(":")

    if len(parts) != 3:
        raise ValueError("Time HH:MM:SS format mein daalo.")

    hours, minutes, seconds = map(int, parts)

    if hours < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError("Time format galat hai.")

    return hours * 3600 + minutes * 60 + seconds


@app.route("/", methods=["GET", "POST"])
def home():
    message = ""

    if request.method == "POST":
        try:
            url = request.form.get("video_url", "").strip()
            start = time_to_seconds(request.form.get("start_time", ""))
            end = time_to_seconds(request.form.get("end_time", ""))
            quality = request.form.get("quality", "720")

            if not re.fullmatch(
                r"https?://(www\.)?(youtube\.com|youtu\.be)/.+", url
            ):
                raise ValueError("Valid YouTube URL daalo.")

            if end <= start:
                raise ValueError("End time, start time se aage hona chahiye.")

            if quality not in {"360", "480", "720", "1080"}:
                raise ValueError("Sahi video quality select karo.")

            # Purani temporary files hatana
            for old_file in DOWNLOAD_DIR.glob("source.*"):
                old_file.unlink()

            output_file = DOWNLOAD_DIR / "Bhajan_Clip.mp4"
            temp_template = str(DOWNLOAD_DIR / "source.%(ext)s")

            options = {
                "format": (
                    f"bestvideo[height<={quality}]+bestaudio/"
                    f"best[height<={quality}]"
                ),
                "outtmpl": temp_template,
                "merge_output_format": "mp4",
                "ffmpeg_location": FFMPEG,
                "noplaylist": True,
            }

            # YouTube video download karna
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                source = Path(ydl.prepare_filename(info))

            # Downloaded file ka sahi path dhoondhna
            if not source.exists():
                candidates = [
                    p for p in DOWNLOAD_DIR.glob("source.*")
                    if p.suffix.lower() in {".mp4", ".mkv", ".webm"}
                ]

                if not candidates:
                    raise RuntimeError("Downloaded video file nahi mili.")

                source = candidates[0]

            # Selected section ko MP4 mein trim karna
            command = [
                FFMPEG,
                "-y",
                "-ss", str(start),
                "-i", str(source),
                "-t", str(end - start),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output_file),
            ]

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

            return send_file(
                output_file,
                as_attachment=True,
                download_name="Bhajan_Clip.mp4",
                mimetype="video/mp4",
            )

        except Exception as exc:
            message = f"Error: {exc}"

    return render_template("index.html", message=message)


if __name__ == "__main__":
    app.run(debug=False)