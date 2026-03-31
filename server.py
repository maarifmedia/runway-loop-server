import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy pürüzsüz geçiş ve ölçeklendirme için gerekli
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx
except ImportError:
    print("❌ MoviePy yüklenemedi.")
    sys.exit(1)

# --- AYARLAR ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/youtube']

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
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def create_videos():
    """Hem 1 saatlik ana videoyu hem de 59 saniyelik dikey Shorts'u üretir."""
    print("🎬 Video işleme süreçleri başlatıldı...")
    if not os.path.exists(FILES["video"]): return False
        
    try:
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        crossfade_time = 0.5 if duration > 2 else 0.1
        
        # 1. ANA VİDEO (1 SAAT)
        print("🕒 1 Saatlik ana video oluşturuluyor...")
        loops_needed = int(3600 / (duration - crossfade_time)) + 1
        clips = [clip] * loops_needed
        final_long = concatenate_videoclips(clips, method="compose", padding=-crossfade_time)
        final_long = final_long.subclip(0, 3600)
        final_long.write_videofile(TEMP_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k", threads=4, logger=None)
        
        # 2. SHORTS VİDEO (59 SN - DİKEY)
        print("📱 Dikey Shorts videosu oluşturuluyor...")
        shorts_loops = int(59 / (duration - crossfade_time)) + 1
        shorts_clips = [clip] * shorts_loops
        final_shorts = concatenate_videoclips(shorts_clips, method="compose", padding=-crossfade_time)
        final_shorts = final_shorts.subclip(0, 59)
        
        # 16:9'dan 9:16'ya dikey crop (merkezden kesme)
        w, h = final_shorts.size
        target_ratio = 9/16
        target_w = h * target_ratio
        final_shorts = final_shorts.crop(x_center=w/2, y_center=h/2, width=target_w, height=h)
        final_shorts = final_shorts.resize(height=1920) # Standart dikey HD
        
        final_shorts.write_videofile(SHORTS_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="3000k", threads=4, logger=None)
        
        clip.close()
        final_long.close()
        final_shorts.close()
        return True
    except Exception as e:
        print(f"❌ Video işleme hatası: {e}"); return False

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_and_pin_comment(youtube):
    try:
        title = read_asset("title") or "Relaxing Ambience"
        description = read_asset("desc") or "Subscribe for more."
        tags = read_asset("tags").split(',') if read_asset("tags") else ["ambience"]
        playlist_id = read_asset("playlist")

        # --- 1. ANA VİDEOYU YÜKLE ---
        print(f"🚀 Ana Video Yükleniyor: {title}")
        body = {'snippet': {'title': f"{title} (1 HOUR)", 'description': description, 'tags': tags, 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        media = MediaFileUpload(TEMP_VIDEO, chunksize=1024*1024, resumable=True)
        res_long = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
        long_id = res_long.get('id')
        print(f"✅ Ana Video Hazır: https://youtu.be/{long_id}")

        # --- 2. SHORTS YÜKLE ---
        print(f"🚀 Shorts Yükleniyor...")
        shorts_body = {'snippet': {'title': f"{title} #shorts", 'description': f"Full version: https://youtu.be/{long_id}", 'tags': tags + ["shorts"], 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        shorts_media = MediaFileUpload(SHORTS_VIDEO, chunksize=1024*1024, resumable=True)
        res_shorts = youtube.videos().insert(part=','.join(shorts_body.keys()), body=shorts_body, media_body=shorts_media).execute()
        shorts_id = res_shorts.get('id')
        print(f"✅ Shorts Hazır: https://youtu.be/{shorts_id}")

        # --- 3. SHORTS'A SABİT YORUM EKLE ---
        print("📌 Shorts'a yorum ekleniyor ve sabitleniyor...")
        comment_body = {
            'snippet': {
                'videoId': shorts_id,
                'topLevelComment': {'snippet': {'textOriginal': f"🎬 Watch the 1-hour full version here: https://youtu.be/{long_id}"}}
            }
        }
        comment_res = youtube.commentThreads().insert(part="snippet", body=comment_body).execute()
        comment_id = comment_res['snippet']['topLevelComment']['id']
        
        # Yorumu sabitle (pin)
        # Not: Bazı API yetkilerinde yorum sabitleme için ek onay gerekebilir.
        try:
            youtube.comments().setModerationStatus(id=comment_id, moderationStatus='published', banAuthor=False).execute()
            # Pinned özelliği v3 API'de bazen doğrudan desteklenmeyebilir, bu yüzden manuel kontrol gerekebilir.
        except: pass

        # Kapak Resmi (Sadece Ana Video İçin)
        if os.path.exists(FILES["thumb"]):
            time.sleep(10)
            youtube.thumbnails().set(videoId=long_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
        
        if playlist_id:
            youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": long_id}}}).execute()

    except Exception as e:
        print(f"💥 Hata: {e}"); sys.exit(1)

if __name__ == "__main__":
    if create_videos():
        service = get_authenticated_service()
        upload_and_pin_comment(service)
        if os.path.exists(TEMP_VIDEO): os.remove(TEMP_VIDEO)
        if os.path.exists(SHORTS_VIDEO): os.remove(SHORTS_VIDEO)
