import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy hata kontrolleri
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    import moviepy.video.fx.all as vfx
except ImportError:
    print("❌ MoviePy veya bağımlılıkları bulunamadı.")
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
    """Ana videoyu ve Shorts klibini daha güvenli bir yöntemle hazırlar."""
    print("🎬 Video işleme motoru başlatılıyor...")
    if not os.path.exists(FILES["video"]):
        print("❌ Kaynak video (current_video.mp4) bulunamadı!")
        return False
        
    try:
        # Ana klibi yükle
        clip = VideoFileClip(FILES["video"])
        duration = clip.duration
        crossfade_time = 0.5 if duration > 2 else 0.1
        
        # 1. ANA VİDEO OLUŞTURMA (1 SAAT)
        print("🕒 1 Saatlik ana video render ediliyor (Sabırlı olun)...")
        loops_needed = int(3600 / (duration - crossfade_time)) + 1
        final_long = concatenate_videoclips([clip] * loops_needed, method="compose", padding=-crossfade_time)
        final_long = final_long.subclip(0, 3600)
        final_long.write_videofile(TEMP_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="5000k", threads=4, logger=None)
        final_long.close()
        print("✅ Ana video dosyası oluşturuldu.")

        # 2. SHORTS VİDEO OLUŞTURMA (59 SN - DİKEY)
        print("📱 Dikey Shorts videosu hazırlanıyor...")
        shorts_loops = int(59 / (duration - crossfade_time)) + 1
        final_shorts = concatenate_videoclips([clip] * shorts_loops, method="compose", padding=-crossfade_time)
        final_shorts = final_shorts.subclip(0, 59)
        
        # Dikey Kesim (Center Crop 9:16) - Daha güvenli yöntem
        w, h = final_shorts.size
        target_w = h * (9/16)
        x1 = (w - target_w) / 2
        x2 = x1 + target_w
        final_shorts = final_shorts.crop(x1=x1, y1=0, x2=x2, y2=h)
        final_shorts = final_shorts.resize(height=1280) # Performans için 720x1280 (HD) yeterlidir
        
        final_shorts.write_videofile(SHORTS_VIDEO, codec="libx264", audio_codec="aac", fps=24, bitrate="2500k", threads=4, logger=None)
        final_shorts.close()
        print("✅ Shorts video dosyası oluşturuldu.")
        
        clip.close()
        return True
    except Exception as e:
        print(f"❌ MoviePy İşlem Hatası: {str(e)}")
        return False

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_all(youtube):
    long_id = None
    try:
        title = read_asset("title") or "Cozy Ambience"
        description = read_asset("desc") or "Relax and enjoy."
        tags = (read_asset("tags") or "ambience,relax").split(',')
        playlist_id = read_asset("playlist")

        # 1. ADIM: ANA VİDEO YÜKLEME
        if os.path.exists(TEMP_VIDEO):
            print(f"🚀 Ana Video Yükleniyor: {title}")
            body = {'snippet': {'title': f"{title} (1 HOUR)", 'description': description, 'tags': tags, 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
            media = MediaFileUpload(TEMP_VIDEO, chunksize=1024*1024, resumable=True)
            res_long = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
            long_id = res_long.get('id')
            print(f"✅ Ana Video Yayında: {long_id}")
            
            # Thumbnail ve Oynatma Listesi (Sadece ana video için)
            if os.path.exists(FILES["thumb"]):
                time.sleep(5)
                youtube.thumbnails().set(videoId=long_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
            if playlist_id:
                youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": long_id}}}).execute()
        
        # 2. ADIM: SHORTS YÜKLEME
        if os.path.exists(SHORTS_VIDEO):
            print("🚀 Shorts Video Yükleniyor...")
            s_desc = f"Watch the full 1-hour version here: https://youtu.be/{long_id}" if long_id else description
            s_body = {'snippet': {'title': f"{title} #shorts #relax", 'description': s_desc, 'tags': tags + ["shorts"], 'categoryId': '10'}, 'status': {'privacyStatus': 'public'}}
            s_media = MediaFileUpload(SHORTS_VIDEO, chunksize=1024*1024, resumable=True)
            res_s = youtube.videos().insert(part=','.join(s_body.keys()), body=s_body, media_body=s_media).execute()
            shorts_id = res_s.get('id')
            print(f"✅ Shorts Yayında: {shorts_id}")

            # 3. ADIM: SHORTS'A YORUM BIRAKMA
            if long_id:
                time.sleep(5)
                try:
                    youtube.commentThreads().insert(part="snippet", body={
                        'snippet': {
                            'videoId': shorts_id,
                            'topLevelComment': {'snippet': {'textOriginal': f"🎬 Watch the full 1-hour cinematic version here: https://youtu.be/{long_id}"}}
                        }
                    }).execute()
                    print("✅ Shorts yorumu bırakıldı.")
                except: print("⚠️ Yorum bırakılamadı (Yetki veya limit sorunu).")

    except Exception as e:
        print(f"💥 Yükleme Hatası: {str(e)}")

if __name__ == "__main__":
    if create_videos():
        y_service = get_authenticated_service()
        upload_all(y_service)
        # Temizlik
        for f in [TEMP_VIDEO, SHORTS_VIDEO]:
            if os.path.exists(f): os.remove(f)
    else:
        print("❌ Video oluşturulamadığı için yükleme iptal edildi.")
