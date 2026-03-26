import subprocess
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

# --- AYARLAR ---
INPUT_VIDEO = "assets/current_video.mp4"
AUDIO_CHOICE_FILE = "assets/audio_choice.txt"
OUTPUT_VIDEO = "final_output_1hour.mp4"
TARGET_DURATION = 3600 # 1 Saat

# GitHub Actions Env'den gelen Metadata (Make.com'dan geliyor)
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Default Cozy Ambience")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing sounds for sleep.")
VIDEO_TAGS = os.environ.get("VIDEO_TAGS", "ambience,sleep,relax")

# YouTube Playlist ID'lerin (Burayı kendi ID'lerinle güncelle)
PLAYLIST_NATURE = "PL...GirisYap" # Sadece doğa sesli liste ID'si
PLAYLIST_MUSIC = "PL...GirisYap" # Müzikli liste ID'si

def get_duration(file_path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def create_loop():
    selected_audio = "assets/background_ambient.mp3"
    is_melodic = False
    
    if os.path.exists(AUDIO_CHOICE_FILE):
        with open(AUDIO_CHOICE_FILE, 'r') as f:
            choice = f.read().strip()
            # Eğer seçimde 'music' veya 'melodic' ibaresi geçerse
            if "music" in choice or "melodic" in choice:
                is_melodic = True
            
            potential_file = f"assets/{choice}.mp3"
            if os.path.exists(potential_file):
                selected_audio = potential_file

    print(f"--- Video Hazırlanıyor: {selected_audio} ---")
    video_dur = get_duration(INPUT_VIDEO)
    loop_count = int(TARGET_DURATION // video_dur) + 1

    # FFmpeg Loop ve Ses Birleştirme
    cmd = [
        "ffmpeg", "-y", "-stream_loop", str(loop_count), "-i", INPUT_VIDEO,
        "-i", selected_audio, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-t", str(TARGET_DURATION),
        "-pix_fmt", "yuv420p", OUTPUT_VIDEO
    ]
    subprocess.run(cmd)
    return is_melodic

def upload_to_youtube(is_melodic):
    print("--- YouTube'a Yükleme Başlıyor ---")
    # YouTube API Yetkilendirme (Secrets'tan gelen bilgilerle)
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    credentials = google.oauth2.credentials.Credentials(
        None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret
    )
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    # Video Metadata Hazırlığı
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": VIDEO_TITLE,
                "description": VIDEO_DESC,
                "tags": VIDEO_TAGS.split(","),
                "categoryId": "10" # Music kategorisi
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(OUTPUT_VIDEO, chunksize=-1, resumable=True)
    )
    response = request.execute()
    video_id = response["id"]
    print(f"Video Yüklendi! ID: {video_id}")

    # Oynatma Listesine Ekleme
    target_playlist = PLAYLIST_MUSIC if is_melodic else PLAYLIST_NATURE
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": target_playlist,
                "resourceId": {"kind": "youtube#video", "videoId": video_id}
            }
        }
    ).execute()
    print(f"Oynatma Listesine Eklendi: {target_playlist}")

if __name__ == "__main__":
    melodic_status = create_loop()
    upload_to_youtube(melodic_status)
