from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/loop", methods=["POST"])
def loop_video():
    data = request.json
    input_url = data["input_url"]
    output_name = "output.mp4"

    subprocess.run(["wget", input_url, "-O", "input.mp4"])

    subprocess.run([
        "ffmpeg",
        "-stream_loop", "449",
        "-i", "input.mp4",
        "-c", "copy",
        output_name
    ])

    return jsonify({"status": "done", "file": output_name})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
