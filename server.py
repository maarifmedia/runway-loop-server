import os
import datetime
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

try:
    from moviepy import VideoFileClip, concatenate_videoclips
    HAS_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_V2 = False

CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

INPUT_VIDEO = "assets/current_video.mp4" 
OUTPUT_VIDEO = "final_loop_video.mp4"
THUMBNAIL_IMAGE = "assets/s.png"

TITLE_FILE = "assets/title.txt"
DESC_FILE = "assets/description.txt"
TAGS_FILE = "assets/tags.txt"
AUDIO_CHOICE_FILE = "assets/audio_choice.txt"

PLAYLIST_NO_MUSIC = "PLBSKEl0NRvK--0dqTjSY61Jx6I3gX74iH"
PLAYLIST_WITH_MUSIC = "PLBSKEl0NRvK_EW7SZvIqgeEO3nR3mA5_9"

def read_asset_file(filepath, default_value=""):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
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
                raise FileNotFoundError("HATA: client_secrets.json bulunamadı!")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    print(f"--- Render Başlıyor: {input_path} ---")
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
    title = read_asset_file(TITLE_FILE, f"Deep Focus - {datetime.datetime.now().strftime('%B %Y')}")
    description = read_asset_file(DESC_FILE, "Relax with @TheQuietCorner-yt")
    tags_raw = read_asset_file(TAGS_FILE, "ambiance,relax,veo3")
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
    audio_choice = read_asset_file(AUDIO_CHOICE_FILE, "").lower()
    is_music = any(word in audio_choice for word in ["music", "müzik", "soft", "melodic"])
    playlist_id = PLAYLIST_WITH_MUSIC if is_music else PLAYLIST_NO_MUSIC
    body = {
        'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': '10'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    response = request.execute()
    video_id = response.get('id')
    print(f"BAŞARILI! Video yüklendi: {video_id}")
    if os.path.exists(THUMBNAIL_IMAGE):
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(THUMBNAIL_IMAGE)).execute()
    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    ).execute()

if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            upload_video(service, OUTPUT_VIDEO)
        else:
            print(f"HATA: {INPUT_VIDEO} bulunamadı!")
            sys.exit(1)
    except Exception as e:
        print(f"SİSTEM HATASI: {str(e)}")
        sys.exit(1)
