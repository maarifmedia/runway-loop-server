import os
import time
import pickle
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- TEKNİK AYARLAR ---
TEMP_VIDEO = "current_video.mp4"
SHORTS_VIDEO = "shorts_video.mp4"
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['[https://www.googleapis.com/auth/youtube.upload](https://www.googleapis.com/auth/youtube.upload)']

def get_authenticated_service():
    """YouTube API bağlantısını kurar."""
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

def check_assets():
    """Video dosyalarının varlığını kontrol eder."""
    print("🔍 Dosya kontrolü yapılıyor...")
    if os.path.exists(TEMP_VIDEO):
        print(f"✅ Ana video bulundu: {TEMP_VIDEO}")
        return True
    else:
        print(f"❌ Hata: {TEMP_VIDEO} bulunamadı! İşlem durduruluyor.")
        return False

def upload_to_youtube(youtube):
    """Videoyu YouTube'a yükler."""
    try:
        print("📤 YouTube'a yükleme başlıyor...")
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": "Aesthetic Relaxing Music (1 HOUR)",
                    "description": "Autonomous cinematic ambiance. Published by @TheQuietCorner-yt",
                    "tags": ["relaxing", "music", "1hour", "ambiance"],
                    "categoryId": "10"
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(TEMP_VIDEO, chunksize=-1, resumable=True)
        )
        response = request.execute()
        print(f"🚀 Başarılı! Video ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"💥 Yükleme hatası: {e}")
        return False

def cleanup():
    """Geçici dosyaları siler."""
    print("🧹 Temizlik yapılıyor...")
    for f in [TEMP_VIDEO, SHORTS_VIDEO]:
        if os.path.exists(f):
            os.remove(f)
            print(f"🗑️ Silindi: {f}")

if __name__ == "__main__":
    print("🎬 Otomasyon Başlatıldı...")
    
    # 1. Adım: Dosyaları kontrol et
    if check_assets():
        # 2. Adım: Yetki al
        try:
            youtube_service = get_authenticated_service()
            
            # 3. Adım: Yükle
            if upload_to_youtube(youtube_service):
                # 4. Adım: Başarılıysa temizle
                cleanup()
                print("✨ Süreç başarıyla tamamlandı.")
            else:
                print("⚠️ Yükleme başarısız olduğu için dosyalar silinmedi.")
        except Exception as e:
            print(f"❌ Kritik hata: {e}")
    else:
        print("📭 İşlenecek dosya yok.")
