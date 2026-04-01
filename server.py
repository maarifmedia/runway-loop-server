import os
import pickle
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- AYARLAR VE YOLLAR ---
ASSETS_DIR = "assets/"
TEMP_VIDEO = f"{ASSETS_DIR}current_video.mp4"
SHORTS_VIDEO = f"{ASSETS_DIR}shorts_video.mp4"
THUMBNAIL = f"{ASSETS_DIR}s.png"
PLAYLIST_FILE = f"{ASSETS_DIR}playlist_id.txt"
TITLE_FILE = f"{ASSETS_DIR}title.txt"
DESC_FILE = f"{ASSETS_DIR}description.txt"
TAGS_FILE = f"{ASSETS_DIR}tags.txt"
TOKEN_FILE = "token.pickle"

def optimize_thumbnail(input_path):
    if os.path.exists(input_path):
        size_mb = os.path.getsize(input_path) / (1024 * 1024)
        if size_mb > 1.9:
            print(f"⚠️ Resim çok büyük ({size_mb:.2f}MB). Optimize ediliyor...")
            img = Image.open(input_path)
            img = img.convert("RGB")
            # En garantici ayar: JPEG formatı ve 75 kalite
            img.save(input_path, "JPEG", quality=75, optimize=True)
            print(f"✅ Yeni boyut: {os.path.getsize(input_path) / (1024 * 1024):.2f}MB")

def get_authenticated_service():
    """GitHub Secrets'tan gelen token ile YouTube bağlantısı kurar."""
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    return build('youtube', 'v3', credentials=credentials)

def read_asset(file_path, default):
    """Make.com'dan gelen SEO dosyalarını güvenli bir şekilde okur."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else default
    return default

def upload_video(youtube, file_path, title, description, tags, is_shorts=False, playlist_id=None):
    """Videoyu parçalı (resumable) yükler ve diğer işlemleri (resim, liste) yapar."""
    if not os.path.exists(file_path):
        print(f"❌ Dosya bulunamadı: {file_path}")
        return None
    try:
        print(f"📤 {title} yükleniyor...")
        # 1 saatlik videolar için 5MB parçalar halinde yükleme
        media = MediaFileUpload(file_path, mimetype='video/mp4', chunksize=5*1024*1024, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags.split(','),
                    "categoryId": "10"
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"⏳ Yükleme yüzdesi: %{int(status.progress() * 100)}")
        
        v_id = response.get("id")
        
        # 🖼️ KÜÇÜK RESİM (Thumbnail) ADIMI
        if not is_shorts and os.path.exists(THUMBNAIL):
            try:
                optimize_thumbnail(THUMBNAIL)
                youtube.thumbnails().set(videoId=v_id, media_body=MediaFileUpload(THUMBNAIL)).execute()
                print("🖼️ Küçük resim başarıyla eklendi.")
            except Exception as e:
                print(f"⚠️ Küçük resim hatası (Atlanıyor): {e}")

        # 📂 OYNATMA LİSTESİ ADIMI
        if playlist_id and not is_shorts:
            try:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": v_id}}}
                ).execute()
                print(f"📂 Oynatma listesine eklendi.")
            except Exception as e:
                print(f"⚠️ Liste hatası (Atlanıyor): {e}")
            
        return v_id
    except Exception as e:
        print(f"❌ Kritik Yükleme Hatası: {e}")
        return None

if __name__ == "__main__":
    print("🎬 @TheQuietCorner-yt Otomasyonu Devrede...")
    service = get_authenticated_service()
    
    # SEO ve Liste verilerini dosyalardan çek
    video_title = read_asset(TITLE_FILE, "Relaxing Ambiance (1 HOUR)")
    video_desc = read_asset(DESC_FILE, "Enjoy the cinematic loop.")
    video_tags = read_asset(TAGS_FILE, "relaxing,ambiance,1hour")
    p_id = read_asset(PLAYLIST_FILE, None)

    # 1. Ana Videoyu Yükle (1 Saatlik Loop)
    main_id = upload_video(service, TEMP_VIDEO, video_title, video_desc, video_tags, playlist_id=p_id)
    
    # 2. Shorts Videoyu Yükle ve Ana Videoya Link Ver
    if main_id and os.path.exists(SHORTS_VIDEO):
        m_url = f"https://www.youtube.com/watch?v={main_id}"
        # Shorts başlığına otomatik etiket ekle
        shorts_title = video_title[:50] + " #shorts"
        upload_video(service, SHORTS_VIDEO, shorts_title, f"Watch full version: {m_url}", "shorts,relax", is_shorts=True)
