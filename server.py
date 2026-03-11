import os
import subprocess
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# --- 1. AYARLAR VE DEĞİŞKENLER ---
VIDEO_TITLE = os.environ.get("VIDEO_TITLE", "Peaceful Relaxation - The Quiet Corner")
VIDEO_DESC = os.environ.get("VIDEO_DESC", "Relaxing ambient sounds. @TheQuietCorner-yt")
VIDEO_TAGS = (os.environ.get("VIDEO_TAGS") or "sleep,relaxing,asmr").split(",")
AUDIO_FILE = os.environ.get("AUDIO_FILENAME", "somine_yagmur.mp3.mp3")
SHORTS_DATA = os.environ.get("SHORTS_PLAN", "")

IMAGE_FILE = "arkaplan.jpg"
OUTPUT_VIDEO = "hazir_video.mp4"

# --- 2. AKILLI GÖRSEL SEÇİCİ VE İNDİRME ---
def download_image(filename):
    # Eski dosyayı sil (Önbellek temizliği)
    if os.path.exists(filename):
        os.remove(filename)

    title_lower = VIDEO_TITLE.lower()
    
    # Başlığa göre atmosfer seçimi (Dağ görselinden kaçınmak için spesifik kelimeler)
    if "cabin" in title_lower or "house" in title_lower or "indoor" in title_lower:
        search_terms = "cozy,fireplace,indoor,cabin-interior"
    elif "lake" in title_lower or "water" in title_lower:
        search_terms = "lakeside,lake-night,campfire-lake"
    elif "rain" in title_lower or "storm" in title_lower:
        search_terms = "rainy-window,dark-room,ambient-rain"
    elif "forest" in title_lower:
        search_terms = "misty-forest,dark-woods,night-forest"
    else:
        # Hiçbiri tutmazsa genel huzurlu gece manzarası
        search_terms = "night-sky,starry-night,calm-nature"

    # Unsplash'ten her seferinde benzersiz görsel çekmek için sig (rastgele sayı) ekliyoruz
    # Make'den gelen linki artık hiç kullanmıyoruz, Python kendisi karar veriyor.
    final_url = f"https://source.unsplash.com/featured/1920x1080/?{search_terms}&sig={os.urandom(4).hex()}"
    
    print(f"Görsel indiriliyor (Seçilen Atmosfer: {search_terms}): {final_url}")
    
    try:
        response = requests.get(final_url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Görsel başarıyla indirildi ve sisteme kaydedildi.")
    except Exception as e:
        print(f"Görsel indirme hatası: {e}. Standart manzara indiriliyor...")
        fallback = requests.get("https://images.unsplash.com/photo-1542332213-31f87348057f")
        with open(filename, 'wb') as f:
            f.write(fallback.content)

# --- 3. 1 SAATLİK RENDER İŞLEMİ (3600 SANİYE) ---
def render_video():
    print(f"Render işlemi {AUDIO_FILE} sesi ile başlatılıyor (Hedef: 1 Saat)...")
    
    aktif_ses = AUDIO_FILE
    if not os.path.exists(aktif_ses):
        print(f"UYARI: {aktif_ses} bulunamadı! Varsayılan sese dönülüyor.")
        aktif_ses = "somine_yagmur.mp3.mp3" 
    
    # 3600 saniye = 1 Saat
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "1", "-i", IMAGE_FILE,
        "-stream_loop", "-1", "-i", aktif_ses,
        "-t", "3600",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]
    
    subprocess.run(command, check=True)
    print("Video başarıyla oluşturuldu. YouTube yükleme adımına geçiliyor.")

# --- 4. YOUTUBE'A YÜKLEME ---
def upload_to_youtube():
    if not os.path.exists('token.pickle'):
        print("KRİTİK HATA: token.pickle dosyası bulunamadı! Yükleme iptal edildi.")
        return

    with open('token.pickle', 'rb') as token:
        credentials = pickle.load(token)
            
    youtube = build('youtube', 'v3', credentials=credentials)
    
    body = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': f"{VIDEO_DESC}\n\n--- CONTENT PLAN ---\n{SHORTS_DATA}",
            'tags': VIDEO_TAGS,
            'categoryId': '10' # Music/Ambient
        },
        'status': {
            'privacyStatus': 'public'
        }
    }
    
    media = MediaFileUpload(OUTPUT_VIDEO, chunksize=1024*1024*5, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    print("YouTube API bağlantısı kuruldu. Dosya gönderiliyor...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yükleme İlerlemesi: %{int(status.progress() * 100)}")
            
    print(f"TEBRİKLER! @TheQuietCorner-yt videosu yayında. ID: {response['id']}")

# --- 5. ANA ÇALIŞTIRMA BLOKU ---
if __name__ == "__main__":
    try:
        # download_image artık parametre almıyor, içindeki mantığı kullanıyor
        download_image(IMAGE_FILE)
        render_video()
        upload_to_youtube()
        print("SÜREÇ BAŞARIYLA TAMAMLANDI.")
    except Exception as e:
        print(f"SİSTEM HATASI: {e}")
