import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import time

# --- 1. AYARLAR VE DEĞİŞKENLER ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds for sleep and focus. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "sleep,relaxing,asmr,ambient").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "No shorts plan provided.")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. AKILLI GÖRSEL SEÇİCİ VE İNDİRME ---
def download_image(filename):
    # Önbellek çakışmasını önlemek için eski dosyayı sil
    if os.path.exists(filename):
        os.remove(filename)

    title_lower = VIDEO_TITLE.lower()
    
    # Kategori Belirleme (Dağ resimlerinden kaçınmak için spesifik kelimeler)
    if any(x in title_lower for x in ["cabin", "house", "indoor", "room", "home"]):
        # Ev/İç mekan atmosferi
        search_terms = "cozy-interior,fireplace-room,dark-aesthetic-home,library-ambient"
    elif any(x in title_lower for x in ["lake", "water", "river", "lakeside"]):
        # Su ve göl kenarı atmosferi
        search_terms = "lakeside-night,dark-lake,calm-water-shore"
    elif "rain" in title_lower or "storm" in title_lower:
        # Yağmur atmosferi
        search_terms = "rainy-window,dark-city-rain,stormy-night-ambient"
    else:
        # Genel huzurlu gece atmosferi
        search_terms = "dark-forest-night,misty-woods,starry-night-sky"

    # Unsplash API - Dağ görsellerini engellemek için -mountain filtresi ekliyoruz
    # sig parametresi her seferinde farklı resim gelmesini sağlar
    final_url = f"https://images.unsplash.com/featured/?{search_terms},-mountain,-peak&sig={int(time.time())}"
    
    print(f"Görsel deneniyor (Tema: {search_terms}): {final_url}")
    
    try:
        # Gerçek bir kullanıcı gibi görünmek için Header ekliyoruz
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(final_url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Hata oluştu, yedek görsele geçiliyor: {e}")
        # Unsplash yanıt vermezse sistemin çökmemesi için sabit huzurlu bir göl resmi
        fallback = requests.get("https://images.unsplash.com/photo-1501785888041-af3ef285b470")
        with open(filename, 'wb') as f:
            f.write(fallback.content)

# --- 3. 1 SAATLİK RENDER İŞLEMİ (3600 SANİYE) ---
def render_video():
    print(f"Video render işlemi başlıyor (Hedef: 3600 Saniye)...")
    
    # Ses dosyası kontrolü
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        print(f"UYARI: {aktif_ses} bulunamadı! Yedek sese geçiliyor.")
        aktif_ses = "somine_yagmur.mp3.mp3" 
    
    # FFmpeg Komutu (1 Saatlik render)
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
    print("Video başarıyla oluşturuldu. Yükleme aşamasına geçiliyor.")

# --- 4. YOUTUBE'A YÜKLEME ---
def upload_to_youtube():
    print("YouTube API bağlantısı kuruluyor...")
    
    if not os.path.exists('token.pickle'):
        print("KRİTİK HATA: token.pickle bulunamadı!")
        return

    with open('token.pickle', 'rb') as token:
        credentials = pickle.load(token)
            
    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': f"{VIDEO_DESC}\n\n--- Content Details ---\n{SHORTS_DATA}",
            'tags': VIDEO_TAGS,
            'categoryId': '10' # Music/Ambient
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
            
    print(f"TEBRİKLER! Video yüklendi. ID: {response['id']}")

# --- 5. ANA ÇALIŞTIRMA ---
if __name__ == "__main__":
    try:
        download_image(IMAGE_FILE)
        render_video()
        upload_to_youtube()
        print("SÜREÇ BAŞARIYLA TAMAMLANDI.")
    except Exception as e:
        print(f"SİSTEM HATASI: {e}")
