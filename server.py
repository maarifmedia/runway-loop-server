import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER (Make.com'dan Gelen Veriler) ---
# Varsayılan linkleri temizledik, doğrudan çevresel değişkenleri alıyoruz.
IMAGE_URL = os.environ.get("IMAGE_URL")
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds for sleep and focus. @TheQuietCorner-yt")
VIDEO_TAGS = os.environ.get("VIDEO_TAGS", "sleep,relaxing,asmr,ambient").split(",")

# Make.com'dan gelen ses ve shorts verileri
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "No shorts plan provided.")

# Sabit dosyalar
IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. GÖRSELİ İNDİRME ---
def download_image(url, filename):
    if not url or "varsayilan-link" in url:
        # Eğer link boş gelirse sistem çökmesin diye yedek bir manzara linki
        url = "https://images.unsplash.com/photo-1542332213-31f87348057f?q=80&w=1920"
        print("UYARI: Geçersiz URL geldi, yedek görsel kullanılıyor.")
        
    print(f"Görsel indiriliyor: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        raise Exception(f"Görsel indirme hatası: {e}")

# --- 3. 1 SAATLİK RENDER İŞLEMİ (FFmpeg) ---
def render_video():
    print(f"Video render işlemi {AUDIO_FILE} sesi ile başlıyor...")
    
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        print(f"UYARI: {aktif_ses} bulunamadı! Varsayılan sese geçiliyor.")
        aktif_ses = "somine_yagmur.mp3.mp3" 
    
    # 1 saatlik (3600 sn) yüksek kaliteli ama hızlı render komutu
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
    print("Video başarıyla oluşturuldu.")

# --- 4. YOUTUBE'A YÜKLEME ---
def upload_to_youtube():
    print("YouTube'a yükleme başlıyor...")
    credentials = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    else:
        # GitHub Secrets üzerinden token kurtarma mantığı (Eğer token.pickle yoksa)
        print("HATA: token.pickle dosyası repoda bulunamadı!")
        return

    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': f"{VIDEO_DESC}\n\n--- Content Plan ---\n{SHORTS_DATA}",
            'tags': VIDEO_TAGS,
            'categoryId': '10' # 10 = Music (Uyku kanalları için daha iyidir)
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
            
    print(f"Video başarıyla yüklendi! Video ID: {response['id']}")

# --- 5. ANA ÇALIŞTIRMA ---
if __name__ == "__main__":
    try:
        download_image(IMAGE_URL, IMAGE_FILE)
        render_video()
        upload_to_youtube()
        print("TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI!")
    except Exception as e:
        print(f"KRİTİK HATA: {e}")
