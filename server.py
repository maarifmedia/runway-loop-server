import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- YAPILANDIRMA (Görseldeki Assets Klasörüne Göre) ---
# .yml dosyasında FFmpeg ile işlenen videoların yolları
TEMP_VIDEO = "assets/current_video.mp4"    # 1 Saatlik Loop Yapılmış Ana Video
SHORTS_VIDEO = "assets/shorts_video.mp4"  # 9:16 Dikey Kesilmiş Shorts
THUMBNAIL = "assets/s.png"                # Kapak Resmi
TOKEN_FILE = "token.pickle"                # .yml tarafından oluşturulan anahtar
CLIENT_SECRETS_FILE = "client_secrets.json"

def get_authenticated_service():
    """GitHub Secrets'tan gelen anahtarı kullanarak YouTube'a bağlanır."""
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise Exception("❌ HATA: Geçerli bir token bulunamadı! Lütfen Secrets kısmını kontrol edin.")

    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    """Shorts altına ana videonun linkini yorum olarak bırakır."""
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
    """Videoyu yükler ve ana video ise küçük resmi ayarlar."""
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
                    "tags": ["relaxing", "ambiance", "1hour"] if not is_shorts else ["shorts", "relax"],
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
        
        # Ana video için Thumbnail (Küçük Resim) yükle
        if not is_shorts and os.path.exists(THUMBNAIL):
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(THUMBNAIL)
            ).execute()
            print("🖼️ Küçük resim başarıyla eklendi.")
            
        print(f"✅ Yükleme tamamlandı: {video_id}")
        return video_id
    except Exception as e:
        print(f"❌ Yükleme Hatası ({title}): {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Devrede...")
    
    try:
        youtube_service = get_authenticated_service()
        
        # 1. ADIM: ANA VİDEOYU YÜKLE (1 SAATLİK)
        main_video_id = upload_video(
            youtube_service, 
            TEMP_VIDEO, 
            "Aesthetic Relaxing Music (1 HOUR)", 
            "Enjoy this 1-hour loop of cinematic ambiance. #relaxing #1hour #ambiance"
        )

        # 2. ADIM: SHORTS YÜKLE VE ANA VİDEOYA LİNK VER
        if main_video_id and os.path.exists(SHORTS_VIDEO):
            main_url = f"https://www.youtube.com/watch?v={main_video_id}"
            
            shorts_id = upload_video(
                youtube_service, 
                SHORTS_VIDEO, 
                "Relaxing Escape #shorts", 
                f"Watch the full 1-hour version here: {main_url} ✨", 
                is_shorts=True
            )
            
            # 3. ADIM: SHORTS ALTINA YORUM AT
            if shorts_id:
                comment_text = f"🌿 Deep relaxation starts here! Watch the full 1-hour version: {main_url}"
                add_comment(youtube_service, shorts_id, comment_text)

        print("✨ Tüm süreç başarıyla tamamlandı.")

    except Exception as e:
        print(f"💥 Kritik Hata: {e}")
