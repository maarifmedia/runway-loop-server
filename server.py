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

# --- 2. NOKTA ATIŞI GÖRSEL SEÇİCİ ---
def download_image():
    if os.path.exists(IMAGE_FILE):
        os.remove(IMAGE_FILE)

    title_lower = VIDEO_TITLE.lower()
    
    # SENİN İSTEDİĞİN TEMALARA GÖRE SERT FİLTRELEME
    if any(x in title_lower for x in ["cabin", "house", "indoor", "salon"]):
        # Salon ve Şömine Manzarası
        terms = "fireplace-living-room,cozy-home-interior,burning-fireplace"
    elif any(x in title_lower for x in ["lake", "water", "göl"]):
        # Göl ve Ateş Manzarası
        terms = "campfire-lake-night,bonfire-shore,night-lake-ambient"
    else:
        # Genel Ateş/Huzur (Varsayılan)
        terms = "burning-fire-logs,cozy-fireplace-close-up"

    # ÖNEMLİ: 'woman', 'person', 'fashion' gibi moda görsellerini YASAKLADIK (-person, -woman)
    # Sadece manzara gelmesi için 'orientation=landscape' ekledik
    url = f"https://source.unsplash.com/featured/1920x1080/?{terms},-person,-woman,-fashion,-girl&sig={random.randint(1, 99999)}"
    
    print(f"Görsel Aranıyor (Sadece Mekan/Ateş): {url}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        with open(IMAGE_FILE, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Hata: {e}. Garanti listeye geçiliyor...")
        # Unsplash saçmalarsa kullanılacak 'The Quiet Corner' ruhuna uygun kesin linkler
        safe_links = [
            "https://images.unsplash.com/photo-1542332213-31f87348057f", # Şömine iç mekan
            "https://images.unsplash.com/photo-1473286835901-04adb1afab03", # Göl kenarı ateş
            "https://images.unsplash.com/photo-1518005020251-0ea5c182dca3"  # Loş şömine
        ]
        res = requests.get(random.choice(safe_links))
        with open(IMAGE_FILE, 'wb') as f:
            f.write(res.content)

# --- 3. GÜVENLİ RENDER (1 SAAT) ---
def render_video():
    if not os.path.exists(IMAGE_FILE): return
    print("Render başladı (1 Saat)...")
    ses = AUDIO_FILE if os.path.exists(AUDIO_FILE) else "somine_yagmur.mp3.mp3"

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
    print(f"Yüklendi! ID: {response['id']}")

if __name__ == "__main__":
    download_image()
    render_video()
    upload()
