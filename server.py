import os
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# MoviePy v2.x ve v1.x uyumluluğu için kontrol
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
THUMBNAIL_IMAGE = "assets/s.png" # Make.com tarafından gönderilen kapak fotoğrafı

def get_authenticated_service():
    """YouTube API kimlik doğrulama sürecini yönetir."""
    creds = None
    # Eğer token.json varsa (GitHub Secrets'tan oluşturulmuşsa) kullan
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Kimlik bilgisi yoksa veya geçersizse yenile veya giriş yaptır
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError("client_secrets.json bulunamadı!")
            
            # Yerel testlerde tarayıcı açar, GitHub'da bu aşamaya gelmemesi için TOKEN_JSON yüklü olmalıdır
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
        
        # Gelecekteki kullanımlar için token'ı kaydet
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def create_one_hour_loop(input_path, output_path, target_minutes=60):
    """Veo 3 videosunu belirlenen süreye kadar döngüye sokar."""
    print(f"--- Video İşleme Başladı: {input_path} ---")
    clip = VideoFileClip(input_path)
    
    target_seconds = target_minutes * 60
    # Kaç tekrar gerektiğini hesapla
    iterations = int(target_seconds / clip.duration) + 1
    
    print(f"Video {iterations} kez uç uca ekleniyor...")
    final_clip = concatenate_videoclips([clip] * iterations)
    
    # Videoyu tam süreye ayarla
    if HAS_V2:
        final_clip = final_clip.with_duration(target_seconds)
    else:
        final_clip = final_clip.subclip(0, target_seconds)
    
    print("Video dosyası oluşturuluyor (Render)...")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    
    clip.close()
    final_clip.close()
    print("--- Video Render Tamamlandı! ---")

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Yüklenen videonun kapak fotoğrafını (s.png) ayarlar."""
    if os.path.exists(thumbnail_path):
        print(f"Kapak fotoğrafı yükleniyor: {thumbnail_path}")
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("Kapak fotoğrafı başarıyla güncellendi!")
        except Exception as e:
            print(f"Kapak fotoğrafı yüklenirken hata: {e}")
    else:
        print("Kapak fotoğrafı (s.png) bulunamadı, varsayılan bırakılıyor.")

def upload_video(youtube, file_path):
    """Videoyu YouTube'a yükler ve kapak fotoğrafını ekler."""
    now = datetime.datetime.now()
    body = {
        'snippet': {
            'title': f"Deep Focus Ambiance - {now.strftime('%B %Y')} | Aesthetic Loop",
            'description': 'Welcome to your quiet corner. Relax and focus with this Veo 3 generated ambiance. #ambiance #cozy #peaceful #thequietcorner',
            'tags': ['ambiance', 'cozy', 'study', 'relax', 'veo3', 'nature'],
            'categoryId': '10' # Müzik/Eğlence
        },
        'status': {
            'privacyStatus': 'public', 
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    
    print("YouTube'a yükleme işlemi başlatıldı...")
    response = request.execute()
    video_id = response.get('id')
    print(f"Başarılı! Video yüklendi. Video ID: {video_id}")
    
    # Küçük resmi yükle
    upload_thumbnail(youtube, video_id, THUMBNAIL_IMAGE)

if __name__ == "__main__":
    try:
        # 1. API Bağlantısını Kur
        youtube_service = get_authenticated_service()
        
        # 2. Döngü Videosunu Oluştur
        if os.path.exists(INPUT_VIDEO):
            create_one_hour_loop(INPUT_VIDEO, OUTPUT_VIDEO)
            # 3. Yükle ve Kapak Fotoğrafını Ayarla
            upload_video(youtube_service, OUTPUT_VIDEO)
        else:
            print(f"HATA: {INPUT_VIDEO} dosyası bulunamadı!")
            
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {str(e)}")
