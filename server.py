import os
import subprocess
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Cozy Ambience - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Peaceful vibes for sleep and focus. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "relaxing,ambient,fireplace").split(",")

# Giriş ve Çıkış Dosyaları
INPUT_VIDEO = "assets/current_video.mp4"  # Make.com buraya yüklemeli
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. VİDEO DÖNGÜLEYİCİ (1 SAAT) ---
def render_video():
    if not os.path.exists(INPUT_VIDEO):
        print(f"Hata: {INPUT_VIDEO} bulunamadı! Make.com videoyu yüklememiş olabilir.")
        return False
    
    print("Render başladı: 10 saniyelik video 1 saate uzatılıyor...")
    
    # Videoyu ve sesini bozmadan tam 1 saat (3600 sn) boyunca döngüye sokar
    # -stream_loop -1 sonsuz döngü sağlar, -t 3600 ise tam 1 saatte keser.
    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", 
        "-i", INPUT_VIDEO,
        "-t", "3600",
        "-c", "copy", # Encode etmeden kopyalar (Saniyeler içinde biter!)
        OUTPUT_VIDEO
    ]
    
    try:
        subprocess.run(command, check=True)
        print("1 Saatlik video başarıyla hazırlandı.")
        return True
    except Exception as e:
        print(f"Render Hatası: {e}")
        return False

# --- 3. YÜKLEME ---
def upload():
    if not os.path.exists('token.pickle'):
        print("Hata: token.pickle bulunamadı!")
        return
    
    if not os.path.exists(OUTPUT_VIDEO): return

    with open('token.pickle', 'rb') as t:
        creds = pickle.load(t)
    
    y = build('youtube', 'v3', credentials=creds)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE, 
            'description': VIDEO_DESC, 
            'tags': VIDEO_TAGS, 
            'categoryId': '10' # Music/Ambient
        },
        'status': {'privacyStatus': 'public'}
    }
    
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    request = y.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status: print(f"Yükleme: %{int(status.progress() * 100)}")
    
    print(f"Yüklendi! Video ID: {response['id']}")

if __name__ == "__main__":
    if render_video():
        upload()
