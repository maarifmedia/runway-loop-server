name: YouTube Otomasyonu - Veo 3 İşleyici

on:
  push:
    paths:
      - 'assets/current_video.mp4'
  workflow_dispatch:

jobs:
  build-and-upload:
    runs-on: ubuntu-latest
    
    # GitHub'ın istediği Node 24 standardına zorlar (Uyarıyı susturur)
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

    steps:
    - name: Depoyu Kontrol Et
      uses: actions/checkout@v4

    - name: Python Kurulumu
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Bağımlılıkları Kur
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Kimlik Bilgilerini Hazırla
      run: |
        echo '${{ secrets.CLIENT_SECRETS_JSON }}' > client_secrets.json
        echo '${{ secrets.TOKEN_JSON }}' > token.json

    - name: Videoyu İşle ve YouTube'a Yükle
      run: python server.py
