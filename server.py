import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER ---
# Make.com'dan GitHub Actions'a environment variable (ortam değişkeni) olarak gelecek veriler
IMAGE_URL = os.environ.get("IMAGE_URL", "https://varsayilan-gorsel-linki.com/resim.jpg")
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Otomatik Uyku Videosu")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Rahatlatıcı uyku sesleri.")
VIDEO_TAGS = os.environ.get("VIDEO_TAGS", "uyku,rahatlama,asmr").split(",")

# Sabit dosyalarımız
AUDIO_FILE = "uyku_sesi.mp3" # GitHub reponda duracak 1 saatlik standart ses dosyan
IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. GÖRSELİ İNDİRME ---
def download_image(url, filename):
    print("Görsel indiriliyor...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    else:
        raise Exception("Görsel indirilemedi!")

# --- 3. SIFIR YÜK FFMPEG RENDER İŞLEMİ ---
def render_video():
    print("Video render işlemi başlıyor (Sıfır Yük Optimizasyonu ile)...")
    # İşin sırrı bu komutta: framerate 0.1 (saniyede 0.1 kare) ve -c:a copy (sesi kopyala, işleme)
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "0.1", 
        "-i", IMAGE_FILE,
        "-i", AUDIO_FILE,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        OUTPUT_VIDEO
    ]
    
    subprocess.run(command, check=True)
    print("Harika! 1 saatlik video saniyeler içinde oluşturuldu.")

# --- 4. YOUTUBE'A YÜKLEME (CHUNKED UPLOAD) ---
def upload_to_youtube():
    print("YouTube'a yükleme başlıyor...")
    credentials = None
    
    # Önceden alınmış bir token varsa onu kullanırız (GitHub Secrets içine koyacağız bunu)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
            
    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': VIDEO_DESC,
            'tags': VIDEO_TAGS,
            'categoryId': '22' # 22 = People & Blogs, 10 = Music gibi değiştirebilirsin
        },
        'status': {
            'privacyStatus': 'public' # Yüklenir yüklenmez herkese açık olur (veya 'private' yapabilirsin)
        }
    }
    
    # Videoyu 5MB'lık parçalar halinde yükleyerek belleği şişirmesini engelliyoruz
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yükleniyor... %{int(status.progress() * 100)}")
            
    print(f"Video başarıyla yüklendi! Video ID: {response['id']}")

# --- 5. ANA ÇALIŞTIRMA BLOKU ---
if __name__ == "__main__":
    try:
        download_image(IMAGE_URL, IMAGE_FILE)
        render_video()
        upload_to_youtube()
        print("TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI!")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")
