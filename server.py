import os
import time
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Yapılandırma
TEMP_VIDEO = "current_video.mp4"
SHORTS_VIDEO = "shorts_video.mp4"
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

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

def create_videos():
    # Burada video oluşturma (Manim/FFmpeg) mantığınız yer alıyor
    # Örnek olarak dosya kontrolü yapıyoruz
    print("🚀 Videolar hazırlanıyor...")
    # Sizin sisteminizde video üretim süreci burada tetiklenir
    return True

def upload_process(youtube):
    try:
        print("📤 YouTube'a yükleniyor...")
        
        # Uzun Video Yükleme
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": "Aesthetic Relaxing Music (1 HOUR)",
                    "description": "Enjoy this cinematic ambiance.",
                    "tags": ["relaxing", "music", "ambiance"],
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
        long_id = response.get("id")
        print(f"✅ Uzun video yüklendi: {long_id}")

        # Playlist ve Shorts işlemleri buraya eklenebilir
        
    except Exception as e:
        print(f"💥 Yükleme Hatası: {e}")

if __name__ == "__main__":
    if create_videos():
        service = get_authenticated_service()
        upload_process(service)
        for f in [TEMP_VIDEO, SHORTS_VIDEO]:
            if os.path.exists(f):
                os.remove(f)
