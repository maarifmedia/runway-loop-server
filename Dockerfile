FROM python:3.10-slim

# Gerekli sistem araçlarını yükle (FFmpeg video için şart)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kütüphaneleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm dosyaları içeri kopyala
COPY . .

# Python kodunu çalıştır
CMD ["python", "server.py"]
