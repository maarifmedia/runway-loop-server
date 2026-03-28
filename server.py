import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v2.x uyumluluğu kontrolü
try:
    from moviepy import VideoFileClip, concatenate_videoclips
    HAS_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_V2 = False

# --- AYARLAR (Make.com ile tam uyumlu) ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
# SCOPE HATASINI ÇÖZEN KRİTİK SATIR: Sadece yükleme yetkisi istenir.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

INPUT_VIDEO = "assets/current_video.mp4" 
OUTPUT_VIDEO = "final_loop_video.mp4"
THUMBNAIL_IMAGE = "assets/s.png"

# Gemini (Make.com) tarafından gönderilen SEO dosyaları
TITLE_FILE = "assets/title.txt"
DESC_FILE = "assets/description.txt"
TAGS_FILE = "assets/tags.txt"

def read_asset_file(filepath, default_value=""):
    """Dosyayı okur, yoksa varsayılan metni döner."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            return default_value
    return default_value

def get_authenticated_service():
    """YouTube API kimlik doğrulama sürecini yönetir."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError("client_secrets.json bulunamadı!")
            
            # Yerel test için tarayıcı açar, GitHub'da TOKEN_JSON kullanılmalıdır.
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    """Veo 3 videosunu 1 saatlik döngüye sokar."""
    print(f"--- Video İşleme Başladı (Döngü Süresi: {target_minutes} dk) ---")
    clip = VideoFileClip(input_path)
    
    target_seconds = target_minutes * 60
    iterations = int(target_seconds / clip.duration) + 1
    
    print(f"Video {iterations} kez uç uca ekleniyor...")
    final_clip = concatenate_videoclips([clip] * iterations)
    
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    print("Video Render ediliyor (Lütfen bekleyin)...")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    
    clip.close()
    final_clip.close()
    print("--- Render Tamamlandı! ---")

def upload_video(youtube, file_path):
    """Videoyu YouTube'a yükler ve Gemini SEO bilgilerini uygular."""
    # Gemini'den gelen dinamik verileri oku
    title = read_asset_file(TITLE_FILE, f"Deep Focus Ambiance - {datetime.datetime.now().strftime('%B %Y')}")
    description = read_asset_file(DESC_FILE, "Welcome to @TheQuietCorner-yt. Enjoy this Veo 3 ambiance.")
    tags_raw = read_asset_file(TAGS_FILE, "ambiance,relax,veo3")
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

    print(f"Yüklenen Başlık: {title}")

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '10' # Müzik kategorisi
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
    video_id = response.get('id')
    print(f"Başarılı! Video yüklendi: https://youtu.be/{video_id}")
    
    # Kapak fotoğrafını (s.png) yükle
    if os.path.exists(THUMBNAIL_IMAGE):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("Kapak fotoğrafı güncellendi!")
        except Exception as e:
            print(f"Thumbnail hatası (Muhtemelen henüz hazır değil): {e}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"HATA: {INPUT_VIDEO} dosyası bulunamadı!")
    except Exception as e:
        print(f"SİSTEM HATASI: {str(e)}")
