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

# --- DİREKTİFLER ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Klasör Yapısı
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

INPUT_VIDEO = os.path.join(ASSETS_DIR, "current_video.mp4") 
OUTPUT_VIDEO = os.path.join(BASE_DIR, "final_loop_video.mp4")
THUMBNAIL_IMAGE = os.path.join(ASSETS_DIR, "s.png")

# Metadata Dosyaları
META_FILES = {
    "TITLE": os.path.join(ASSETS_DIR, "title.txt"),
    "DESC": os.path.join(ASSETS_DIR, "description.txt"),
    "TAGS": os.path.join(ASSETS_DIR, "tags.txt")
}

def check_and_read_file(filepath, label):
    """Dosyayı kontrol eder, son değişim tarihini loglar ve okur."""
    if os.path.exists(filepath):
        # Dosyanın son değiştirilme zamanını al
        mtime = os.path.getmtime(filepath)
        dt_mtime = datetime.datetime.fromtimestamp(mtime)
        print(f"📂 [DOSYA ANALİZİ] {label} bulundu. Son güncelleme: {dt_mtime}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    print(f"📝 [İÇERİK] {label}: {content[:50]}...")
                    return content
                else:
                    print(f"⚠️ [UYARI] {label} dosyası boş!")
        except Exception as e:
            print(f"❌ [HATA] {label} okunurken hata: {e}")
    else:
        print(f"❓ [YOK] {label} dosyası ({filepath}) bulunamadı!")
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
    
    final_clip = concatenate_videoclips([clip] * iterations)
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    clip.close()
    final_clip.close()

def upload_video(youtube, file_path):
    # Verileri dosyadan çek
    title_raw = check_and_read_file(META_FILES["TITLE"], "BAŞLIK")
    desc_raw = check_and_read_file(META_FILES["DESC"], "AÇIKLAMA")
    tags_raw = check_and_read_file(META_FILES["TAGS"], "ETİKETLER")

    # Yedek Plan
    now = datetime.datetime.now().strftime('%B %Y')
    title = title_raw if title_raw else f"The Quiet Corner Ambiance - {now}"
    description = desc_raw if desc_raw else "Calm vibes for study and relaxation. @TheQuietCorner-yt"
    tags = [t.strip() for t in tags_raw.split(',')] if tags_raw else ["relax", "veo3", "ambiance"]

    print(f"📤 [YÜKLEME] YouTube'a gönderiliyor: {title}")

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
    print(f"✅ [BAŞARI] Video ID: {video_id}")
    
    # Küçük resim yükleme
    if os.path.exists(THUMBNAIL_IMAGE):
        print(f"🖼️ [THUMBNAIL] Yükleniyor...")
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("✨ [TAMAM] Küçük resim güncellendi.")
        except Exception as e:
            print(f"❗ [HATA] Resim yüklenemedi: {e}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"❌ [HATA] {INPUT_VIDEO} dosyası mevcut değil!")
    except Exception as e:
        print(f"💣 [SİSTEM HATASI] {str(e)}")

