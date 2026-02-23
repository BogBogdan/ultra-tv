import re
import os
import csv
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SCHEDULE_FILE = "schedule.txt"

def parse_schedule():
    """Reads the schedule file and returns a list of dictionaries with date and startTime."""
    items = []
    if not os.path.exists(SCHEDULE_FILE):
        return items
    
    # Regex for "date","startTime","name","link","duration"
    pattern = re.compile(r'"([^"]*)","([^"]*)","([^"]*)","([^"]*)","([^"]*)"')
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                items.append({
                    "date": match.group(1),
                    "startTime": match.group(2),
                    "name": match.group(3),
                    "link": match.group(4),
                    "duration": match.group(5)
                })
    return items

def save_schedule(schedule):
    """Saves the schedule back to file with date and startTime."""
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        for item in schedule:
            f.write(f'"{item.get("date", "2026-02-23")}","{item.get("startTime", "00:00")}","{item["name"]}","{item["link"]}","{item["duration"]}"\n')

@app.route('/')
def index():
    return "<h1>TV API is running</h1><p>The Web UI is available at <a href='http://localhost:5173'>http://localhost:5173</a></p>"

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    return jsonify(parse_schedule())

@app.route('/api/schedule', methods=['POST'])
def update_schedule():
    data = request.json
    if not isinstance(data, list):
        return jsonify({"error": "Invalid format, expected list"}), 400
    save_schedule(data)
    return jsonify({"status": "success"})

import subprocess

def get_video_duration(file_path):
    """Gets the duration of a video file using ffprobe or yt-dlp."""
    # Metoda 1: ffprobe (brže)
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5)
        seconds = float(result.stdout.strip())
        return format_seconds(seconds)
    except Exception:
        pass

    # Metoda 2: yt-dlp --get-duration (pouzdanije jer ga već imamo)
    try:
        # Koristimo yt-dlp iz venv-a ako možemo, ili sistemski
        yt_dlp_cmd = os.path.join(os.getcwd(), 'venv', 'Scripts', 'yt-dlp.exe')
        if not os.path.exists(yt_dlp_cmd):
            yt_dlp_cmd = 'yt-dlp'
            
        cmd = [yt_dlp_cmd, '--get-duration', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
        duration_str = result.stdout.strip()
        
        # Ako yt-dlp vrati HH:MM:SS format, to je ok
        if ':' in duration_str:
            return duration_str
        
        # Ako vrati samo sekunde
        try:
            return format_seconds(float(duration_str))
        except:
            return duration_str
    except Exception:
        return "0:00"

def format_seconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

LIBRARY_FILE = "videos.txt"

def parse_library():
    """Reads the library file and returns a list of dictionaries."""
    library = []
    if not os.path.exists(LIBRARY_FILE):
        return library
    
    pattern = re.compile(r'"([^"]*)","([^"]*)","([^"]*)"')
    with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                library.append({
                    "name": match.group(1),
                    "link": match.group(2),
                    "duration": match.group(3)
                })
    return library

@app.route('/api/videos', methods=['GET'])
def get_library_videos():
    """Returns a list of videos from the library file."""
    return jsonify(parse_library())

if __name__ == '__main__':
    # Ensure files exist
    for f_path in [SCHEDULE_FILE, LIBRARY_FILE]:
        if not os.path.exists(f_path):
            with open(f_path, "w", encoding="utf-8") as f:
                pass
    app.run(port=5000, debug=True)
