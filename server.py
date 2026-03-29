import os
import datetime
import time
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v2.x uyumluluğu
try:
    from moviepy import VideoFileClip, concatenate_videoclips
    HAS_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_V2 = False

# --- AYARLAR ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Dosya yollarını kesinleştir (Absolute path mantığı)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

INPUT_VIDEO = os.path.join(ASSETS_DIR, "current_video.mp4") 
OUTPUT_VIDEO = os.path.join(BASE_DIR, "final_loop_video.mp4")
THUMBNAIL_IMAGE = os.path.join(ASSETS_DIR, "s.png")

TITLE_FILE = os.path.join(ASSETS_DIR, "title.txt")
DESC_FILE = os.path.join(ASSETS_DIR, "description.txt")
TAGS_FILE = os.path.join(ASSETS_DIR, "tags.txt")

def read_metadata(filepath, label):
    """Dosyayı bulana kadar kısa süre bekler ve okur."""
    print(f"🔍 {label} aranıyor: {filepath}")
    
    # Dosyanın yazılma süresi için 5 saniye tolerans
    for _ in range(5):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        print(f"✅ [BAŞARILI] {label} içeriği alındı.")
                        return content
            except Exception as e:
                print(f"⚠️ {label} okuma denemesi başarısız: {e}")
        time.sleep(2)
    
    print(f"❌ [BULUNAMADI] {label} dosyası yok veya boş. Varsayılan kullanılacak.")
    return None

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError("client_secrets.json bulunamadı!")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    print(f"🎬 [İŞLEM] 1 Saatlik render başladı...")
    clip = VideoFileClip(input_path)
    target_seconds = target_minutes * 60
    iterations = int(target_seconds / clip.duration) + 1
    
    final_clip = concatenate_videoclips([clip] * iterations)
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    clip.close()
    final_clip.close()

def upload_video(youtube, file_path):
    # Dosyaları oku
    title_val = read_metadata(TITLE_FILE, "BAŞLIK")
    desc_val = read_metadata(DESC_FILE, "AÇIKLAMA")
    tags_val = read_metadata(TAGS_FILE, "ETİKETLER")

    # Dinamik veya Varsayılan değerler
    now_str = datetime.datetime.now().strftime('%B %Y')
    title = title_val if title_val else f"Deep Focus Ambiance - {now_str}"
    description = desc_val if desc_val else f"Calm ambiance for study and relax. Created for @TheQuietCorner-yt."
    tags = [t.strip() for t in tags_val.split(',')] if tags_val else ["ambiance", "relax", "veo3"]

    print(f"📤 [YOUTUBE] Yükleniyor: {title}")

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '10'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    response = request.execute()
    video_id = response.get('id')
    print(f"🚀 [TAMAMLANDI] Video yüklendi: https://youtu.be/{video_id}")
    
    # Kapak Fotoğrafı
    if os.path.exists(THUMBNAIL_IMAGE):
        try:
            print(f"🖼️ [RESİM] Kapak fotoğrafı yükleniyor...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("🎨 [BAŞARI] Kapak fotoğrafı güncellendi.")
        except Exception as e:
            print(f"⚠️ [RESİM HATASI] {e}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"❌ [HATA] Giriş videosu (current_video.mp4) bulunamadı!")
    except Exception as e:
        print(f"💣 [SİSTEM DURDU] {str(e)}")

