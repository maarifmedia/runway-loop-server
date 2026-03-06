import subprocess
import os
import datetime

# 1️⃣ Klasörleri ve dosyaları kontrol et
os.makedirs("videos", exist_ok=True)

image_file = "rain.jpg"   # Video için görsel
audio_file = "rain.mp3"   # Ses dosyası
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"videos/sleep_video_rain_{timestamp}.mp4"

# 2️⃣ Dosya var mı kontrol
if not os.path.exists(image_file):
    raise FileNotFoundError(f"{image_file} bulunamadı!")
if not os.path.exists(audio_file):
    raise FileNotFoundError(f"{audio_file} bulunamadı!")

# 3️⃣ ffmpeg komutu
ffmpeg_cmd = [
    "ffmpeg",
    "-loop", "1",
    "-i", image_file,
    "-i", audio_file,
    "-c:v", "libx264",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    "-t", "3600",  # 1 saatlik video
    "-pix_fmt", "yuv420p",
    output_file
]

# 4️⃣ Komutu çalıştır
try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Video oluşturuldu: {output_file}")
except subprocess.CalledProcessError as e:
    print("❌ ffmpeg çalıştırılamadı!")
    print(e)
