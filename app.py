#!/usr/bin/env python3
"""
ComfyUI Model Downloader - Unraid Docker App
Flask backend with download management, progress tracking, and model CRUD.
"""

import json
import os
import subprocess
import threading
import time
import uuid
import re
import shutil
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

# --- Configuration ---
COMFY_ROOT = os.environ.get("COMFY_ROOT", "/comfyui-models")
MODELS_JSON = os.environ.get("MODELS_JSON", "/app/models.json")
USER_MODELS_JSON = os.environ.get("USER_MODELS_JSON", "/app/data/user_models.json")
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Model Store ---
def load_models():
    """Load base models + user-added models."""
    models = []
    if os.path.exists(MODELS_JSON):
        with open(MODELS_JSON) as f:
            models = json.load(f)
    # Merge user models
    if os.path.exists(USER_MODELS_JSON):
        with open(USER_MODELS_JSON) as f:
            user_models = json.load(f)
            models.extend(user_models)
    return models

def save_user_models(user_models):
    with open(USER_MODELS_JSON, "w") as f:
        json.dump(user_models, f, indent=2)

def load_user_models():
    if os.path.exists(USER_MODELS_JSON):
        with open(USER_MODELS_JSON) as f:
            return json.load(f)
    return []

# --- Download Manager ---
class DownloadManager:
    def __init__(self):
        self.active_downloads = {}  # id -> {process, model, progress, status, speed, eta}
        self.history = []           # completed/failed downloads
        self.queue = []             # queued model ids
        self.max_concurrent = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "2"))
        self.lock = threading.Lock()
        self._queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._queue_thread.start()

    def _process_queue(self):
        while True:
            time.sleep(1)
            with self.lock:
                active_count = sum(1 for d in self.active_downloads.values() if d["status"] == "downloading")
                while self.queue and active_count < self.max_concurrent:
                    model_id = self.queue.pop(0)
                    models = load_models()
                    model = next((m for m in models if m["id"] == model_id), None)
                    if model:
                        try:
                            self._start_download(model)
                            active_count += 1
                        except (ValueError, OSError) as e:
                            self.history.insert(0, {"model": model, "status": "failed", "error": str(e), "progress": 0})

    def enqueue(self, model_ids):
        """Add models to download queue."""
        models = load_models()
        valid_ids = {m["id"] for m in models}
        added = []
        with self.lock:
            for mid in model_ids:
                if mid in valid_ids and mid not in self.queue and mid not in self.active_downloads:
                    self.queue.append(mid)
                    added.append(mid)
        return added

    def _start_download(self, model):
        """Start a wget download in background."""
        dest_file = safe_model_path(model)
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)

        dl_id = model["id"]
        self.active_downloads[dl_id] = {
            "model": model,
            "progress": 0,
            "status": "downloading",
            "speed": "",
            "eta": "",
            "dest_file": dest_file,
            "started_at": time.time(),
            "process": None,
        }

        thread = threading.Thread(target=self._run_download, args=(dl_id, model, dest_file), daemon=True)
        thread.start()

    def _run_download(self, dl_id, model, dest_file):
        """Run wget and parse progress."""
        try:
            cmd = [
                "wget", "-c", "--progress=dot:giga",
                "-O", dest_file,
                model["url"]
            ]
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True
            )
            with self.lock:
                self.active_downloads[dl_id]["process"] = proc

            # Parse wget stderr for progress
            for line in proc.stderr:
                line = line.strip()
                # wget dot progress: "  50% [====>   ] 1,234,567  1.23M/s  eta 5m"
                pct_match = re.search(r'(\d+)%', line)
                speed_match = re.search(r'([\d.]+[KMG]?/s)', line)
                eta_match = re.search(r'eta\s+([\dm\s]+)', line)

                with self.lock:
                    if dl_id in self.active_downloads:
                        if pct_match:
                            self.active_downloads[dl_id]["progress"] = int(pct_match.group(1))
                        if speed_match:
                            self.active_downloads[dl_id]["speed"] = speed_match.group(1)
                        if eta_match:
                            self.active_downloads[dl_id]["eta"] = eta_match.group(1).strip()

            proc.wait()
            with self.lock:
                if dl_id in self.active_downloads:
                    if proc.returncode == 0:
                        self.active_downloads[dl_id]["status"] = "completed"
                        self.active_downloads[dl_id]["progress"] = 100
                    else:
                        self.active_downloads[dl_id]["status"] = "failed"
                    self.active_downloads[dl_id]["finished_at"] = time.time()
                    # Move to history
                    entry = self.active_downloads.pop(dl_id)
                    entry.pop("process", None)
                    self.history.insert(0, entry)
                    # Keep history manageable
                    if len(self.history) > 100:
                        self.history = self.history[:100]

        except Exception as e:
            with self.lock:
                if dl_id in self.active_downloads:
                    self.active_downloads[dl_id]["status"] = "failed"
                    self.active_downloads[dl_id]["error"] = str(e)
                    entry = self.active_downloads.pop(dl_id)
                    entry.pop("process", None)
                    self.history.insert(0, entry)

    def cancel(self, dl_id):
        """Cancel a running or queued download."""
        with self.lock:
            if dl_id in self.queue:
                self.queue.remove(dl_id)
                return True
            if dl_id in self.active_downloads:
                proc = self.active_downloads[dl_id].get("process")
                if proc:
                    proc.terminate()
                self.active_downloads[dl_id]["status"] = "cancelled"
                entry = self.active_downloads.pop(dl_id)
                entry.pop("process", None)
                self.history.insert(0, entry)
                return True
        return False

    def get_status(self):
        """Get current download status."""
        with self.lock:
            active = {}
            for dl_id, info in self.active_downloads.items():
                active[dl_id] = {
                    "model": info["model"],
                    "progress": info["progress"],
                    "status": info["status"],
                    "speed": info["speed"],
                    "eta": info["eta"],
                }
            return {
                "active": active,
                "queue": self.queue[:],
                "history": self.history[:20],
            }

dm = DownloadManager()


# --- Request / Path Helpers ---
def json_body():
    """Return the JSON body as a dict (empty dict for missing/invalid JSON)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def safe_model_path(model):
    """Resolve the model's target path and make sure it stays inside COMFY_ROOT."""
    root = os.path.realpath(COMFY_ROOT)
    path = os.path.realpath(os.path.join(root, model["dest"], model["filename"]))
    if os.path.commonpath([root, path]) != root:
        raise ValueError("Path escapes COMFY_ROOT")
    return path


# --- Disk Usage Helper ---
def get_disk_usage():
    """Get disk usage of COMFY_ROOT."""
    try:
        usage = shutil.disk_usage(COMFY_ROOT)
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "percent": round(usage.used / usage.total * 100, 1),
        }
    except OSError:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

def check_existing_models():
    """Check which models already exist on disk."""
    models = load_models()
    existing = {}
    for m in models:
        try:
            filepath = safe_model_path(m)
        except ValueError:
            continue
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            existing[m["id"]] = {
                "exists": True,
                "size_bytes": size,
                "size_mb": round(size / (1024**2), 1),
            }
    return existing


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/models")
def api_models():
    models = load_models()
    existing = check_existing_models()
    return jsonify({
        "models": models,
        "existing": existing,
        "disk": get_disk_usage(),
        "comfy_root": COMFY_ROOT,
    })

@app.route("/api/download", methods=["POST"])
def api_download():
    data = json_body()
    model_ids = data.get("model_ids", [])
    if not model_ids:
        return jsonify({"error": "No model_ids provided"}), 400
    added = dm.enqueue(model_ids)
    return jsonify({"queued": added, "total_queue": len(dm.queue)})

@app.route("/api/download/cancel", methods=["POST"])
def api_cancel():
    data = json_body()
    dl_id = data.get("id")
    success = dm.cancel(dl_id)
    return jsonify({"success": success})

@app.route("/api/download/status")
def api_status():
    return jsonify(dm.get_status())

@app.route("/api/models/add", methods=["POST"])
def api_add_model():
    """Add a new custom model."""
    data = json_body()
    required = ["name", "category", "size", "url", "dest", "filename"]
    for field in required:
        if not str(data.get(field, "")).strip():
            return jsonify({"error": f"Missing field: {field}"}), 400
    if not re.match(r"^https?://", data["url"]):
        return jsonify({"error": "url must start with http:// or https://"}), 400
    if "/" in data["filename"] or "\\" in data["filename"] or data["filename"] in (".", ".."):
        return jsonify({"error": "filename must not contain path separators"}), 400
    try:
        safe_model_path({"dest": data["dest"], "filename": data["filename"]})
    except ValueError:
        return jsonify({"error": "dest must stay inside COMFY_ROOT"}), 400

    user_models = load_user_models()
    new_id = f"u{len(user_models):04d}_{uuid.uuid4().hex[:6]}"
    model = {
        "id": new_id,
        "name": data["name"],
        "category": data["category"],
        "size": data["size"],
        "url": data["url"],
        "dest": data["dest"].rstrip("/") + "/",
        "filename": data["filename"],
    }
    user_models.append(model)
    save_user_models(user_models)
    return jsonify({"model": model, "total_user_models": len(user_models)})

@app.route("/api/models/delete", methods=["POST"])
def api_delete_model():
    """Delete a user-added model (not base models)."""
    data = json_body()
    model_id = data.get("id")
    user_models = load_user_models()
    before = len(user_models)
    user_models = [m for m in user_models if m["id"] != model_id]
    if len(user_models) < before:
        save_user_models(user_models)
        return jsonify({"success": True})
    return jsonify({"error": "Model not found or is a base model"}), 404

@app.route("/api/models/delete-file", methods=["POST"])
def api_delete_file():
    """Delete a downloaded model file from disk."""
    data = json_body()
    model_id = data.get("id")
    models = load_models()
    model = next((m for m in models if m["id"] == model_id), None)
    if not model:
        return jsonify({"error": "Model not found"}), 404
    try:
        filepath = safe_model_path(model)
    except ValueError:
        return jsonify({"error": "Path escapes COMFY_ROOT"}), 400
    if os.path.isfile(filepath):
        os.remove(filepath)
        return jsonify({"success": True, "deleted": filepath})
    return jsonify({"error": "File not found on disk"}), 404

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = json_body()
        try:
            max_conc = int(data.get("max_concurrent", 2))
        except (TypeError, ValueError):
            return jsonify({"error": "max_concurrent must be a number"}), 400
        dm.max_concurrent = max(1, min(5, max_conc))
        return jsonify({"max_concurrent": dm.max_concurrent})
    return jsonify({
        "max_concurrent": dm.max_concurrent,
        "comfy_root": COMFY_ROOT,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
