import os
import json
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- YAPILANDIRMA ---
TEMP_VIDEO = "assets/current_video.mp4"
SHORTS_VIDEO = "assets/shorts_video.mp4"
THUMBNAIL = "assets/s.png"
CLIENT_SECRETS_FILE = "client_secrets.json"
# GitHub .yml dosyasının oluşturduğu isimle eşleşmeli
TOKEN_FILE = "token.pickle" 

def get_authenticated_service():
    credentials = None
    # .yml tarafından oluşturulan token.json dosyasını oku
    if os.path.exists(TOKEN_FILE):
        try:
            credentials = Credentials.from_authorized_user_file(TOKEN_FILE)
        except Exception:
            # Eğer JSON değilse eski usul pickle dene (Geriye dönük uyumluluk)
            with open(TOKEN_FILE, 'rb') as token:
                credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise Exception("❌ HATA: Geçerli bir token bulunamadı! Lütfen Secrets kısmını kontrol edin.")

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

def upload_video(youtube, file_path, title, description, is_shorts=False):
    if not os.path.exists(file_path):
        print(f"⚠️ Dosya bulunamadı: {file_path}")
        return None
    try:
        print(f"📤 {title} yükleniyor...")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["relax", "shorts"] if is_shorts else ["relaxing", "1hour"],
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        v_id = response.get("id")
        print(f"✅ Başarılı: {v_id}")
        return v_id
    except Exception as e:
        print(f"❌ Yükleme Hatası: {e}")
        return None

if __name__ == "__main__":
    service = get_authenticated_service()
    main_id = upload_video(service, TEMP_VIDEO, "Aesthetic Relaxing Music (1 HOUR)", "Enjoy this 1-hour loop. #relaxing")
    
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        s_id = upload_video(service, SHORTS_VIDEO, "Relaxing Escape #shorts", f"Full version: {m_url}", is_shorts=True)
        if s_id:
            add_comment(service, s_id, f"🌿 Watch the full version here: {m_url}")
