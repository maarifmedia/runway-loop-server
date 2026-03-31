import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- AYARLAR ---
TEMP_VIDEO = "assets/current_video.mp4"
SHORTS_VIDEO = "assets/shorts_video.mp4"
THUMBNAIL = "assets/s.png"
TOKEN_FILE = "token.pickle"

# Oynatma Listesi ID'leri (Senin ID'lerinle değiştir)
PL_MELODIC_ID = "PL_MUZIKLI_ID" 
PL_NATURE_ID = "PL_DOGA_ID"

def get_authenticated_service():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    return build('youtube', 'v3', credentials=credentials)

def upload_video(youtube, file_path, title, description, is_shorts=False, playlist_id=None):
    if not os.path.exists(file_path): return None
    
    print(f"📤 {title} yükleniyor...")
    media = MediaFileUpload(file_path, chunksize=5*1024*1024, resumable=True)
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
    
    # 🖼️ Küçük Resim Ekle (Ana Video için)
    if not is_shorts and os.path.exists(THUMBNAIL):
        youtube.thumbnails().set(videoId=v_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
        print("🖼️ Küçük resim eklendi.")
    
    # 📂 Oynatma Listesine Ekle
    if playlist_id:
        youtube.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": v_id}}}
        ).execute()
        print(f"📂 Oynatma listesine eklendi.")
        
    return v_id

if __name__ == "__main__":
    service = get_authenticated_service()
    
    # Not: sound_choice'a göre playlist_id belirle (Örn: Doğa sesi ise PL_NATURE_ID)
    # Şimdilik varsayılan olarak Nature seçili.
    target_playlist = PL_NATURE_ID 
    
    main_id = upload_video(service, TEMP_VIDEO, "Aesthetic Relaxing Music (1 HOUR)", "Relaxing loop.", playlist_id=target_playlist)
    
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        upload_video(service, SHORTS_VIDEO, "Relaxing Escape #shorts", f"Full: {m_url}", is_shorts=True)
