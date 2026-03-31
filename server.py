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
# ÖNEMLİ: Yorum yapabilmek için 'force-ssl' yetkisi eklendi
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload', 
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
PLAYLIST_ID = "PL_MUZIKLI_ID"      # Kendi Playlist ID'niz

def get_authenticated_service():
    """YouTube API bağlantısını kurar ve Token kontrolü yapar."""
    credentials = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Sunucu ortamında tarayıcı açılmayacağı için hata vermemesi adına
            # Bu kısmın daha önce yerelde 'token.pickle' oluşturmuş olması gerekir.
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    """Videoya ilk yorumu bırakır."""
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
        ).execute()
        print(f"💬 Yorum eklendi: {video_id}")
    except Exception as e:
        print(f"⚠️ Yorum hatası: {e}")

def upload_video(youtube, file_path, title, description, is_shorts=False):
    """SEO uyumlu video yükleme ve opsiyonel Thumbnail/Playlist işlemi."""
    if not os.path.exists(file_path):
        print(f"⚠️ Dosya bulunamadı, atlanıyor: {file_path}")
        return None

    try:
        print(f"📤 {title} yükleniyor...")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relaxing music", "shorts", "ambiance"] if is_shorts else ["relaxing music", "1 hour loop", "ambiance", "sleep music"],
                    "categoryId": "10"
                },
                "status": {
                    "privacyStatus": "public", 
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        video_id = response.get("id")
        
        # Ana video için Thumbnail ve Playlist ekle
        if not is_shorts:
            if os.path.exists(THUMBNAIL):
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
                print("🖼️ Küçük resim eklendi.")
            
            if PLAYLIST_ID:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": PLAYLIST_ID,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id}
                        }
                    }
                ).execute()
                print("🔗 Oynatma listesine eklendi.")
            
        return video_id
    except Exception as e:
        print(f"❌ Yükleme Hatası ({title}): {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Devrede...")
    
    try:
        youtube_service = get_authenticated_service()
        main_video_id = None

        # 1. ANA VİDEOYU YÜKLE (1 SAATLİK)
        if os.path.exists(TEMP_VIDEO):
            main_video_id = upload_video(
                youtube_service, 
                TEMP_VIDEO, 
                "Aesthetic Relaxing Music (1 HOUR)", 
                "Enjoy this 1-hour loop of cinematic ambiance. #relaxing #1hour #ambiance"
            )

        # 2. SHORTS YÜKLE VE ANA VİDEOYA LİNK VER
        if os.path.exists(SHORTS_VIDEO) and main_video_id:
            main_url = f"https://www.youtube.com/watch?v={main_video_id}"
            
            shorts_id = upload_video(
                youtube_service, 
                SHORTS_VIDEO, 
                "Relaxing Escape #shorts", 
                f"Experience the full 1-hour version here: {main_url} ✨", 
                is_shorts=True
            )
            
            # 3. SHORTS ALTINA İLK YORUMU AT (LİNK İLE)
            if shorts_id:
                comment_text = f"🌿 Deep relaxation starts here! Watch the full 1-hour version: {main_url}"
                add_comment(youtube_service, shorts_id, comment_text)

        # 4. TEMİZLİK
        print("🧹 Geçici dosyalar temizleniyor...")
        for f in [TEMP_VIDEO, SHORTS_VIDEO, THUMBNAIL]:
            if os.path.exists(f):
                os.remove(f)
        
        print("✨ Tüm sistem başarıyla tamamlandı.")

    except Exception as e:
        print(f"💥 Kritik Sistem Hatası: {e}")
