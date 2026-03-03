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


def download_file(url, path):
    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()

    with open(path, "wb") as f:
        f.write(r.content)


def run_ffmpeg(job_id, input_url, duration):
    try:
        input_path = os.path.join(BASE_DIR, f"{job_id}_input.mp4")

        download_file(input_url, input_path)

        size = os.path.getsize(input_path)

        # Eğer 500KB'dan küçükse büyük ihtimal HTML
        if size < 500000:
            with open(input_path, "rb") as f:
                preview = f.read(300)
            raise Exception(f"Downloaded file too small ({size} bytes). First bytes: {preview}")

        # Test decode only (no encode yet)
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path],
            check=True
        )

        JOBS[job_id]["status"] = "finished"

    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)


@app.route("/loop", methods=["POST"])
def start_loop():
    data = request.json
    input_url = data.get("input_url")
    duration = data.get("duration")

    if not input_url or not duration:
        return jsonify({"error": "input_url and duration required"}), 400

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "started"}

    thread = threading.Thread(
        target=run_ffmpeg,
        args=(job_id, input_url, duration)
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
