import os
import time
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- YAPILANDIRMA (SEO VE TEKNİK) ---
TEMP_VIDEO = "current_video.mp4"    # 1 Saatlik Loop Video
SHORTS_VIDEO = "shorts_video.mp4"  # Shorts Video
THUMBNAIL = "s.png"                # Hazırlanan Küçük Resim
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']
PLAYLIST_ID = "PL_MUZIKLI_ID"      # Playlist ID'n

def get_authenticated_service():
    credentials = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    """Videoya yönlendirme içeren ilk yorumu atar."""
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": comment_text}}}}
        ).execute()
        print(f"💬 Yorum eklendi: {video_id}")
    except Exception as e:
        print(f"⚠️ Yorum hatası: {e}")

def upload_video(youtube, file_path, title, description, is_shorts=False):
    """SEO uyumlu yükleme yapar."""
    if not os.path.exists(file_path):
        return None
    try:
        print(f"📤 {title} yükleniyor...")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relaxing music", "ambiance", "sleep music", "shorts"] if is_shorts else ["relaxing music", "1 hour loop", "study music", "ambiance"],
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        video_id = response.get("id")
        
        # Thumbnail ekle (Sadece ana video için)
        if not is_shorts and os.path.exists(THUMBNAIL):
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
            print("🖼️ Küçük resim eklendi.")
            
        return video_id
    except Exception as e:
        print(f"❌ Yükleme hatası: {e}")
        return None

if __name__ == "__main__":
    service = get_authenticated_service()
    
    # 1. ADIM: ANA VİDEOYU YÜKLE (1 SAATLİK LOOP)
    main_video_id = None
    if os.path.exists(TEMP_VIDEO):
        main_video_id = upload_video(
            service, 
            TEMP_VIDEO, 
            "Aesthetic Relaxing Music (1 HOUR)", 
            "Immerse yourself in this 1-hour cinematic ambiance. Perfect for study, sleep, or relaxation. ✨ #relaxing #ambiance"
        )
        
    # 2. ADIM: SHORTS YÜKLE VE ANA VİDEOYA LİNK VER
    if os.path.exists(SHORTS_VIDEO) and main_video_id:
        main_url = f"https://www.youtube.com/watch?v={main_video_id}"
        shorts_id = upload_video(
            service, 
            SHORTS_VIDEO, 
            "Relaxing Escape #shorts", 
            f"Watch the full 1-hour version here: {main_url} 🌿", 
            is_shorts=True
        )
        
        # 3. ADIM: SHORTS ALTINA İLK YORUMU AT (LİNK İLE)
        if shorts_id:
            comment_text = f"✨ Experience the full 1-hour version for deep relaxation: {main_url}"
            add_comment(service, shorts_id, comment_text)

    # 4. ADIM: TEMİZLİK
    for f in [TEMP_VIDEO, SHORTS_VIDEO, THUMBNAIL]:
        if os.path.exists(f): os.remove(f)
    print("✨ Tüm sistem başarıyla çalıştı.")
