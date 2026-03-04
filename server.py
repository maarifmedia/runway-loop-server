import os
import uuid
import subprocess
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

jobs = {}

DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")

CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

def upload_large_file(file_path, dropbox_path):
    headers = {
        "Authorization": f"Bearer {DROPBOX_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    file_size = os.path.getsize(file_path)

    with open(file_path, "rb") as f:
        # START SESSION
        start_url = "https://content.dropboxapi.com/2/files/upload_session/start"
        start_headers = headers.copy()
        start_headers["Dropbox-API-Arg"] = '{"close": false}'
        start_res = requests.post(start_url, headers=start_headers, data=f.read(CHUNK_SIZE))
        session_id = start_res.json()["session_id"]

        cursor = {
            "session_id": session_id,
            "offset": f.tell()
        }

        # APPEND CHUNKS
        while f.tell() < file_size:
            append_url = "https://content.dropboxapi.com/2/files/upload_session/append_v2"
            append_headers = headers.copy()
            append_headers["Dropbox-API-Arg"] = str({
                "cursor": cursor,
                "close": False
            }).replace("'", '"')

            chunk = f.read(CHUNK_SIZE)
            requests.post(append_url, headers=append_headers, data=chunk)

            cursor["offset"] = f.tell()

        # FINISH SESSION
        finish_url = "https://content.dropboxapi.com/2/files/upload_session/finish"
        finish_headers = headers.copy()
        finish_headers["Dropbox-API-Arg"] = str({
            "cursor": cursor,
            "commit": {
                "path": dropbox_path,
                "mode": "add",
                "autorename": True,
                "mute": False
            }
        }).replace("'", '"')

        requests.post(finish_url, headers=finish_headers)

@app.route("/loop", methods=["POST"])
def loop_video():
    data = request.json
    video_url = data.get("video_url")
    duration = int(data.get("duration"))

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "started"}

    input_path = f"/tmp/{job_id}_input.mp4"
    output_path = f"/tmp/{job_id}_output.mp4"

    subprocess.run(["wget", "-O", input_path, video_url])

    ffmpeg_command = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy",
        output_path
    ]

    subprocess.run(ffmpeg_command)

    dropbox_path = f"/youtube_outputs/{job_id}.mp4"

    upload_large_file(output_path, dropbox_path)

    jobs[job_id] = {
        "status": "finished",
        "dropbox_path": dropbox_path
    }

    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    return jsonify(jobs.get(job_id, {"status": "not_found"}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
