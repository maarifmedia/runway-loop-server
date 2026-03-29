import os
import datetime
import time
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

# Dosya Yolları
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
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def add_to_playlist(youtube, video_id, playlist_id):
    if not playlist_id: return
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
        print(f"✅ Oynatma listesine eklendi: {playlist_id}")
    except Exception as e:
        print(f"⚠️ Oynatma listesi hatası: {e}")

def upload_video(youtube):
    title = read_asset("title") or f"Relaxing Ambience - {datetime.datetime.now().strftime('%Y')}"
    description = read_asset("desc") or "Cozy vibes for your soul. @TheQuietCorner-yt"
    tags = read_asset("tags").split(',') if read_asset("tags") else ["ambiance", "relax"]
    playlist_id = read_asset("playlist")

    print(f"🚀 Yükleniyor: {title}")

    body = {
        'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '10'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }

    media = MediaFileUpload(FILES["video"], chunksize=-1, resumable=True)
    response = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
    video_id = response.get('id')

    # Küçük Resim
    if os.path.exists(FILES["thumb"]):
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(FILES["thumb"])).execute()
    
    # Oynatma Listesi
    add_to_playlist(youtube, video_id, playlist_id)
    print(f"✨ Bitti! Video ID: {video_id}")

if __name__ == "__main__":
    service = get_authenticated_service()
    if os.path.exists(FILES["video"]):
        upload_video(service)
