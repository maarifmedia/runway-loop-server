from flask import Flask, request, jsonify
import subprocess
import os
import datetime

app = Flask(__name__)

# Video ve ses dosyalarının bulunduğu klasör
VIDEO_FOLDER = "videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True)

@app.route("/create-video", methods=["POST"])
def create_video():
    try:
        data = request.json

        # Scene ve duration parametresi alıyoruz
        scene = data.get("scene", "rain")  # rain / fireplace / forest
        duration = data.get("duration", "3600")  # saniye cinsinden, default 1 saat

        # Dosya isimleri
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{VIDEO_FOLDER}/sleep_video_{scene}_{timestamp}.mp4"

        # Görsel ve ses dosyaları
        image_file = f"{scene}.jpg"
        audio_file = f"{scene}.mp3"

        # FFmpeg komutu
        command = [
            "ffmpeg",
            "-loop", "1",
            "-i", image_file,
            "-i", audio_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            output_file
        ]

        subprocess.run(command, check=True)

        # Başarılı yanıt
        return jsonify({"status": "success", "video_file": output_file})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
