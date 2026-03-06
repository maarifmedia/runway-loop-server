from flask import Flask, send_file
import subprocess
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Server is running"

@app.route("/generate")
def generate():

    image_url = "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
    audio_url = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3"

    os.system(f"wget -O image.jpg {image_url}")
    os.system(f"wget -O audio.mp3 {audio_url}")

    ffmpeg_command = [
        "ffmpeg",
        "-y",
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

    return send_file("output.mp4", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
