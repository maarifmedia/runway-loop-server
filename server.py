import os
import pickle
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- DOSYA YOLLARI ---
ASSETS_DIR = "assets/"
TEMP_VIDEO = f"{ASSETS_DIR}current_video.mp4"
SHORTS_VIDEO = f"{ASSETS_DIR}shorts_video.mp4"
THUMBNAIL = f"{ASSETS_DIR}s.png"
PLAYLIST_FILE = f"{ASSETS_DIR}playlist_id.txt"
TITLE_FILE = f"{ASSETS_DIR}title.txt"
DESC_FILE = f"{ASSETS_DIR}description.txt"
TAGS_FILE = f"{ASSETS_DIR}tags.txt"
TOKEN_FILE = "token.pickle"

def add_comment(youtube, video_id, text):
    """Shorts videosuna otomatik yorum ekler."""
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": text}
                    }
                }
            }
        ).execute()
        print(f"💬 Yorum eklendi: {video_id}")
    except Exception as e:
        print(f"⚠️ Yorum hatası: {e}")

def optimize_thumbnail(input_path):
    """Resmi 2MB altına indirmek için JPEG 75 kalite uygular."""
    if os.path.exists(input_path):
        size_mb = os.path.getsize(input_path) / (1024 * 1024)
        if size_mb > 1.9:
            print(f"⚠️ Resim optimize ediliyor ({size_mb:.2f}MB)...")
            img = Image.open(input_path).convert("RGB")
            img.save(input_path, "JPEG", quality=75, optimize=True)
            print(f"✅ Yeni boyut: {os.path.getsize(input_path) / (1024 * 1024):.2f}MB")

def get_authenticated_service():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    return build('youtube', 'v3', credentials=credentials)

def read_asset(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else default
    return default

def upload_video(youtube, file_path, title, description, tags, is_shorts=False, playlist_id=None):
    if not os.path.exists(file_path): return None
    try:
        print(f"📤 {title} yükleniyor...")
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "tags": tags.split(','), "categoryId": "10"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=media
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status: print(f"⏳ %{int(status.progress() * 100)}")
        
        v_id = response.get("id")
        
        if not is_shorts and os.path.exists(THUMBNAIL):
            try:
                optimize_thumbnail(THUMBNAIL)
                youtube.thumbnails().set(videoId=v_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
                print("🖼️ Kapak eklendi.")
            except: pass

        if playlist_id and not is_shorts:
            try:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": v_id}}}
                ).execute()
                print("📂 Listeye eklendi.")
            except: pass
            
        return v_id
    except Exception as e:
        print(f"❌ Kritik Hata: {e}")
        return None

if __name__ == "__main__":
    service = get_authenticated_service()
    title = read_asset(TITLE_FILE, "Relaxing Ambiance (1 HOUR)")
    desc = read_asset(DESC_FILE, "Relaxing loop.")
    tags = read_asset(TAGS_FILE, "relaxing,1hour")
    p_id = read_asset(PLAYLIST_FILE, None)

    # 1. ANA VİDEO
    main_id = upload_video(service, TEMP_VIDEO, title, desc, tags, playlist_id=p_id)
    
    # 2. SHORTS VE YORUM
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        s_id = upload_video(service, SHORTS_VIDEO, title[:50] + " #shorts", f"Full version: {m_url}", "shorts,relax", is_shorts=True)
        
        if s_id:
            comment_text = f"🌿 Watch the full 1-hour version here: {m_url}"
            add_comment(service, s_id, comment_text)
