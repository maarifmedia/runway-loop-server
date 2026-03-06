import subprocess
import os
import datetime

# ------------------------
# 1️⃣ Ayarlar
# ------------------------
IMAGE_FILE = "rain.jpg"     # Görsel dosya
AUDIO_FILE = "rain.mp3"     # Ses dosyası
VIDEO_DIR = "videos"        # Çıktı klasörü
TEST_DURATION = "10"        # Test video süresi (saniye)
FULL_DURATION = "3600"      # Tam video süresi (1 saat)

# ------------------------
# 2️⃣ Klasör ve dosya kontrol
# ------------------------
os.makedirs(VIDEO_DIR, exist_ok=True)

if not os.path.exists(IMAGE_FILE):
    raise FileNotFoundError(f"{IMAGE_FILE} bulunamadı!")
if not os.path.exists(AUDIO_FILE):
    raise FileNotFoundError(f"{AUDIO_FILE} bulunamadı!")

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
test_output = os.path.join(VIDEO_DIR, f"test_video_{timestamp}.mp4")
full_output = os.path.join(VIDEO_DIR, f"sleep_video_rain_{timestamp}.mp4")

# ------------------------
# 3️⃣ ffmpeg komut fonksiyonu
# ------------------------
def create_video(duration, output_file):
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", IMAGE_FILE,
        "-i", AUDIO_FILE,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-t", duration,
        "-pix_fmt", "yuv420p",
        output_file
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Video oluşturuldu: {output_file}")
    except subprocess.CalledProcessError as e:
        print("❌ ffmpeg çalıştırılamadı!")
        print(e)
        exit(1)

# ------------------------
# 4️⃣ Önce test video
# ------------------------
print("▶️ 10 saniyelik test video oluşturuluyor...")
create_video(TEST_DURATION, test_output)

# ------------------------
# 5️⃣ Tam video
# ------------------------
print("▶️ 1 saatlik tam video oluşturuluyor...")
create_video(FULL_DURATION, full_output)
