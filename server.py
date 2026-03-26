import subprocess
import os

# Ayarlar
INPUT_VIDEO = "assets/current_video.mp4"
AUDIO_CHOICE_FILE = "assets/audio_choice.txt" 
OUTPUT_VIDEO = "final_output_1hour.mp4"
TARGET_DURATION = 3600 # 1 Saat

def get_duration(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def create_loop():
    # Varsayılan ses
    selected_audio = "assets/background_ambient.mp3"
    
    # Gemini'den gelen seçimi kontrol et
    if os.path.exists(AUDIO_CHOICE_FILE):
        with open(AUDIO_CHOICE_FILE, 'r') as f:
            choice = f.read().strip()
            # Eğer klasörde bu isimde bir ses varsa onu seç
            potential_file = f"assets/{choice}.mp3"
            if os.path.exists(potential_file):
                selected_audio = potential_file

    print(f"--- İşlem Başlıyor ---")
    print(f"Video: {INPUT_VIDEO}")
    print(f"Seçilen Ses: {selected_audio}")

    if not os.path.exists(INPUT_VIDEO):
        print("Hata: Video dosyası bulunamadı!")
        return

    video_dur = get_duration(INPUT_VIDEO)
    loop_count = int(TARGET_DURATION // video_dur) + 1

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
    print("--- 1 Saatlik Video Hazır! ---")

if __name__ == "__main__":
    create_loop()
