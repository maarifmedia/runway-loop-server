import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER ---
IMAGE_URL = os.environ.get("IMAGE_URL")
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "sleep,relaxing,asmr").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. AKILLI GÖRSEL SEÇİCİ VE İNDİRME ---
def download_image(url, filename):
    # Eski dosyayı temizle (Cache engelleme)
    if os.path.exists(filename):
        os.remove(filename)

    # Görsel çeşitliliği için başlığa göre anahtar kelime analizi
    title_lower = VIDEO_TITLE.lower()
    search_terms = "nature,calm,peaceful" # Varsayılan
    
    if "cabin" in title_lower or "house" in title_lower:
        search_terms = "cozy,cabin,fireplace,interior"
    elif "lake" in title_lower or "water" in title_lower:
        search_terms = "lakeside,reflections,calm,water"
    elif "rain" in title_lower or "storm" in title_lower:
        search_terms = "rainy,window,dark,ambient"
    elif "forest" in title_lower or "woods" in title_lower:
        search_terms = "forest,trees,misty,ethereal"
    elif "music" in title_lower:
        search_terms = "aesthetic,minimalist,calm"

    # Eğer Make'den gelen URL hatalıysa veya 'varsayilan' ise Unsplash'e akıllı arama gönder
    if not url or "varsayilan" in url or "link.com" in url:
        url = f"https://source.unsplash.com/featured/1920x1080/?{search_terms}"
    
    print(f"Görsel indiriliyor (Tema: {search_terms}): {url}")
    try:
        # Unsplash bazen doğrudan linke yönlendirir, o yüzden allow_redirects açık
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Hata: {e}. Yedek görsel kullanılıyor.")
        backup = "https://images.unsplash.com/photo-1542332213-31f87348057f"
        f_res = requests.get(backup)
        with open(filename, 'wb') as f:
            f.write(f_res.content)

# --- 3. 1 SAATLİK RENDER İŞLEMİ (3600 SANİYE) ---
def render_video():
    print(f"1 Saatlik video render işlemi {AUDIO_FILE} ile başlıyor...")
    
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        aktif_ses = "somine_yagmur.mp3.mp3" 
    
    # Süreyi 3600 (1 saat) olarak sabitledik
    render_suresi = "3600" 

    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "1", "-i", IMAGE_FILE,
        "-stream_loop", "-1", "-i", aktif_ses,
        "-t", render_suresi,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]
    
    subprocess.run(command, check=True)
    print("Video başarıyla oluşturuldu.")

# --- 4. YOUTUBE'A YÜKLEME ---
def upload_to_youtube():
    if not os.path.exists('token.pickle'):
        print("HATA: token.pickle yok!")
        return

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
        'status': {
            'privacyStatus': 'public'
        }
    }
    
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yükleniyor... %{int(status.progress() * 100)}")
            
    print(f"BAŞARILI! Video ID: {response['id']}")

if __name__ == "__main__":
    try:
        download_image(IMAGE_URL, IMAGE_FILE)
        render_video()
        upload_to_youtube()
    except Exception as e:
        print(f"KRİTİK HATA: {e}")
