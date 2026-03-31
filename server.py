import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- YAPILANDIRMA ---
TEMP_VIDEO = "assets/current_video.mp4"
SHORTS_VIDEO = "assets/shorts_video.mp4"
THUMBNAIL = "assets/s.png"
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
        else:
            raise Exception("❌ HATA: Geçerli bir token bulunamadı!")

    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment_text}}
                }
            }
        ).execute()
        print(f"💬 Yorum eklendi: {video_id}")
    except Exception as e:
        print(f"⚠️ Yorum hatası: {e}")

def upload_video(youtube, file_path, title, description, is_shorts=False):
    if not os.path.exists(file_path):
        print(f"⚠️ Dosya bulunamadı: {file_path}")
        return None

    try:
        print(f"📤 {title} yükleniyor (Büyük dosya modu aktif)...")
        
        # KRİTİK DÜZELTME: Büyük dosyalar için chunksize (parça boyutu) eklendi
        # 1024 * 1024 = 1MB. Burada 5MB'lık parçalar halinde gönderiyoruz.
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relaxing", "1hour"] if not is_shorts else ["shorts"],
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=media
        )

        # Yükleme işlemini parçalı şekilde başlat ve takip et
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"⏳ Yükleme yüzdesi: %{int(status.progress() * 100)}")
        
        video_id = response.get("id")
        
        # Ana video için Thumbnail
        if not is_shorts and os.path.exists(THUMBNAIL):
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
            print("🖼️ Küçük resim eklendi.")
            
        print(f"✅ Yükleme tamamlandı: {video_id}")
        return video_id
    except Exception as e:
        print(f"❌ Yükleme Hatası: {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Devrede...")
    try:
        service = get_authenticated_service()
        
        # 1. ANA VİDEO
        main_video_id = upload_video(service, TEMP_VIDEO, "Aesthetic Relaxing Music (1 HOUR)", "Enjoy the loop.")

        # 2. SHORTS
        if main_video_id and os.path.exists(SHORTS_VIDEO):
            m_url = f"https://www.youtube.com/watch?v={main_video_id}"
            shorts_id = upload_video(service, SHORTS_VIDEO, "Relaxing Escape #shorts", f"Full version: {m_url}", is_shorts=True)
            
            if shorts_id:
                add_comment(service, shorts_id, f"🌿 Watch the full 1-hour version: {m_url}")

        print("✨ Süreç başarıyla bitti.")
    except Exception as e:
        print(f"💥 Kritik Hata: {e}")
