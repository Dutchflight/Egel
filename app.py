import os
import uuid
import subprocess
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file

app = Flask(__name__, static_folder="static", template_folder="static")

UPLOAD_DIR = Path("/tmp/uploads")
OUTPUT_DIR = Path("/tmp/outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Job status tracking: job_id -> {"status", "progress", "filename", "output", "error"}
jobs = {}
jobs_lock = threading.Lock()


def run_ffmpeg(job_id: str, input_path: Path, output_path: Path, original_name: str):
    with jobs_lock:
        jobs[job_id]["status"] = "converting"
        jobs[job_id]["progress"] = 50

    try:
        result = subprocess.run(
            ["ffmpeg", "-y",
             "-i", str(input_path),
             "-c:v", "libx264",
             "-c:a", "aac",
             "-movflags", "+faststart",
             str(output_path)],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0 and output_path.exists():
            with jobs_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["output"] = output_path.name
        else:
            error_msg = result.stderr[-500:] if result.stderr else "FFmpeg fout"
            with jobs_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = error_msg
    except subprocess.TimeoutExpired:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Conversie duurde te lang (timeout)"
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
