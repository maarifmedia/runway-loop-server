import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- KRİTİK PILLOW YAMASI (Hata Engelleyici) ---
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        # Yeni Pillow sürümlerinde (10+) ANTIALIAS kaldırıldı, LANCZOS'a yönlendiriyoruz
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    
    from moviepy.editor import VideoFileClip, concatenate_videoclips
except ImportError:
    print("❌ MoviePy veya Pillow bulunamadı.")
    sys.exit(1)

# --- AYARLAR ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['[https://www.googleapis.com/auth/youtube.upload](https://www.googleapis.com/auth/youtube.upload)', '[https://www.googleapis.com/auth/youtube.force-ssl](https://www.googleapis.com/auth/youtube.force-ssl)', '[https://www.googleapis.com/auth/youtube](https://www.googleapis.com/auth/youtube)']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_VIDEO = "final_60min_video.mp4"
SHORTS_VIDEO = "shorts_video.mp4"

FILES = {
    "video": os.path.join(ASSETS_DIR, "current_video.mp4"),
    "title": os.path.join(ASSETS_DIR, "title.txt"),
    "desc": os.path.join(ASSETS_DIR, "description.txt"),
    "tags": os.path.join(ASSETS_DIR, "tags.txt"),
    "thumb": os.path.join(ASSETS_DIR, "s.png"),
    "playlist": os.path.join(ASSETS_DIR, "playlist_id.txt")
}

def read_asset(file_key):
    path = FILES[file_key]
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def create_videos():
    """Ana videoyu ve Shorts klibini hazırlar."""
    print("🎬 Video motoru başlatılıyor...")
    if not os.path.exists(FILES["video"]): return False
    
    try:
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        crossfade_p = 0.5 if duration > 2 else 0.1

        # 1. ANA VİDEO (1 SAAT)
        print("🕒 1 Saatlik ana video render ediliyor...")
        loops = int(3600 / (duration - crossfade_p)) + 1
        final_long = concatenate_videoclips([clip] * loops, method="compose", padding=-crossfade_p)
        final_long = final_long.subclip(0, 3600)
        final_long.write_videofile(TEMP_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k", threads=4, logger=None)
        
        # 2. SHORTS (59 SN - DİKEY)
        print("📱 Shorts videosu dikey olarak kesiliyor...")
        s_loops = int(59 / (duration - crossfade_p)) + 1
        final_s = concatenate_videoclips([clip] * s_loops, method="compose", padding=-crossfade_p)
        final_s = final_s.subclip(0, 59)
        
        # Dikey Kesim (9:16)
        w, h = final_s.size
        target_w = h * (9/16)
        final_s = final_s.crop(x_center=w/2, y_center=h/2, width=target_w, height=h)
        final_s = final_s.resize(height=1280) # 720x1280 HD
        
        final_s.write_videofile(SHORTS_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="2500k", threads=4, logger=None)
        
        clip.close()
        print("✅ Videolar başarıyla oluşturuldu.")
        return True
    except Exception as e:
        print(f"❌ MoviePy İşlem Hatası: {e}")
        return False

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_process(youtube):
    long_id = None
    try:
        title = read_asset("title") or "Cozy Ambience"
        description = read_asset("desc") or "Relaxing atmosphere."
        tags = (read_asset("tags") or "relax").split(',')
        playlist_id = read_asset("playlist")

        # 1. Ana Video Yükle
        print(f"🚀 Yükleniyor: {title}")
        body = {'snippet': {'title': f"{title} (1 HOUR)", 'description': description, 'tags': tags, 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        res_l = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=MediaFileUpload(TEMP_VIDEO, resumable=True)).execute()
        long_id = res_l.get('id')
        print(f"✅ Ana Video Hazır: {long_id}")
        
        # 2. Shorts Yükle
        print(f"🚀 Shorts Yükleniyor...")
        s_body = {'snippet': {'title': f"{title} #shorts", 'description': f"Watch full version: [https://youtu.be/](https://youtu.be/){long_id}", 'tags': tags + ["shorts"], 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        res_s = youtube.videos().insert(part=','.join(s_body.keys()), body=s_body, media_body=MediaFileUpload(SHORTS_VIDEO, resumable=True)).execute()
        shorts_id = res_s.get('id')
        print(f"✅ Shorts Hazır: {shorts_id}")

        # 3. Yorum
        if long_id:
            try:
                youtube.commentThreads().insert(part="snippet", body={'snippet': {'videoId': shorts_id, 'topLevelComment': {'snippet': {'textOriginal': f"🎬 Watch the full 1-hour version here: [https://youtu.be/](https://youtu.be/){long_id}"}}}}).execute()
            except: pass

        # Kapak & Playlist (Sadece Ana Video)
        if os.path.exists(FILES["thumb"]):
            time.sleep(10)
            youtube.thumbnails().set(videoId=long_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
        if playlist_id:
            youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": long_id}}}).execute()

    except Exception as e: print(f"💥 Yükleme Hatası: {e}")

if __name__ == "__main__":
    if create_videos():
        service = get_authenticated_service()
        upload_process(service)
        for f in [TEMP_VIDEO, SHORTS_VIDEO]:
            if os.path.exists(f): os.remove(f)
