import os
import uuid
import subprocess
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

jobs = {}

def get_access_token():
    url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "refresh_token": YOUTUBE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    r = requests.post(url, data=data)
    return r.json()["access_token"]


def upload_youtube(video_path, title):

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    metadata = {
        "snippet": {
            "title": title,
            "description": "Auto uploaded video",
            "tags": ["loop"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"

    r = requests.post(init_url, headers=headers, json=metadata)

    upload_url = r.headers["Location"]

    with open(video_path, "rb") as f:

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4"
        }

        requests.put(upload_url, headers=headers, data=f)


@app.route("/loop", methods=["POST"])
def loop_video():

    data = request.json
    video_url = data.get("video_url")
    duration = int(data.get("duration"))

    job_id = str(uuid.uuid4())

    input_path = f"/tmp/{job_id}_input.mp4"
    output_path = f"/tmp/{job_id}_output.mp4"

    subprocess.run(["wget", "-O", input_path, video_url])

    loop_count = int(duration / 8)


ffmpeg_command = [
    "ffmpeg",
    "-loop", "1",
    "-i", "image.jpg",
    "-i", "audio.mp3",
    "-c:v", "libx264",
    "-t", "3600",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    "output.mp4"
]

subprocess.run(ffmpeg_command)

    upload_youtube(output_path, f"Loop Video {job_id}")

    return jsonify({"status": "uploaded"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
