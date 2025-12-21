import os
import uuid
import subprocess
from flask import Flask, request, jsonify, send_from_directory

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_ROOT, "static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audios")
VIDEO_DIR = os.path.join(STATIC_DIR, "videos")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/video_generation")
def video_generation():
    if "audio" not in request.files:
        return jsonify({"error": "missing form-data file field: audio"}), 400

    f = request.files["audio"]
    if not f.filename.lower().endswith(".wav"):
        return jsonify({"error": "only .wav is supported"}), 400

    task_id = str(uuid.uuid4())[:8]
    wav_path = os.path.join(AUDIO_DIR, f"{task_id}.wav")
    out_mp4 = os.path.join(VIDEO_DIR, f"{task_id}.mp4")

    f.save(wav_path)

    # Call your unified inference script
    cmd = [
        "bash", os.path.join(APP_ROOT, "run_talkinggaussian.sh"),
        "infer",
        "--wav", wav_path,
        "--out", out_mp4,
        "--extractor", "deepspeech",
        "--dataset", "data/May",
        "--model", "output/talking_May",
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return jsonify({
            "error": "inference failed",
            "stderr": r.stderr[-2000:],
            "stdout": r.stdout[-2000:],
        }), 500

    return jsonify({
        "task_id": task_id,
        "video_url": f"/static/videos/{task_id}.mp4"
    })

@app.get("/static/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
