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

# --- AYARLAR ---
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

INPUT_VIDEO = "assets/current_video.mp4" 
OUTPUT_VIDEO = "final_loop_video.mp4"
THUMBNAIL_IMAGE = "assets/s.png"

# Gemini (Make.com) tarafından güncellenmesi gereken dosyalar
TITLE_FILE = "assets/title.txt"
DESC_FILE = "assets/description.txt"
TAGS_FILE = "assets/tags.txt"

def read_asset_file(filepath, label, default_value=""):
    """Dosyayı okur ve durumu raporlar."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    print(f"[DOSYA BULUNDU] {label}: {content[:30]}...")
                    return content
                else:
                    print(f"[UYARI] {label} dosyası boş! Varsayılan kullanılıyor.")
        except Exception as e:
            print(f"[HATA] {label} okunurken sorun oluştu: {e}")
    else:
        print(f"[DOSYA YOK] {filepath} bulunamadı! Varsayılan değer atanıyor.")
    return default_value

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
    print(f"--- Video İşleme Başladı: {input_path} ---")
    clip = VideoFileClip(input_path)
    target_seconds = target_minutes * 60
    iterations = int(target_seconds / clip.duration) + 1
    
    print(f"Video {iterations} kez uç uca ekleniyor...")
    final_clip = concatenate_videoclips([clip] * iterations)
    
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    clip.close()
    final_clip.close()
    print("--- Render Tamamlandı ---")

def upload_video(youtube, file_path):
    # Gemini verilerini oku
    title = read_asset_file(TITLE_FILE, "BAŞLIK", f"Deep Focus Ambiance - {datetime.datetime.now().strftime('%B %Y')}")
    description = read_asset_file(DESC_FILE, "AÇIKLAMA", "Relaxing ambiance created with Veo 3. Follow @TheQuietCorner-yt.")
    tags_raw = read_asset_file(TAGS_FILE, "ETİKETLER", "ambiance,relax,veo3")
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

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
    
    print(f"YouTube'a yükleniyor: {title}")
    response = request.execute()
    video_id = response.get('id')
    print(f"Başarılı! ID: {video_id}")
    
    # Kapak fotoğrafını kontrol et ve yükle
    if os.path.exists(THUMBNAIL_IMAGE):
        print(f"[THUMBNAIL] {THUMBNAIL_IMAGE} bulundu, yükleniyor...")
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("[THUMBNAIL] Başarıyla yüklendi.")
        except Exception as e:
            print(f"[THUMBNAIL HATA] {e}")
    else:
        print("[THUMBNAIL] assets/s.png bulunamadı! YouTube varsayılan resmi kullanacak.")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"HATA: {INPUT_VIDEO} dosyası mevcut değil!")
    except Exception as e:
        print(f"SİSTEM HATASI: {str(e)}")
