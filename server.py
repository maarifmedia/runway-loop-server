from flask import Flask, request, jsonify
import threading
import subprocess
import os
import requests

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "Runway loop server running"

def process_video(input_url, duration):
    try:
        input_path = "/tmp/input.mp4"
        output_path = "/tmp/output.mp4"

        # Videoyu indir
        r = requests.get(input_url, stream=True)
        with open(input_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        # FFmpeg loop (arka planda, uzun sürebilir)
        cmd = [
            "ffmpeg",
            "-stream_loop", "-1",
            "-i", input_path,
            "-t", str(duration),
            "-c", "copy",
            output_path
        ]

        subprocess.run(cmd, check=True)
        print("Loop video hazır:", output_path)

        # ŞİMDİLİK BURADA DURUYORUZ
        # (Bir sonraki adımda Dropbox upload ekleyeceğiz)

    except Exception as e:
        print("Hata:", e)

@app.route("/start", methods=["POST"])
def start():
    data = request.json
    input_url = data.get("input_url")
    duration = data.get("duration")

    if not input_url or not duration:
        return jsonify({"error": "input_url and duration required"}), 400

    # Make'e HEMEN cevap → timeout olmaz
    thread = threading.Thread(
        target=process_video,
        args=(input_url, duration)
    )
    thread.start()

    return jsonify({"status": "started"}), 200

import os

app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 10000))
)
