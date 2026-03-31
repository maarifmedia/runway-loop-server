import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy pürüzsüz geçiş ve ölçeklendirme için
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
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
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def create_videos():
    """Ana videoyu ve Shorts klibini hazırlar."""
    print("🎬 Video işleme süreçleri başladı...")
    if not os.path.exists(FILES["video"]): return False
    try:
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        crossfade_time = 0.5 if duration > 2 else 0.1
        
        # 1. ANA VİDEO (1 SAAT)
        loops_needed = int(3600 / (duration - crossfade_time)) + 1
        final_long = concatenate_videoclips([clip] * loops_needed, method="compose", padding=-crossfade_time)
        final_long = final_long.subclip(0, 3600)
        final_long.write_videofile(TEMP_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k", threads=4, logger=None)
        
        # 2. SHORTS VİDEO (59 SN - DİKEY)
        shorts_loops = int(59 / (duration - crossfade_time)) + 1
        final_shorts = concatenate_videoclips([clip] * shorts_loops, method="compose", padding=-crossfade_time)
        final_shorts = final_shorts.subclip(0, 59)
        
        # Dikey Kesim (9:16)
        w, h = final_shorts.size
        target_w = h * (9/16)
        final_shorts = final_shorts.crop(x_center=w/2, y_center=h/2, width=target_w, height=h)
        final_shorts = final_shorts.resize(height=1920)
        final_shorts.write_videofile(SHORTS_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="3000k", threads=4, logger=None)
        
        clip.close()
        return True
    except Exception as e:
        print(f"❌ Video hata: {e}"); return False

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_process(youtube):
    try:
        title = read_asset("title") or "Cozy Ambience"
        description = read_asset("desc") or "Relaxing atmosphere."
        tags = (read_asset("tags") or "ambience").split(',')
        playlist_id = read_asset("playlist")

        # 1. ANA VİDEO YÜKLE
        print(f"🚀 Ana Video: {title}")
        body = {'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        media = MediaFileUpload(TEMP_VIDEO, chunksize=1024*1024, resumable=True)
        res_long = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
        long_id = res_long.get('id')
        print(f"✅ Ana Video ID: {long_id}")

        # 2. SHORTS YÜKLE
        print(f"🚀 Shorts Yükleniyor...")
        shorts_body = {'snippet': {'title': f"{title} #shorts", 'description': f"Full 1-hour version: https://youtu.be/{long_id}", 'tags': tags + ["shorts"], 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
        shorts_media = MediaFileUpload(SHORTS_VIDEO, chunksize=1024*1024, resumable=True)
        res_shorts = youtube.videos().insert(part=','.join(shorts_body.keys()), body=shorts_body, media_body=shorts_media).execute()
        shorts_id = res_shorts.get('id')
        print(f"✅ Shorts ID: {shorts_id}")

        # 3. OTOMATİK YORUM (SHORTS'A)
        print("💬 Shorts'a yönlendirme yorumu bırakılıyor...")
        try:
            youtube.commentThreads().insert(part="snippet", body={
                'snippet': {
                    'videoId': shorts_id,
                    'topLevelComment': {'snippet': {'textOriginal': f"🎬 Watch the full 1-hour cinematic version here: https://youtu.be/{long_id}"}}
                }
            }).execute()
            print("✅ Yorum başarıyla bırakıldı.")
        except Exception as e: print(f"⚠️ Yorum bırakılamadı: {e}")

        # Kapak Resmi ve Liste (Ana Video)
        if os.path.exists(FILES["thumb"]):
            time.sleep(15)
            youtube.thumbnails().set(videoId=long_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
            print("✅ Kapak resmi eklendi.")
        
        if playlist_id:
            youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": long_id}}}).execute()
            print("✅ Listeye eklendi.")

    except Exception as e:
        print(f"💥 Kritik Hata: {e}"); sys.exit(1)

if __name__ == "__main__":
    if create_videos():
        service = get_authenticated_service()
        upload_process(service)
        if os.path.exists(TEMP_VIDEO): os.remove(TEMP_VIDEO)
        if os.path.exists(SHORTS_VIDEO): os.remove(SHORTS_VIDEO)
