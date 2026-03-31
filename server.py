import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- YAPILANDIRMA ---
TEMP_VIDEO = "assets/current_video.mp4"
SHORTS_VIDEO = "assets/shorts_video.mp4"
THUMBNAIL = "assets/s.png"
PLAYLIST_FILE = "assets/playlist.txt"  # Make.com'dan gelen ID dosyası
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

def get_target_playlist():
    """playlist.txt içindeki ID'yi okur, yoksa None döner."""
    if os.path.exists(PLAYLIST_FILE):
        with open(PLAYLIST_FILE, 'r') as f:
            playlist_id = f.read().strip()
            if playlist_id:
                print(f"📂 Hedef Oynatma Listesi Belirlendi: {playlist_id}")
                return playlist_id
    print("⚠️ playlist.txt bulunamadı veya boş, listeye eklenmeyecek.")
    return None

def upload_video(youtube, file_path, title, description, is_shorts=False, playlist_id=None):
    if not os.path.exists(file_path): return None
    try:
        print(f"📤 {title} yükleniyor...")
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "categoryId": "10"},
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
            youtube.thumbnails().set(videoId=v_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
            print("🖼️ Küçük resim eklendi.")

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
    playlist_id = get_target_playlist() # Dosyadan ID'yi oku

    # 1. ANA VİDEO
    main_id = upload_video(service, TEMP_VIDEO, "Aesthetic Relaxing Music (1 HOUR)", "Enjoy the loop.", playlist_id=playlist_id)
    
    # 2. SHORTS
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        shorts_id = upload_video(service, SHORTS_VIDEO, "Relaxing Escape #shorts", f"Full version: {m_url}", is_shorts=True)
        # Shorts altına yorum ekleme kodu buraya eklenebilir...
