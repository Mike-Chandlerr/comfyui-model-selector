---
title: ComfyUI Model Downloader
emoji: ⚡
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 5000
pinned: true
license: mit
short_description: Web-based Model Manager for ComfyUI - 145 AI models in 13 categories
---

# ⚡ ComfyUI Model Downloader

Web-basierter Model Manager für ComfyUI. **145 AI-Modelle** in **13 Kategorien** direkt auf deinem Server downloaden und verwalten.

## Features

- 145 vorinstallierte Modelle (CLIP, ControlNet, FLUX, HiDream, Hunyuan, LoRA, WAN Video...)
- Dark Theme Web-Interface mit Kategorien-Filter und Suche
- Download-Manager mit Fortschrittsanzeige
- Neue Modelle jederzeit hinzufügen
- Bash-Script Export
- Resume Support (wget -c)

## Self-Host auf Unraid / Docker

```bash
docker build -t comfyui-model-downloader .

docker run -d \
  --name comfyui-model-downloader \
  --restart unless-stopped \
  -p 5050:5000 \
  -v /pfad/zu/ComfyUI:/comfyui-models \
  -v /pfad/zu/appdata:/app/data \
  -e MAX_CONCURRENT_DOWNLOADS=2 \
  comfyui-model-downloader
```

## Kategorien

| Kategorie | Anzahl |
|---|---|
| WAN Effects | 20 |
| Other | 28 |
| LoRA | 25 |
| WAN Video | 17 |
| CLIP | 13 |
| ControlNet | 11 |
| Qwen | 7 |
| IPAdapter | 6 |
| VAE | 6 |
| FLUX | 4 |
| Hunyuan | 4 |
| SDXL | 3 |
| HiDream | 2 |
