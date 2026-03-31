import os
import time
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- YAPILANDIRMA ---
TEMP_VIDEO = "current_video.mp4"    # 1 Saatlik Ana Video
SHORTS_VIDEO = "shorts_video.mp4"  # Shorts Video
THUMBNAIL = "s.png"                # Kapak Resmi
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload', 
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
PLAYLIST_ID = "PL_MUZIKLI_ID" # Buraya kendi Playlist ID'ni yapıştır

def get_authenticated_service():
    """YouTube bağlantısını kurar. Tarayıcı hatasını engellemek için sadece Token kullanır."""
    credentials = None
    # 1. Önce mevcut token.pickle dosyasını kontrol et
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    # 2. Eğer token yoksa veya geçersizse
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("🔄 Token süresi dolmuş, yenileniyor...")
            credentials.refresh(Request())
        else:
            # KRİTİK DÜZELTME: Sunucuda tarayıcı açılamayacağı için burada durduruyoruz.
            # Bu hata gelirse, bilgisayarınızda token.pickle oluşturup yüklemelisiniz.
            raise Exception("❌ HATA: token.pickle bulunamadı! Lütfen yerel bilgisayarınızda bir kez çalıştırıp oluşan dosyayı GitHub'a yükleyin.")
            
        # Yenilenen veya yeni alınan tokenı kaydet
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return build('youtube', 'v3', credentials=credentials)

def add_comment(youtube, video_id, comment_text):
    """Videoya link içeren ilk yorumu atar."""
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
    """SEO uyumlu yükleme yapar."""
    if not os.path.exists(file_path):
        print(f"⚠️ Dosya eksik: {file_path}")
        return None
    try:
        print(f"📤 {title} yükleniyor...")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relaxing", "shorts"] if is_shorts else ["relaxing", "1hour", "ambiance"],
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        video_id = response.get("id")
        
        # Ana video özelleştirmeleri
        if not is_shorts:
            if os.path.exists(THUMBNAIL):
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
                print("🖼️ Küçük resim yüklendi.")
            if PLAYLIST_ID:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={"snippet": {"playlistId": PLAYLIST_ID, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
                ).execute()
                print("🔗 Oynatma listesine eklendi.")
        return video_id
    except Exception as e:
        print(f"❌ Yükleme hatası: {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Başlatıldı...")
    try:
        service = get_authenticated_service()
        main_id = None

        # 1. ANA VİDEO
        if os.path.exists(TEMP_VIDEO):
            main_id = upload_video(service, TEMP_VIDEO, "Aesthetic Relaxing Music (1 HOUR)", "1-hour cinematic loop. ✨")

        # 2. SHORTS VE YORUM BAĞLANTISI
        if os.path.exists(SHORTS_VIDEO) and main_id:
            m_url = f"https://www.youtube.com/watch?v={main_id}"
            s_id = upload_video(service, SHORTS_VIDEO, "Relaxing Escape #shorts", f"Full version: {m_url}", is_shorts=True)
            
            if s_id:
                add_comment(service, s_id, f"🌿 Watch the full 1-hour version here: {m_url}")

        # 3. TEMİZLİK
        for f in [TEMP_VIDEO, SHORTS_VIDEO, THUMBNAIL]:
            if os.path.exists(f): os.remove(f)
        print("✨ Süreç başarıyla tamamlandı.")

    except Exception as e:
        print(f"💥 Sistem Durduruldu: {e}")
