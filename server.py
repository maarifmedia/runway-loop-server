import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- DOSYA YOLLARI ---
ASSETS_DIR = "assets/"
TEMP_VIDEO = f"{ASSETS_DIR}current_video.mp4"
SHORTS_VIDEO = f"{ASSETS_DIR}shorts_video.mp4"
THUMBNAIL = f"{ASSETS_DIR}s.png"
PLAYLIST_FILE = f"{ASSETS_DIR}playlist.txt"
# SEO Dosyaları
TITLE_FILE = f"{ASSETS_DIR}title.txt"
DESC_FILE = f"{ASSETS_DIR}description.txt"
TAGS_FILE = f"{ASSETS_DIR}tags.txt"

TOKEN_FILE = "token.pickle"
CLIENT_SECRETS_FILE = "client_secrets.json"

def get_authenticated_service():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    return build('youtube', 'v3', credentials=credentials)

def read_asset_file(file_path, default_text):
    """SEO dosyalarını okur, dosya yoksa varsayılan metni döner."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else default_text
    return default_text

def upload_video(youtube, file_path, title, description, tags, is_shorts=False, playlist_id=None):
    if not os.path.exists(file_path): return None
    try:
        print(f"📤 {title} yükleniyor...")
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags.split(','),
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status: print(f"⏳ %{int(status.progress() * 100)}")
        
        v_id = response.get("id")
        
        # Thumbnail Yükleme (Resumable)
        if not is_shorts and os.path.exists(THUMBNAIL):
            thumb_media = MediaFileUpload(THUMBNAIL, mimetype='image/png', resumable=True)
            youtube.thumbnails().set(videoId=v_id, media_body=thumb_media).execute()
            print("🖼️ Küçük resim eklendi.")

        # Oynatma Listesine Ekle
        if playlist_id and not is_shorts:
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": v_id}}}
            ).execute()
            print(f"📂 Oynatma listesine eklendi.")
            
        return v_id
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None

if __name__ == "__main__":
    service = get_authenticated_service()
    
    # 📝 SEO Verilerini Oku
    video_title = read_asset_file(TITLE_FILE, "Aesthetic Relaxing Music (1 HOUR)")
    video_desc = read_asset_file(DESC_FILE, "Enjoy this relaxing loop.")
    video_tags = read_asset_file(TAGS_FILE, "relaxing,ambiance,1hour")
    
    # 📂 Playlist ID Oku
    target_playlist = read_asset_file(PLAYLIST_FILE, None)

    # 1. ANA VİDEO YÜKLE
    main_id = upload_video(service, TEMP_VIDEO, video_title, video_desc, video_tags, playlist_id=target_playlist)
    
    # 2. SHORTS YÜKLE
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        s_title = video_title[:60] + " #shorts" # Shorts için başlığı kırp
        upload_video(service, SHORTS_VIDEO, s_title, f"Full version: {m_url}", "shorts,relax", is_shorts=True)
