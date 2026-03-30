import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy kütüphanesini farklı içe aktarma yollarını deneyerek yükleyen koruma yapısı
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips
    except ImportError:
        print("❌ HATA: MoviePy kütüphanesi yüklenemedi. Lütfen requirements.txt dosyasını kontrol edin.")
        sys.exit(1)

# --- KONFİGÜRASYON VE DOSYA YOLLARI ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"

# YouTube API için gerekli tam yetki kapsamı
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_VIDEO = "final_60min_video.mp4" # Geçici olarak oluşturulacak 1 saatlik video

# Assets klasöründeki kaynak dosyaların yolları
FILES = {
    "video": os.path.join(ASSETS_DIR, "current_video.mp4"),
    "title": os.path.join(ASSETS_DIR, "title.txt"),
    "desc": os.path.join(ASSETS_DIR, "description.txt"),
    "tags": os.path.join(ASSETS_DIR, "tags.txt"),
    "thumb": os.path.join(ASSETS_DIR, "s.png"),
    "playlist": os.path.join(ASSETS_DIR, "playlist_id.txt")
}

def read_asset(file_key):
    """Belirtilen anahtara göre metin dosyasını okur."""
    path = FILES[file_key]
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def create_1hour_video():
    """Kısa videoyu alır ve tam 60 dakikalık (1 saat) bir döngü oluşturur."""
    print("🎬 Video işleniyor (Hedef: 60 Dakika Döngü)...")
    if not os.path.exists(FILES["video"]):
        print(f"❌ HATA: Kaynak video bulunamadı: {FILES['video']}")
        return False
        
    try:
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        
        # 3600 saniye (1 saat) için gereken tekrar sayısı hesaplanır
        loops_needed = int(3600 / duration) + 1
        print(f"🔄 Kaynak klip {duration:.2f}s sürüyor. {loops_needed} kez uç uca eklenecek.")
        
        # Klipler birleştirilir
        final_clip = concatenate_videoclips([clip] * loops_needed)
        final_clip = final_clip.subclip(0, 3600) # Tam 1 saatte kesilir
        
        # GitHub Actions kaynaklarını optimize kullanmak için render ayarları
        print("⏳ Render işlemi başladı. Bu işlem GitHub üzerinde 15-30 dk sürebilir...")
        final_clip.write_videofile(
            TEMP_VIDEO, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            bitrate="5000k", # 1080p için kaliteli ve optimize boyut
            threads=4,
            logger=None
        )
        
        clip.close()
        final_clip.close()
        print("✅ 1 saatlik video başarıyla oluşturuldu.")
        return True
    except Exception as e:
        print(f"❌ Video işleme (MoviePy) hatası: {e}")
        return False

def get_authenticated_service():
    """YouTube API servisine kimlik doğrulaması yaparak bağlanır."""
    try:
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("Kritik: Geçersiz Token! Lütfen GitHub Secrets verilerini yenileyin.")
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"🛑 Kimlik Doğrulama Hatası: {e}")
        sys.exit(1)

def upload_video(youtube):
    """Hazırlanan 1 saatlik videoyu tüm metadata bilgileriyle YouTube'a yükler."""
    try:
        title = read_asset("title") or f"Cozy Ambience - {datetime.datetime.now().year}"
        description = read_asset("desc") or "Subscribe to @TheQuietCorner-yt for more cinematic relaxation."
        tags = read_asset("tags").split(',') if read_asset("tags") else ["ambience", "relaxing"]
        playlist_id = read_asset("playlist")

        print(f"🚀 Video Yükleniyor: {title}")

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '10' # Müzik kategorisi
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Büyük dosyalar için 'resumable' yükleme modu kullanılır
        media = MediaFileUpload(TEMP_VIDEO, chunksize=1024*1024, resumable=True)
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        print("📤 YouTube sunucularına veri aktarımı başladı...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"📊 İlerleme: %{int(status.progress() * 100)}")

        video_id = response.get('id')
        print(f"✅ Video başarıyla yüklendi! Video ID: {video_id}")

        # --- KAPAK RESMİ (THUMBNAIL) ---
        if os.path.exists(FILES["thumb"]):
            print("🖼️ Kapak resmi yükleniyor...")
            time.sleep(10) # YouTube'un videoyu tanıması için kısa bir bekleme
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(FILES["thumb"])
                ).execute()
                print("✅ Kapak resmi başarıyla ayarlandı.")
            except Exception as e:
                print(f"⚠️ Kapak resmi hatası: {e}")
        
        # --- OYNATMA LİSTESİNE EKLEME ---
        if playlist_id:
            print(f"📂 Oynatma listesine ekleniyor: {playlist_id}")
            try:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id}
                        }
                    }
                ).execute()
                print("✅ Oynatma listesine eklendi.")
            except Exception as e:
                print(f"⚠️ Oynatma listesi hatası: {e}")

    except Exception as e:
        print(f"💥 Kritik Yükleme Hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 1. Döngü videosunu oluştur
    if create_1hour_video():
        # 2. Servise bağlan
        service = get_authenticated_service()
        # 3. Yüklemeyi gerçekleştir
        upload_video(service)
        
        # 4. Temizlik: Devasa geçici dosyayı silerek GitHub disk alanını boşalt
        if os.path.exists(TEMP_VIDEO):
            os.remove(TEMP_VIDEO)
            print(f"🗑️ Geçici dosya ({TEMP_VIDEO}) silindi.")
    else:
        print("❌ Video döngüsü oluşturulamadığı için işlem durduruldu.")
        sys.exit(1)
