import os
import datetime
import time
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- AYARLAR ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

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

def get_authenticated_service():
    try:
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("❌ Token geçersiz ve yenilenemiyor. Lütfen bilgisayarınızda yeni bir token.json üretip GitHub Secrets'a yapıştırın.")
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"🛑 Kimlik Doğrulama Hatası: {e}")
        sys.exit(1)

def upload_video(youtube):
    try:
        title = read_asset("title") or f"Relaxing Ambience - {datetime.datetime.now().strftime('%Y')}"
        description = read_asset("desc") or "Cozy vibes for your soul. @TheQuietCorner-yt"
        tags = read_asset("tags").split(',') if read_asset("tags") else ["ambiance", "relax"]
        playlist_id = read_asset("playlist")

        print(f"🚀 Hazırlanıyor: {title}")

        body = {
            'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '10'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }

        media = MediaFileUpload(FILES["video"], chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        print("📤 Video yükleme başladı...")
        response = request.execute()
        video_id = response.get('id')
        print(f"✅ Video yüklendi! ID: {video_id}")

        # Küçük Resim (Thumbnail)
        if os.path.exists(FILES["thumb"]):
            print("🖼️ Küçük resim yükleniyor...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
            print("✅ Küçük resim ayarlandı.")
        
        # Oynatma Listesi
        if playlist_id:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            print(f"📂 Oynatma listesine eklendi: {playlist_id}")

        print(f"✨ İşlem başarıyla tamamlandı!")

    except Exception as e:
        print(f"💥 Yükleme Sırasında Hata Oluştu: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists(FILES["video"]):
        print(f"❌ HATA: {FILES['video']} bulunamadı!")
        sys.exit(1)
        
    service = get_authenticated_service()
    upload_video(service)
