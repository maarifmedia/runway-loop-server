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
import express from "express";
import fetch from "node-fetch";
import { exec } from "child_process";
import fs from "fs";
import path from "path";

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;

// Basit health check
app.get("/", (req, res) => {
  res.send("Runway loop server is running");
});

// ASENKRON LOOP ENDPOINT
app.post("/start", async (req, res) => {
  const { input_url, duration } = req.body;

  if (!input_url || !duration) {
    return res.status(400).json({ error: "input_url and duration required" });
  }

  // Make'e HEMEN cevap veriyoruz (timeout olmaz)
  res.json({ status: "started" });

  const workdir = "/tmp";
  const inputPath = path.join(workdir, "input.mp4");
  const outputPath = path.join(workdir, "output.mp4");

  try {
    // Videoyu indir
    const response = await fetch(input_url);
    const buffer = await response.arrayBuffer();
    fs.writeFileSync(inputPath, Buffer.from(buffer));

    // FFmpeg loop
    const cmd = `ffmpeg -stream_loop -1 -i ${inputPath} -t ${duration} -c copy ${outputPath}`;

    exec(cmd, async (error) => {
      if (error) {
        console.error("FFmpeg error:", error);
        return;
      }

      console.log("Loop video ready:", outputPath);
      // BURADA ileride Dropbox upload ekleyebiliriz
    });
  } catch (err) {
    console.error("Processing error:", err);
  }
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
{
  "type": "module",
  "dependencies": {
    "express": "^4.19.2",
    "node-fetch": "^3.3.2"
  }
}
