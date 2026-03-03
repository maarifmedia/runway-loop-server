import os
import uuid
import threading
import subprocess
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

JOBS = {}
BASE_DIR = "/tmp/videos"
os.makedirs(BASE_DIR, exist_ok=True)

DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")


def upload_to_dropbox(local_path, dropbox_path):
    with open(local_path, "rb") as f:
        headers = {
            "Authorization": f"Bearer {DROPBOX_TOKEN}",
            "Dropbox-API-Arg": str({
                "path": dropbox_path,
                "mode": "overwrite",
                "autorename": True,
                "mute": False
            }).replace("'", '"'),
            "Content-Type": "application/octet-stream"
        }

        response = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers=headers,
            data=f
        )

        return response.status_code == 200


def run_ffmpeg(job_id, duration):
    try:
        input_path = os.path.join(BASE_DIR, f"{job_id}_input.mp4")
        output_path = os.path.join(BASE_DIR, f"{job_id}_loop.mp4")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", input_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                output_path
            ],
            check=True
        )

        dropbox_path = f"/youtube_outputs/{job_id}.mp4"

        success = upload_to_dropbox(output_path, dropbox_path)

        if success:
            JOBS[job_id]["status"] = "finished"
            JOBS[job_id]["dropbox_path"] = dropbox_path
        else:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = "Dropbox upload failed"

    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)


@app.route("/loop", methods=["POST"])
def start_loop():
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400

    file = request.files["file"]
    duration = request.form.get("duration", 3600)

    job_id = str(uuid.uuid4())
    input_path = os.path.join(BASE_DIR, f"{job_id}_input.mp4")
    file.save(input_path)

    JOBS[job_id] = {"status": "started"}

    thread = threading.Thread(
        target=run_ffmpeg,
        args=(job_id, duration)
    )
    thread.start()

    return jsonify({
        "status": "started",
        "job_id": job_id
    })


@app.route("/status/<job_id>", methods=["GET"])
def check_status(job_id):
    job = JOBS.get(job_id)

    if not job:
        return jsonify({"error": "job not found"}), 404

    return jsonify(job)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
