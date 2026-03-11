import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import time
import random

# --- 1. AYARLAR ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Cozy Ambience - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Peaceful vibes for sleep and focus. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "relaxing,ambient,fireplace").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. ASLA DAĞ GETİRMEYEN GÖRSEL İNDİRİCİ ---
def download_image():
    if os.path.exists(IMAGE_FILE):
        os.remove(IMAGE_FILE)

    title_lower = VIDEO_TITLE.lower()
    
    # Kategori Belirleme
    if any(x in title_lower for x in ["cabin", "house", "room", "indoor"]):
        terms = "fireplace,cozy-interior,burning-fire"
    elif any(x in title_lower for x in ["lake", "water", "lakeside"]):
        terms = "campfire-lake,bonfire-night,fire-on-beach"
    else:
        terms = "burning-logs,fireplace-close-up"

    # DAĞLARI SİLİYORUZ: Sorguya '-mountain,-peak,-hills' ekleyerek Unsplash'i zorluyoruz
    # sig=random ile her seferinde farklı resim gelmesini garanti ediyoruz
    final_url = f"https://source.unsplash.com/featured/1920x1080/?{terms},-mountain,-peak,-hills&sig={random.randint(1, 99999)}"
    
    print(f"Görsel Aranıyor: {final_url}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(final_url, headers=headers, timeout=25)
        response.raise_for_status()
        with open(IMAGE_FILE, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Hata: {e}. Garanti görsel listesinden biri seçiliyor...")
        # Unsplash saçmalarsa kullanılacak 'ateş/huzur' odaklı kesin linkler
        safe_links = [
            "https://images.unsplash.com/photo-1542332213-31f87348057f", # Şömine
            "https://images.unsplash.com/photo-1473286835901-04adb1afab03", # Kamp ateşi
            "https://images.unsplash.com/photo-1518005020251-0ea5c182dca3"  # Gece ateşi
        ]
        res = requests.get(random.choice(safe_links))
        with open(IMAGE_FILE, 'wb') as f:
            f.write(res.content)

# --- 3. 1 SAATLİK GÜVENLİ RENDER ---
def render_video():
    if not os.path.exists(IMAGE_FILE): return
    print("Render başladı (1 Saat)...")
    ses = AUDIO_FILE if os.path.exists(AUDIO_FILE) else "somine_yagmur.mp3.mp3"

    # Gelen resim ne olursa olsun 1080p'ye zorlayan filtre
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "1", "-i", IMAGE_FILE,
        "-stream_loop", "-1", "-i", ses,
        "-t", "3600",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]
    subprocess.run(command, check=True)

# --- 4. YÜKLEME ---
def upload():
    if not os.path.exists('token.pickle'): return
    with open('token.pickle', 'rb') as t:
        creds = pickle.load(t)
    y = build('youtube', 'v3', credentials=creds)
    body = {
        'snippet': {'title': VIDEO_TITLE, 'description': VIDEO_DESC, 'tags': VIDEO_TAGS, 'categoryId': '10'},
        'status': {'privacyStatus': 'public'}
    }
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    request = y.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status: print(f"Yükleme: %{int(status.progress() * 100)}")
    print(f"Başarılı! ID: {response['id']}")

if __name__ == "__main__":
    download_image()
    render_video()
    upload()
