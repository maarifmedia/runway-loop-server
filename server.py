import subprocess, os, datetime, requests

# -----------------------
# 1️⃣ Dosya URL'leri
# -----------------------
files = {
    "rain.jpg": "https://raw.githubusercontent.com/username/repo/branch/rain.jpg",
    "rain.mp3": "https://raw.githubusercontent.com/username/repo/branch/rain.mp3"
}

# -----------------------
# 2️⃣ Dosyaları indir
# -----------------------
for filename, url in files.items():
    if not os.path.exists(filename):
        r = requests.get(url)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"{filename} indirildi")
        else:
            raise Exception(f"{filename} indirilemedi, status: {r.status_code}")
    else:
        print(f"{filename} zaten mevcut")

# -----------------------
# 3️⃣ videos klasörü
# -----------------------
if not os.path.exists("videos"):
    os.makedirs("videos")
elif not os.path.isdir("videos"):
    os.remove("videos")
    os.makedirs("videos")

# -----------------------
# 4️⃣ ffmpeg komutu
# -----------------------
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
test_output = f"videos/test_video_{timestamp}.mp4"
full_output = f"videos/sleep_video_rain_{timestamp}.mp4"

def create_video(duration, output_file):
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", "rain.jpg",
        "-i", "rain.mp3",
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

# -----------------------
# 5️⃣ Önce test video
# -----------------------
print("▶️ 10 saniyelik test video oluşturuluyor...")
create_video("10", test_output)

# -----------------------
# 6️⃣ 1 saatlik video
# -----------------------
print("▶️ 1 saatlik video oluşturuluyor...")
create_video("3600", full_output)
