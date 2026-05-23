import os
import uuid
import subprocess
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file

app = Flask(__name__, static_folder="static", template_folder="static")

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Job status tracking: job_id -> {"status", "progress", "filename", "output", "error"}
jobs = {}
jobs_lock = threading.Lock()


def run_ffmpeg(job_id: str, input_path: Path, output_path: Path, original_name: str):
    """Run FFmpeg and track progress via duration + time."""
    with jobs_lock:
        jobs[job_id]["status"] = "converting"
        jobs[job_id]["progress"] = 0

    try:
        # First, get duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
            capture_output=True, text=True
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

        # Run FFmpeg with progress output
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            str(output_path)
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    ms = int(line.split("=")[1])
                    current_time = ms / 1_000_000
                    if duration > 0:
                        progress = min(int((current_time / duration) * 100), 99)
                        with jobs_lock:
                            jobs[job_id]["progress"] = progress
                except (ValueError, IndexError):
                    pass

        process.wait()

        if process.returncode == 0 and output_path.exists():
            with jobs_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["output"] = output_path.name
        else:
            stderr_output = ""
            try:
                stderr_output = process.stderr.read()[-500:]
            except Exception:
                pass
            with jobs_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = stderr_output or "FFmpeg fout"
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
    finally:
        try:
            input_path.unlink()
        except Exception:
            pass


@app.route("/")
def index():
    return send_file("static/index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Geen bestand meegestuurd"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Geen bestandsnaam"}), 400

    original_name = Path(file.filename).stem
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}.avi"
    output_filename = f"{original_name}_{job_id[:8]}.mp4"
    output_path = OUTPUT_DIR / output_filename

    file.save(input_path)

    with jobs_lock:
        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "filename": file.filename,
            "output": None,
            "error": None
        }

    thread = threading.Thread(
        target=run_ffmpeg,
        args=(job_id, input_path, output_path, original_name),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "filename": file.filename})


@app.route("/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Onbekende taak"}), 404
    return jsonify(job)


@app.route("/download/<filename>")
def download(filename):
    output_path = OUTPUT_DIR / filename
    if not output_path.exists():
        return jsonify({"error": "Bestand niet gevonden"}), 404
    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename
    )


if __name__ == "__main__":
    print("=" * 50)
    print("  AVI naar MP4 Converter")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
