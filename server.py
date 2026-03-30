import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy kütüphanesini içe aktarırken hata kontrolü yapıyoruz
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips
    except ImportError:
        print("❌ HATA: MoviePy kütüphanesi yüklenemedi. Lütfen requirements.txt dosyasını kontrol edin.")
        sys.exit(1)

# --- KONFİGÜRASYON ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_VIDEO = "final_60min_video.mp4"

FILES = {
    "video": os.path.join(ASSETS_DIR, "current_video.mp4"),
    "title": os.path.join(ASSETS_DIR, "title.txt"),
    "desc": os.path.join(ASSETS_DIR, "description.txt"),
    "tags": os.path.join(ASSETS_DIR, "tags.txt"),
    "thumb": os.path.join(ASSETS_DIR, "s.png"),
    "playlist": os.path.join(ASSETS_DIR, "playlist_id.txt")
}

def read_asset(file_key):
    """Assets klasöründeki dosyaları okur."""
    path = FILES[file_key]
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def create_1hour_video():
    """Videoyu pürüzsüz bir döngüyle 1 saate tamamlar."""
    print("🎬 Video döngüye sokuluyor (Pürüzsüz Geçiş Modu)...")
    if not os.path.exists(FILES["video"]):
        print(f"❌ HATA: Kaynak video bulunamadı: {FILES['video']}")
        return False
        
    try:
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        
        # Döngü geçişi için 0.5 saniyelik bir yumuşatma (crossfade) süresi
        crossfade_time = 0.5 if duration > 2 else 0.1
        
        # 3600 saniye (1 saat) için gereken döngü sayısını hesapla
        loops_needed = int(3600 / (duration - crossfade_time)) + 1
        print(f"🔄 Klip {duration:.2f}s sürüyor. {loops_needed} tekrar ve {crossfade_time}s geçişle birleştiriliyor.")
        
        # Klipleri birbirinin üzerine bindirerek (padding) pürüzsüzce birleştir
        clips = [clip] * loops_needed
        final_clip = concatenate_videoclips(clips, method="compose", padding=-crossfade_time)
        
        # Tam 1 saatte kes
        final_clip = final_clip.subclip(0, 3600)
        
        print("⏳ Render işlemi başladı (Bu işlem GitHub üzerinde 20-30 dk sürebilir)...")
        final_clip.write_videofile(
            TEMP_VIDEO, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            bitrate="5000k",
            threads=4,
            logger=None
        )
        
        clip.close()
        final_clip.close()
        print("✅ 1 saatlik pürüzsüz video hazır.")
        return True
    except Exception as e:
        print(f"❌ Video işleme hatası: {e}")
        return False

def get_authenticated_service():
    """YouTube API bağlantısını kurar."""
    try:
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("Kritik: Token geçersiz! Lütfen yeni token üretin.")
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"🛑 Kimlik Doğrulama Hatası: {e}")
        sys.exit(1)

def upload_video(youtube):
    """Metadata ve Kapak Resmi ile birlikte yükleme yapar."""
    try:
        title = read_asset("title") or "Cinematic Ambience (1 HOUR)"
        description = read_asset("desc") or "Subscribe to @TheQuietCorner-yt."
        tags = read_asset("tags").split(',') if read_asset("tags") else ["ambience"]
        playlist_id = read_asset("playlist")

        print(f"🚀 Yükleniyor: {title}")

        body = {
            'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '10'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }

        media = MediaFileUpload(TEMP_VIDEO, chunksize=1024*1024, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        print("📤 YouTube sunucusuna gönderiliyor...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"📊 İlerleme: %{int(status.progress() * 100)}")

        video_id = response.get('id')
        print(f"✅ Başarıyla yüklendi! Video ID: {video_id}")

        # Kapak Resmi (Thumbnail)
        if os.path.exists(FILES["thumb"]):
            print("🖼️ Kapak resmi ayarlanıyor...")
            time.sleep(10)
            try:
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
                print("✅ Kapak resmi eklendi.")
            except Exception as e: print(f"⚠️ Kapak hatası: {e}")
        
        # Oynatma Listesi
        if playlist_id:
            try:
                youtube.playlistItems().insert(part="snippet", body={
                    "snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}
                }).execute()
                print("✅ Oynatma listesine eklendi.")
            except Exception as e: print(f"⚠️ Liste hatası: {e}")

    except Exception as e:
        print(f"💥 Kritik Yükleme Hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if create_1hour_video():
        service = get_authenticated_service()
        upload_video(service)
        if os.path.exists(TEMP_VIDEO):
            os.remove(TEMP_VIDEO)
            print("🗑️ Geçici dosya silindi.")
