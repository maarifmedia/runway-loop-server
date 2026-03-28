import os
import datetime
import time
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

ASSETS_DIR = "assets"
INPUT_VIDEO = os.path.join(ASSETS_DIR, "current_video.mp4") 
OUTPUT_VIDEO = "final_loop_video.mp4"
THUMBNAIL_IMAGE = os.path.join(ASSETS_DIR, "s.png")

# SEO Dosyaları
TITLE_FILE = os.path.join(ASSETS_DIR, "title.txt")
DESC_FILE = os.path.join(ASSETS_DIR, "description.txt")
TAGS_FILE = os.path.join(ASSETS_DIR, "tags.txt")

def read_metadata(filepath, label):
    """Dosyayı okur ve içeriği doğrular."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    print(f"✅ [OKUNDU] {label}: {content[:50]}...")
                    return content
                else:
                    print(f"⚠️ [BOŞ] {label} dosyası boş bulundu.")
        except Exception as e:
            print(f"❌ [HATA] {label} okunurken teknik hata: {e}")
    else:
        print(f"📂 [YOK] {filepath} bulunamadı.")
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
    print(f"🎬 [İŞLEM] Render başlıyor: {input_path}")
    clip = VideoFileClip(input_path)
    target_seconds = target_minutes * 60
    iterations = int(target_seconds / clip.duration) + 1
    
    print(f"🔄 [DÖNGÜ] {iterations} tekrar ekleniyor...")
    final_clip = concatenate_videoclips([clip] * iterations)
    
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    clip.close()
    final_clip.close()
    print("✨ [TAMAM] Render bitti.")

def upload_video(youtube, file_path):
    # Dosyaları doğrula
    title_text = read_metadata(TITLE_FILE, "BAŞLIK")
    desc_text = read_metadata(DESC_FILE, "AÇIKLAMA")
    tags_text = read_metadata(TAGS_FILE, "ETİKETLER")

    # Yedekleme (Backup) Planı
    title = title_text if title_text else f"The Quiet Corner Ambiance - {datetime.datetime.now().strftime('%B %Y')}"
    description = desc_text if desc_text else "Sinematik Veo 3 ambiance deneyimi. @TheQuietCorner-yt"
    tags = [t.strip() for t in tags_text.split(',')] if tags_text else ["relax", "focus", "veo3"]

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

    print(f"📤 [YOUTUBE] Yükleniyor: {title}")
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    response = request.execute()
    video_id = response.get('id')
    print(f"🚀 [YÜKLENDİ] Video ID: {video_id}")
    
    # Küçük resim (s.png) kontrolü
    if os.path.exists(THUMBNAIL_IMAGE):
        try:
            print(f"🖼️ [THUMBNAIL] Yükleniyor: {THUMBNAIL_IMAGE}")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("🎨 [TAMAM] Kapak fotoğrafı güncellendi.")
        except Exception as e:
            print(f"⚠️ [RESİM HATASI] {e}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"❌ [KRİTİK HATA] Giriş videosu bulunamadı: {INPUT_VIDEO}")
    except Exception as e:
        print(f"💣 [SİSTEM DURDU] {str(e)}")

