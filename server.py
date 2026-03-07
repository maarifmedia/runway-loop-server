import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER (Make.com'dan Gelen Veriler) ---
IMAGE_URL = os.environ.get("IMAGE_URL", "https://varsayilan-link.com/resim.jpg")
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Otomatik Uyku Videosu")
# Açıklamaya varsayılan olarak kanalının etiketini de ekledik
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Rahatlatıcı uyku sesleri. Abone olmayı unutmayın: @TheQuietCorner-yt")
VIDEO_TAGS = os.environ.get("VIDEO_TAGS", "uyku,rahatlama,asmr").split(",")

# İŞTE SEÇENEK B'NİN FARKI: Make.com'dan gelen ses dosyasının adı
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "yagmur.mp3") 

# Sabit dosyalarımız
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
        raise Exception("Görsel indirilemedi! Lütfen URL'yi kontrol edin.")

# --- 3. SIFIR YÜK FFMPEG RENDER İŞLEMİ (DİNAMİK SES İLE) ---
def render_video():
    print(f"Video render işlemi {AUDIO_FILE} sesi ile başlıyor...")
    
    # Repoda o isimde bir ses dosyası var mı diye kontrol edelim, yoksa hata vermesin diye varsayılan bir ses kullansın
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        print(f"UYARI: {aktif_ses} bulunamadı! Lütfen GitHub reponuza bu dosyayı yüklediğinizden emin olun.")
        # İstersen buraya bir varsayılan ses (fallback) atayabilirsin
    
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "0.1", 
        "-i", IMAGE_FILE,
        "-i", aktif_ses,
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
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    else:
        raise Exception("Yetkilendirme dosyası (token.pickle) bulunamadı!")
            
    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': VIDEO_DESC,
            'tags': VIDEO_TAGS,
            'categoryId': '22' # 22 = People & Blogs
        },
        'status': {
            'privacyStatus': 'public' # Yüklendiği an herkese açık olur
        }
    }
    
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
