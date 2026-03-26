import subprocess
import os
import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload

# --- AYARLAR ---
INPUT_VIDEO = "assets/current_video.mp4"
AUDIO_CHOICE_FILE = "assets/audio_choice.txt"
OUTPUT_VIDEO = "final_output_1hour.mp4"
TARGET_DURATION = 3600  # 1 Saat (Saniye)

# GitHub Actions Env (Make.com'dan Payload ile gelen veriler)
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Cozy Ambience - Relaxing Night")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Enjoy this relaxing atmosphere.")
VIDEO_TAGS = os.environ.get("VIDEO_TAGS", "ambience,relax,sleep")

# YouTube Oynatma Listesi ID'lerin
PLAYLIST_NATURE = "PLBSKEl0NRvK--0dqTjSY61Jx6I3gX74iH"  # Sadece Doğa Sesleri
PLAYLIST_MUSIC = "PLBSKEl0NRvK_EW7SZvIqgeEO3nR3mA5_9"   # Müzikli (Melodik)

def get_duration(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def create_loop():
    # Varsayılan ses
    selected_audio = "assets/background_ambient.mp3"
    is_melodic = False
    
    # Gemini'nin ses seçimini oku
    if os.path.exists(AUDIO_CHOICE_FILE):
        with open(AUDIO_CHOICE_FILE, 'r') as f:
            choice = f.read().strip()
            # Eğer seçim adında 'melodic' veya 'music' geçiyorsa müzikli listeye gidecek
            if "melodic" in choice or "music" in choice:
                is_melodic = True
            
            potential_file = f"assets/{choice}.mp3"
            if os.path.exists(potential_file):
                selected_audio = potential_file

    print(f"--- Video Hazırlanıyor ---")
    print(f"Ses Dosyası: {selected_audio}")
    print(f"Müzikli mi?: {is_melodic}")

    if not os.path.exists(INPUT_VIDEO):
        print("Hata: Kaynak video (current_video.mp4) bulunamadı!")
        return None

    video_dur = get_duration(INPUT_VIDEO)
    loop_count = int(TARGET_DURATION // video_dur) + 1

    # FFmpeg: Döngüye sok, sesi ekle, 1 saatte kes ve paketle
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count),
        "-i", INPUT_VIDEO,
        "-i", selected_audio,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-t", str(TARGET_DURATION),
        "-pix_fmt", "yuv420p",
        OUTPUT_VIDEO
    ]
    subprocess.run(cmd)
    return is_melodic

def upload_to_youtube(is_melodic):
    print("--- YouTube Yükleme İşlemi Başlıyor ---")
    
    # Secrets'tan gelen yetki bilgileri
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    creds = google.oauth2.credentials.Credentials(
        None, 
        refresh_token=refresh_token, 
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, 
        client_secret=client_secret
    )
    
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    # 1. Videoyu Yükle
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": VIDEO_TITLE,
                "description": VIDEO_DESC,
                "tags": VIDEO_TAGS.split(","),
                "categoryId": "10"  # Müzik kategorisi
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(OUTPUT_VIDEO, chunksize=-1, resumable=True)
    )
    response = request.execute()
    video_id = response["id"]
    print(f"Video Başarıyla Yüklendi! ID: {video_id}")

    # 2. Oynatma Listesine Ekle
    target_playlist = PLAYLIST_MUSIC if is_melodic else PLAYLIST_NATURE
    
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": target_playlist,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    ).execute()
    print(f"Video şu listeye eklendi: {target_playlist}")

if __name__ == "__main__":
    melodic_flag = create_loop()
    if melodic_flag is not None:
        upload_to_youtube(melodic_flag)
