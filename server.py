import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER ---
# Make.com'dan gelen IMAGE_URL'yi alıyoruz. Gelmezse None olacak.
IMAGE_URL = os.environ.get("IMAGE_URL")
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds for sleep and focus. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "sleep,relaxing,asmr").split(",")

# Ses dosyası ve Shorts planı
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "No shorts plan provided.")

# Sabit dosyalar
IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. GÖRSELİ İNDİRME ---
def download_image(url, filename):
    # Eğer URL gelmediyse veya içinde hatalı 'varsayilan' ibaresi varsa yedek link kullan
    if not url or "varsayilan" in url or "link.com" in url:
        url = "https://images.unsplash.com/photo-1542332213-31f87348057f?q=80&w=1920"
        print("BİLGİ:IMAGE_URL boş veya hatalı geldi. Yedek manzara görseli indiriliyor...")
    
    print(f"Görsel indiriliyor: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi.")
    except Exception as e:
        print(f"Görsel indirme hatası: {e}. İşleme yedek görsel aranarak devam ediliyor.")
        # Burada çökmemesi için tekrar deniyoruz
        fallback_url = "https://images.unsplash.com/photo-1542332213-31f87348057f"
        f_res = requests.get(fallback_url)
        with open(filename, 'wb') as f:
            f.write(f_res.content)

# --- 3. RENDER İŞLEMİ (TEST İÇİN 60 SANİYE) ---
def render_video():
    print(f"Video render işlemi {AUDIO_FILE} sesi ile başlıyor...")
    
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        print(f"UYARI: {aktif_ses} bulunamadı! Varsayılan sese (somine_yagmur.mp3.mp3) geçiliyor.")
        aktif_ses = "somine_yagmur.mp3.mp3" 
    
    # DİKKAT: Test için süreyi 60 saniye yaptık. 
    # Sistem çalıştığında bunu tekrar 3600 yapabilirsin.
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
    print(f"Harika! {render_suresi} saniyelik video başarıyla oluşturuldu.")

# --- 4. YOUTUBE'A YÜKLEME ---
def upload_to_youtube():
    print("YouTube'a yükleme aşamasına geçildi...")
    
    if not os.path.exists('token.pickle'):
        print("KRİTİK HATA: token.pickle dosyası bulunamadı! Yükleme yapılamıyor.")
        return

    with open('token.pickle', 'rb') as token:
        credentials = pickle.load(token)
            
    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': f"{VIDEO_DESC}\n\n--- Content Plan ---\n{SHORTS_DATA}",
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
    print("Yükleme işlemi başlatılıyor...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yükleniyor... %{int(status.progress() * 100)}")
            
    print(f"TEBRİKLER! Video yüklendi. ID: {response['id']}")

# --- 5. ANA ÇALIŞTIRMA ---
if __name__ == "__main__":
    try:
        download_image(IMAGE_URL, IMAGE_FILE)
        render_video()
        upload_to_youtube()
        print("TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI!")
    except Exception as e:
        print(f"BİR HATA OLUŞTU: {e}")

