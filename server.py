import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- YAPILANDIRMA ---
TEMP_VIDEO = "assets/current_video.mp4"    # 1 Saatlik Ana Video
SHORTS_VIDEO = "assets/shorts_video.mp4"  # Dikey Kesilmiş Shorts
THUMBNAIL = "assets/s.png"                # Kapak Resmi
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS_FILE = "client_secrets.json"

# --- OYNATMA LİSTESİ ID'LERİ ---
PL_MELODIC_ID = "PLBSKEl0NRvK--0dqTjSY61Jx6I3gX74iH"
PL_NATURE_ID = "PLBSKEl0NRvK_EW7SZvIqgeEO3nR3mA5_9"

def get_authenticated_service():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise Exception("❌ HATA: Geçerli bir token bulunamadı!")
    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": comment_text}}}}
        ).execute()
        print(f"💬 Yorum eklendi: {video_id}")
    except Exception as e:
        print(f"⚠️ Yorum hatası: {e}")

def upload_video(youtube, file_path, title, description, is_shorts=False, playlist_id=None):
    if not os.path.exists(file_path):
        print(f"⚠️ Dosya bulunamadı: {file_path}")
        return None

    try:
        print(f"📤 {title} yükleniyor (Parçalı yükleme aktif)...")
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relaxing", "ambiance", "1hour"] if not is_shorts else ["shorts", "relax"],
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"⏳ Yükleme yüzdesi: %{int(status.progress() * 100)}")
        
        video_id = response.get("id")
        
        # 🖼️ Ana Video ise Küçük Resim Ekle
        if not is_shorts and os.path.exists(THUMBNAIL):
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
            print("🖼️ Küçük resim başarıyla eklendi.")

        # 📂 Oynatma Listesine Ekle
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
            print(f"📂 Oynatma listesine eklendi (ID: {playlist_id})")
            
        print(f"✅ Başarılı: {video_id}")
        return video_id
    except Exception as e:
        print(f"❌ Yükleme Hatası: {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Başlatıldı...")
    try:
        service = get_authenticated_service()
        
        # Oynatma listesi seçimi (Varsayılan olarak Doğa seçili, 
        # Make.com'dan gelen veriye göre bunu otomatize edebiliriz)
        target_playlist = PL_NATURE_ID 

        # 1. ANA VİDEOYU YÜKLE
        main_video_id = upload_video(
            service, 
            TEMP_VIDEO, 
            "Aesthetic Relaxing Music (1 HOUR)", 
            "Enjoy this 1-hour loop of cinematic ambiance. #relaxing #1hour #ambiance",
            playlist_id=target_playlist
        )

        # 2. SHORTS YÜKLE VE LİNKLE
        if main_video_id and os.path.exists(SHORTS_VIDEO):
            main_url = f"https://www.youtube.com/watch?v={main_video_id}"
            shorts_id = upload_video(
                service, 
                SHORTS_VIDEO, 
                "Relaxing Escape #shorts", 
                f"Watch the full 1-hour version here: {main_url}", 
                is_shorts=True
            )
            
            if shorts_id:
                comment_text = f"🌿 Watch the full 1-hour version: {main_url}"
                add_comment(service, shorts_id, comment_text)

        print("✨ Tüm işlemler başarıyla tamamlandı.")
    except Exception as e:
        print(f"💥 Kritik Hata: {e}")
