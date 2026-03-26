import subprocess
import os

# Ayarlar
INPUT_VIDEO = "assets/current_video.mp4"
INPUT_AUDIO = "assets/background_ambient.mp3"  # Reponda bu isimde sabit bir ses dosyası olmalı
OUTPUT_VIDEO = "final_output_1hour.mp4"
TARGET_DURATION = 3600  # 1 Saat (Saniye cinsinden)

def get_duration(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def create_loop():
    print("--- Veo Video İşleme Başlıyor ---")
    
    if not os.path.exists(INPUT_VIDEO):
        print(f"Hata: {INPUT_VIDEO} bulunamadı!")
        return

    # 1. Videonun süresini al
    video_dur = get_duration(INPUT_VIDEO)
    loop_count = int(TARGET_DURATION // video_dur) + 1
    
    print(f"Orijinal Video Süresi: {video_dur}s")
    print(f"Döngü Sayısı: {loop_count}")

    # 2. FFmpeg ile video döngüsü, ses ekleme ve 1 saate kesme işlemi
    # Bu komut videoyu loop yapar, dışarıdan gelen sesi ekler ve tam 1 saatte keser.
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count),
        "-i", INPUT_VIDEO,
        "-i", INPUT_AUDIO,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-t", str(TARGET_DURATION),
        "-pix_fmt", "yuv420p",
        OUTPUT_VIDEO
    ]

    subprocess.run(cmd)
    print(f"--- İşlem Tamamlandı: {OUTPUT_VIDEO} oluşturuldu ---")

if __name__ == "__main__":
    create_loop()
