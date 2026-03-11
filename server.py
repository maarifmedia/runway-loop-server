import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import time

# --- 1. AYARLAR VE DEĞİŞKENLER ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "sleep,relaxing,asmr").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. GELİŞMİŞ GÖRSEL SEÇİCİ VE İNDİRME ---
def download_image(filename):
    if os.path.exists(filename):
        os.remove(filename)

    title_lower = VIDEO_TITLE.lower()
    
    # Dağ (Mountain) kelimesini yasaklıyoruz ve iç mekan/göl odaklı kelimeleri güçlendiriyoruz
    if any(x in title_lower for x in ["cabin", "house", "indoor", "room"]):
        # İç mekan garantisi için 'room' ve 'interior' anahtar kelimelerini zorunlu kılıyoruz
        search_terms = "cozy-room-interior,fireplace-living-room,dark-aesthetic-room"
    elif any(x in title_lower for x in ["lake", "water", "river"]):
        search_terms = "lakeside-night,dark-lake-water,campfire-by-lake"
    elif "rain" in title_lower:
        search_terms = "rainy-window-view,street-rain-night,dark-rainy-ambient"
    else:
        search_terms = "dark-forest-night,misty-night-ambient"

    # Unsplash'e 'mountain' kelimesini eksi (-) operatörüyle göndererek dağ resimlerini filtrelemeye çalışıyoruz
    # Ayrıca sig parametresine zaman damgası ekleyerek her saniye farklı resim gelmesini sağlıyoruz
    final_url = f"https://source.unsplash.com/featured/1920x1080/?{search_terms},-mountain,-peak&sig={int(time.time())}"
    
    print(f"Görsel indiriliyor (Filtreli Tema: {search_terms}): {final_url}")
    
    try:
        # User-Agent ekleyerek gerçek bir tarayıcı gibi davranıyoruz (Unsplash bot koruması için)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(final_url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Yeni görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Hata: {e}. Yedek göl görseli indiriliyor...")
        fallback = requests.get("https://images.unsplash.com/photo-1501785888041-af3ef285b470")
        with open(filename, 'wb') as f:
            f.write(fallback.content)

# --- 3. 1 SAATLİK RENDER ---
def render_video():
    print(f"1 Saatlik render başlıyor: {AUDIO_FILE}")
    aktif_ses = AUDIO_FILE if os.path.exists(AUDIO_FILE) else "somine_yagmur.mp3.mp3" 
    
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "1", "-i", IMAGE_FILE,
        "-stream_loop", "-1", "-i", aktif_ses,
        "-t", "3600",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]
    subprocess.run(command, check=True)

# --- 4. YOUTUBE YÜKLEME ---
def upload_to_youtube():
    if not os.path.exists('token.pickle'): return
    with open('token.pickle', 'rb') as token:
        credentials = pickle.load(token)
    youtube = build('youtube', 'v3', credentials=credentials)
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': f"{VIDEO_DESC}\n\n{SHORTS_DATA}",
            'tags': VIDEO_TAGS,
            'categoryId': '10'
        },
        'status': {'privacyStatus': 'public'}
    }
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status: print(f"Yükleniyor: %{int(status.progress() * 100)}")
    print(f"Bitti! ID: {response['id']}")

if __name__ == "__main__":
    try:
        download_image(IMAGE_FILE)
        render_video()
        upload_to_youtube()
    except Exception as e:
        print(f"HATA: {e}")
