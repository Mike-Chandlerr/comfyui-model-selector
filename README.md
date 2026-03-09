---
title: ComfyUI Model Downloader
emoji: ⚡
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 5000
pinned: true
license: mit
short_description: 145 AI Models Manager for ComfyUI
---

# ⚡ ComfyUI Model Downloader v1.1

Web-basierter Model Manager für ComfyUI — **145 AI-Modelle** in **13 Kategorien**, kuratiert und sofort einsatzbereit.

---

## 🎯 Was ist das?

Eine Web-App zum Durchsuchen, Auswählen und Downloaden von AI-Modellen für [ComfyUI](https://github.com/comfyanonymous/ComfyUI). Statt mühsam einzelne URLs zusammenzusuchen, hast du hier alle wichtigen Modelle an einem Ort — sortiert nach Kategorie, mit Größenangaben und korrekten Zielpfaden.

### Hier auf HuggingFace kannst du:
- ✅ Alle 145 Modelle durchsuchen und filtern
- ✅ Modelle auswählen und ein **Bash-Script generieren** (Copy & Paste)
- ✅ Das Script auf deinem eigenen Server ausführen
- ✅ Den Code klonen und selbst als Docker hosten

### Auf deinem eigenen Server kannst du zusätzlich:
- ✅ Downloads **direkt auf dem Server starten** mit Fortschrittsanzeige
- ✅ Parallele Downloads (konfigurierbar)
- ✅ Eigene Modelle dauerhaft hinzufügen
- ✅ Sehen welche Modelle bereits installiert sind
- ✅ Abgebrochene Downloads fortsetzen (Resume Support)

---

## 📋 Modell-Kategorien (145 Modelle)

| Kategorie | Anzahl | Beispiele |
|---|---|---|
| Other | 28 | SAM, IC-Light, SUPIR, MMAudio, InfiniteYou |
| LoRA | 25 | ACE, FastWan, Lightx2v, CausVid, HYPER FLUX |
| WAN Effects | 20 | Remade-AI: Assassin, Cakeify, Inflate, Zen... |
| WAN Video | 17 | Wan 2.1/2.2, FramePack, Multitalk, Phantom |
| CLIP | 13 | t5xxl, HiDream, umt5, LLaVA, SigLIP |
| ControlNet | 11 | FLUX Inpainting, InstantX Union, QR Monster |
| Qwen | 7 | Qwen Image Edit, Lightning, qwreal |
| IPAdapter | 6 | SDXL, SD15, PuLID, InstantID |
| VAE | 6 | FLUX ae, HiDream, SDXL, WAN 2.1 |
| FLUX | 4 | Dev fp8, Schnell Q4, Kontext, Fill |
| Hunyuan | 4 | FramePack, Video 720p, 3D-dit-v2 |
| SDXL | 3 | RealVisXL, Realism Engine, Sketch |
| HiDream | 2 | i1 fast fp8, e1 full Q4 |

---

## 🚀 So verwendest du es

### Option 1 — Bash-Script (einfachste Methode)

1. Öffne die App hier auf HuggingFace
2. Wähle die Modelle aus die du brauchst
3. Klicke **"📋 Bash Script kopieren"**
4. Füge das Script auf deinem Server ein:

```bash
# Auf deinem Server (Unraid, Linux, WSL):
bash download_models.sh

# Oder mit anderem ComfyUI-Pfad:
COMFY_ROOT="/dein/pfad/zu/ComfyUI" bash download_models.sh
```

Das Script erstellt automatisch alle Unterordner und lädt mit wget -c (Resume Support).

---

### Option 2 — Self-Host als Docker (volle Power)

Klone dieses Repository und starte es auf deinem eigenen Server. Dann hast du alle Features inkl. direkter Server-Downloads.

```bash
# 1. Repo klonen
git clone https://huggingface.co/spaces/MikeChandler/comfyui-model-downloader-v1.1
cd comfyui-model-downloader-v1.1

# 2. Docker Image bauen
docker build -t comfyui-model-downloader .

# 3. Container starten
docker run -d \
  --name comfyui-model-downloader \
  --restart unless-stopped \
  -p 5050:5000 \
  -v /pfad/zu/deinem/ComfyUI:/comfyui-models \
  -v /pfad/zu/appdata:/app/data \
  -e MAX_CONCURRENT_DOWNLOADS=2 \
  -e TZ=Europe/Vienna \
  comfyui-model-downloader
```

Dann öffne http://dein-server:5050

---

### Option 3 — Unraid Server

```bash
cd /mnt/user/appdata/comfyui-model-downloader
docker build -t comfyui-model-downloader .

docker run -d \
  --name comfyui-model-downloader \
  --restart unless-stopped \
  -p 5050:5000 \
  -v /mnt/user/dein_share/ComfyUI:/comfyui-models \
  -v /mnt/user/appdata/comfyui-model-downloader:/app/data \
  -e MAX_CONCURRENT_DOWNLOADS=2 \
  -e TZ=Europe/Vienna \
  comfyui-model-downloader
```

Erreichbar unter http://DEINE-UNRAID-IP:5050

---

## ⚙️ Konfiguration

| Variable | Default | Beschreibung |
|---|---|---|
| COMFY_ROOT | /comfyui-models | ComfyUI-Pfad im Container (Volume Mount) |
| MAX_CONCURRENT_DOWNLOADS | 2 | Max parallele Downloads (1-5) |
| PORT | 5000 | Interner App-Port |
| TZ | Europe/Vienna | Zeitzone |

---

## 📡 API Endpunkte

Die App bietet eine REST-API für Automatisierung (z.B. via n8n):

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| GET | /api/models | Alle Modelle + Disk Info |
| POST | /api/download | Downloads starten |
| GET | /api/download/status | Download-Fortschritt |
| POST | /api/download/cancel | Download abbrechen |
| POST | /api/models/add | Eigenes Modell hinzufügen |
| POST | /api/models/delete | User-Modell löschen |
| GET | /api/settings | Einstellungen |

---

## 🔄 Eigene Modelle hinzufügen

Im Self-Host Modus kannst du jederzeit neue Modelle ergänzen:

**Web-Interface:** Klicke auf "+ Neues Modell" und gib Name, URL, Kategorie und Zielordner ein.

**API:**
```bash
curl -X POST http://localhost:5050/api/models/add \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mein Custom LoRA",
    "category": "LoRA",
    "size": "500MB",
    "url": "https://huggingface.co/user/model/resolve/main/model.safetensors",
    "dest": "models/loras/",
    "filename": "mein_lora.safetensors"
  }'
```

Eigene Modelle werden persistent gespeichert und überleben Container-Neustarts.

---

## 🛠️ Troubleshooting

**Downloads brechen ab?** Einfach nochmal starten — wget -c setzt dort fort wo es aufgehört hat.

**Port 5050 belegt?** Ändere den Port: -p 5051:5000

**Container-Logs prüfen:**
```bash
docker logs comfyui-model-downloader
```

---

## 📄 Lizenz

MIT — Frei verwendbar, auch kommerziell.

---

*Erstellt von [MikeChandler](https://huggingface.co/MikeChandler) — für die ComfyUI Community*
