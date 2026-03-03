import os
import uuid
import threading
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

JOBS = {}
BASE_DIR = "/tmp/videos"
os.makedirs(BASE_DIR, exist_ok=True)


def run_ffmpeg(job_id, input_url, duration):
    try:
        input_path = os.path.join(BASE_DIR, f"{job_id}_input.mp4")
        output_path = os.path.join(BASE_DIR, f"{job_id}_loop.mp4")

        # Download video
        subprocess.run(
            ["wget", "-O", input_path, input_url],
            check=True
        )

        # Create looped video (re-encode for compatibility)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop", "-1",
                "-i", input_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-movflags", "+faststart",
                output_path
            ],
            check=True
        )

        JOBS[job_id]["status"] = "finished"
        JOBS[job_id]["output_path"] = output_path

    except subprocess.CalledProcessError as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = f"FFmpeg/Wget error: {e}"

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
