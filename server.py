import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import time

# --- 1. AYARLAR ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Relaxing Atmosphere")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Peaceful vibes by @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "relax,ambient").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. HATA VERMEYEN GÖRSEL İNDİRİCİ ---
def download_image():
    if os.path.exists(IMAGE_FILE):
        os.remove(IMAGE_FILE)

    title_lower = VIDEO_TITLE.lower()
    
    # Kategori Belirleme
    if any(x in title_lower for x in ["cabin", "house", "room"]):
        # Dağdan kaçmak için 'interior' ve 'living room' vurgusu
        terms = "cozy-interior,living-room,fireplace-room"
    elif any(x in title_lower for x in ["lake", "water"]):
        terms = "lakeside,lake-shore,night-water"
    else:
        terms = "dark-forest,misty-woods"

    # Unsplash'e dağ istemediğimizi (minus mountain) ve her seferinde farklı istediğimizi söylüyoruz
    url = f"https://source.unsplash.com/featured/1920x1080/?{terms},-mountain,-peak&sig={int(time.time())}"
    
    print(f"Deneme: {url}")
    
    try:
        # User-Agent eklemek Unsplash'in bizi engellemesini önler
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        with open(IMAGE_FILE, 'wb') as f:
            f.write(response.content)
        print("Görsel indi.")
    except Exception as e:
        print(f"Hata: {e}. Çökmemek için yedek manzara yükleniyor...")
        # BURASI KRİTİK: Eğer Unsplash hata verirse, sistemin çökmemesi için 
        # doğrudan çalışan bir manzara görseli indiriyoruz.
        yedek_url = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920"
        y_res = requests.get(yedek_url)
        with open(IMAGE_FILE, 'wb') as f:
            f.write(y_res.content)

# --- 3. 1 SAATLİK GÜVENLİ RENDER ---
def render_video():
    # Görsel inmiş mi kontrol et, inmemişse (imkansız ama) boş bir görsel yarat
    if not os.path.exists(IMAGE_FILE):
        print("HATA: Görsel yok! Render yapılamaz.")
        return

    print("Render başladı (3600 sn)...")
    
    # Ses dosyasının adını kontrol et
    ses = AUDIO_FILE if os.path.exists(AUDIO_FILE) else "somine_yagmur.mp3.mp3"

    # FFmpeg komutuna görsel boyutlarını sabitleyen (1920x1080) filtre ekledik 
    # Bu, 'Invalid argument' hatalarını önler.
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
    print("Video bitti.")

# --- 4. YÜKLEME ---
def upload():
    if not os.path.exists('token.pickle'):
        print("Hata: token.pickle yok!")
        return

    with open('token.pickle', 'rb') as t:
        creds = pickle.load(t)
            
    y = build('youtube', 'v3', credentials=creds)
    body = {
        'snippet': {'title': VIDEO_TITLE, 'description': VIDEO_DESC, 'tags': VIDEO_TAGS, 'categoryId': '10'},
        'status': {'privacyStatus': 'public'}
    }
    m = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    req = y.videos().insert(part="snippet,status", body=body, media_body=m)
    
    res = None
    while res is None:
        status, res = req.next_chunk()
        if status: print(f"Yükleme: %{int(status.progress() * 100)}")
    print(f"Yüklendi: {res['id']}")

if __name__ == "__main__":
    download_image()
    render_video()
    upload()
