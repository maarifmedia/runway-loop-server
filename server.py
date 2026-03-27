import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v2.x uyumluluğu
try:
    from moviepy import VideoFileClip, concatenate_videoclips
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips

# --- YAPILANDIRMA ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
INPUT_VIDEO = "assets/current_video.mp4" 
OUTPUT_VIDEO = "final_loop_video.mp4"   

def get_authenticated_service():
    """YouTube API kimlik doğrulama sürecini yönetir."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Bulut ortamında (GitHub Actions) etkileşimli giriş yapılamaz.
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError("Kimlik dosyası bulunamadı!")
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    """Veo 3 videosunu (sesiyle birlikte) 1 saatlik döngüye sokar."""
    print(f"--- Veo 3 İşleniyor: {input_path} ---")
    clip = VideoFileClip(input_path)
    
    target_seconds = target_minutes * 60
    iterations = int(target_seconds / clip.duration) + 1
    
    print(f"Video {iterations} kez döngüye alınıyor...")
    # Sesiyle beraber uç uca ekle
    final_clip = concatenate_videoclips([clip] * iterations)
    
    # Tam süreye ayarla
    final_clip = final_clip.with_duration(target_seconds)
    
    print("Video dosyası oluşturuluyor (Render)...")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    
    clip.close()
    final_clip.close()
    print("--- 1 Saatlik Video Hazır! ---")

def upload_video(youtube, file_path):
    """YouTube'a yükleme yapar."""
    now = datetime.datetime.now()
    body = {
        'snippet': {
            'title': f"Deep Focus Ambiance - {now.strftime('%B %Y')} | Aesthetic Loop",
            'description': 'Welcome to your quiet corner. Relax and focus with this Veo 3 generated ambiance. #ambiance #cozy #peaceful #thequietcorner',
            'tags': ['ambiance', 'cozy', 'study', 'relax', 'veo3'],
            'categoryId': '10'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    print("YouTube'a yükleme başladı...")
    response = request.execute()
    print(f"Başarılı! Video yüklendi. ID: {response.get('id')}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"Hata: {INPUT_VIDEO} bulunamadı!")
    except Exception as e:
        print(f"Hata: {str(e)}")
