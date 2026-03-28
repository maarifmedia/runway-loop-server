import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v2.x uyumluluk kontrolü
try:
    from moviepy import VideoFileClip, concatenate_videoclips
    HAS_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_V2 = False

# --- GÜNCELLENMİŞ YETKİLER (SCOPES) ---
# Playlist işlemleri için 'https://www.googleapis.com/auth/youtube' gereklidir.
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

INPUT_VIDEO = "assets/current_video.mp4" 
OUTPUT_VIDEO = "final_loop_video.mp4"
THUMBNAIL_IMAGE = "assets/s.png"

# Gemini/Make SEO Dosyaları
TITLE_FILE = "assets/title.txt"
DESC_FILE = "assets/description.txt"
TAGS_FILE = "assets/tags.txt"
AUDIO_CHOICE_FILE = "assets/audio_choice.txt"

# --- OYNATMA LİSTELERİ ---
PLAYLIST_NO_MUSIC = "PLBSKEl0NRvK--0dqTjSY61Jx6I3gX74iH"
PLAYLIST_WITH_MUSIC = "PLBSKEl0NRvK_EW7SZvIqgeEO3nR3mA5_9"

def read_asset_file(filepath, default_value=""):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            return default_value
    return default_value

def get_authenticated_service():
    """Yeni yetki kapsamı ile YouTube servisini bağlar."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError("client_secrets.json bulunamadı!")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    print(f"--- Video İşleniyor: {input_path} ---")
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
    title = read_asset_file(TITLE_FILE, f"Deep Focus Ambiance - {datetime.datetime.now().strftime('%B %Y')}")
    description = read_asset_file(DESC_FILE, "Relax and focus with @TheQuietCorner-yt.")
    tags_raw = read_asset_file(TAGS_FILE, "ambiance,relax,veo3")
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
    
    audio_choice = read_asset_file(AUDIO_CHOICE_FILE, "").lower()
    is_music = any(word in audio_choice for word in ["music", "müzik", "soft", "melodic"])
    playlist_id = PLAYLIST_WITH_MUSIC if is_music else PLAYLIST_NO_MUSIC
    
    print(f"Başlık: {title} | Kategori: {'Müzikli' if is_music else 'Ambiance'}")

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
    print(f"Başarılı! Video yüklendi: https://youtu.be/{video_id}")
    
    # Kapak Fotoğrafı
    if os.path.exists(THUMBNAIL_IMAGE):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
            print("Thumbnail yüklendi.")
        except Exception as e:
            print(f"Thumbnail Hatası: {e}")

    # Oynatma Listesi
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        ).execute()
        print(f"Oynatma listesine eklendi: {playlist_id}")
    except Exception as e:
        print(f"Oynatma Listesi Hatası: {e}")

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"Hata: {INPUT_VIDEO} dosyası bulunamadı!")
    except Exception as e:
        print(f"Sistem Hatası: {str(e)}")
