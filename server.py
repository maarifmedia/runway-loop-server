import os
import time

def main():
    print("🚀 Sistem baslatildi...")
    # Buraya sadece temel islemleri ekliyoruz
    TEMP_VIDEO = "current_video.mp4"
    SHORTS_VIDEO = "shorts_video.mp4"
    
    for f in [TEMP_VIDEO, SHORTS_VIDEO]:
        if os.path.exists(f):
            print(f"🧹 Temizleniyor: {f}")
            os.remove(f)
    print("✅ Islem tamamlandi.")

if __name__ == "__main__":
    main()
