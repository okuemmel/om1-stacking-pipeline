#!/usr/bin/env python3
"""
OM-1 Macro Focus Stacking Pipeline - Web Interface
Version 4.2 Final - With scan progress feedback
"""

import os
import sys
import subprocess
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import yaml
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from PIL import Image

# ===== CONFIGURATION =====
CONFIG_FILE = Path.home() / '.stacking_config.yaml'
CACHE_DIR = Path.home() / '.stacking_cache' / 'thumbnails'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'om1-stacking-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
processing_active = False
current_series_data = []

# ===== LOGGING =====
def log(message, level="INFO"):
    """Enhanced logging with timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

# ===== CONFIG =====
def load_config():
    """Load configuration from YAML file"""
    if not CONFIG_FILE.exists():
        default = {
            'sd_card_mode': 'ask',
            'watch_dir': '/Volumes/SD-CARD/DCIM',
            'output_dir': '~/Pictures/Stacked',
            'temp_dir': '/tmp/stacking',
            'time_threshold': 30,
            'min_images': 3,
            'stacker': 'helicon',
            'helicon_binary': '/Applications/HeliconFocus.app/Contents/MacOS/HeliconFocus',
            'helicon_method': 'C',
            'helicon_radius': 8,
            'helicon_smoothing': 4,
            'jpg_quality': 95,
            'jpg_converter': 'imagemagick',
            'output_format': 'jpg',
            'output_quality': 95,
            'keep_temp': False,
        }
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default, f, default_flow_style=False)
        log("Created default config")
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# ===== SD CARD DETECTION =====
def find_sd_cards():
    """Find all mounted SD cards"""
    log("Searching for SD cards...")
    sd_cards = []
    
    volumes_dir = Path('/Volumes')
    if not volumes_dir.exists():
        return sd_cards
    
    for volume in volumes_dir.iterdir():
        if volume.is_dir() and volume.name not in ['.', '..', 'Macintosh HD']:
            dcim_path = volume / 'DCIM'
            if dcim_path.exists():
                log(f"Found SD card: {volume.name}")
                sd_cards.append({
                    'name': volume.name,
                    'path': str(volume),
                    'dcim': str(dcim_path)
                })
    
    return sd_cards

# ===== IMAGE DETECTION =====
def find_images(directory: Path) -> List[Path]:
    """Find all image files recursively"""
    log(f"Searching: {directory}")
    images = []
    
    for ext in ['*.ORF', '*.orf', '*.JPG', '*.jpg']:
        found = list(directory.rglob(ext))
        if found:
            log(f"Found {len(found)} {ext} files")
            images.extend(found)
    
    images = sorted(set(images))
    log(f"Total: {len(images)} images")
    return images

def get_image_metadata(image_path: Path) -> Optional[Dict]:
    """Extract metadata from image"""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-s3', str(image_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            date_str = result.stdout.strip()
            dt = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            return {'path': image_path, 'timestamp': dt, 'name': image_path.name}
    except:
        pass
    
    # Fallback
    try:
        mtime = image_path.stat().st_mtime
        return {
            'path': image_path,
            'timestamp': datetime.fromtimestamp(mtime),
            'name': image_path.name
        }
    except:
        return None

# ===== SERIES DETECTION =====
def detect_series(images: List[Path], config: Dict) -> List[List[Dict]]:
    """Detect focus stacking series"""
    if not images:
        return []
    
    time_threshold = config.get('time_threshold', 30)
    min_images = config.get('min_images', 3)
    
    log(f"Detecting series (threshold: {time_threshold}s, min: {min_images})")
    
    # Get metadata
    images_with_metadata = []
    total = len(images)
    for i, img in enumerate(images):
        if i % 10 == 0:
            log(f"Reading metadata: {i+1}/{total}")
            socketio.emit('scan_progress', {
                'step': 'reading_metadata',
                'message': f'Reading metadata: {i+1}/{total}...',
                'current': i + 1,
                'total': total
            })
        
        metadata = get_image_metadata(img)
        if metadata:
            images_with_metadata.append(metadata)
    
    if not images_with_metadata:
        return []
    
    # Sort by timestamp
    images_with_metadata.sort(key=lambda x: x['timestamp'])
    
    # Group into series
    series = []
    current_series = [images_with_metadata[0]]
    
    for i in range(1, len(images_with_metadata)):
        prev = images_with_metadata[i-1]
        curr = images_with_metadata[i]
        time_diff = (curr['timestamp'] - prev['timestamp']).total_seconds()
        
        if time_diff <= time_threshold:
            current_series.append(curr)
        else:
            if len(current_series) >= min_images:
                series.append(current_series)
            current_series = [curr]
    
    if len(current_series) >= min_images:
        series.append(current_series)
    
    log(f"Detected {len(series)} series")
    return series

# ===== THUMBNAIL GENERATION =====
def generate_thumbnail(image_path: Path, size=(200, 133)) -> Optional[Path]:
    """Generate thumbnail with caching"""
    try:
        stat = image_path.stat()
        cache_key = f"{image_path.name}_{size[0]}x{size[1]}_{stat.st_size}_{stat.st_mtime}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        cache_path = CACHE_DIR / f"{cache_hash}.jpg"
        
        if cache_path.exists():
            return cache_path
        
        if image_path.suffix.lower() == '.orf':
            subprocess.run(
                ['magick', f'{image_path}[0]', '-thumbnail', f'{size[0]}x{size[1]}', str(cache_path)],
                capture_output=True,
                timeout=10
            )
            if cache_path.exists():
                return cache_path
        
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(cache_path, 'JPEG', quality=85)
            return cache_path
    except Exception as e:
        log(f"Thumbnail error: {e}", "WARNING")
        return None

# ===== STACKING =====
def prepare_images(series: List[Dict], temp_dir: Path, config: Dict) -> List[Path]:
    """Prepare images for stacking"""
    temp_dir.mkdir(parents=True, exist_ok=True)
    prepared = []
    
    for i, img_data in enumerate(series):
        img_path = img_data['path']
        dest = temp_dir / f"{i:04d}.jpg"
        
        if img_path.suffix.lower() in ['.jpg', '.jpeg']:
            shutil.copy2(img_path, dest)
            prepared.append(dest)
        elif img_path.suffix.lower() == '.orf':
            jpg_path = img_path.with_suffix('.JPG')
            if not jpg_path.exists():
                jpg_path = img_path.with_suffix('.jpg')
            
            if jpg_path.exists():
                shutil.copy2(jpg_path, dest)
                prepared.append(dest)
            else:
                subprocess.run(
                    ['magick', str(img_path), '-quality', '95', str(dest)],
                    capture_output=True,
                    timeout=30
                )
                if dest.exists():
                    prepared.append(dest)
    
    return prepared

def stack_with_helicon(images: List[Path], output_path: Path, config: Dict) -> bool:
    """Stack with Helicon Focus"""
    helicon = config.get('helicon_binary')
    if not Path(helicon).exists():
        log("Helicon not found", "ERROR")
        return False
    
    cmd = [
        helicon, '-silent',
        f'-mp:{config.get("helicon_method", "C")}',
        f'-rp:{config.get("helicon_radius", 8)}',
        f'-sp:{config.get("helicon_smoothing", 4)}',
    ]
    cmd.extend([str(img) for img in images])
    cmd.append(f'-save:{output_path}')
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        return result.returncode == 0 and output_path.exists()
    except:
        return False

def add_metadata(output_path: Path, series: List[Dict], config: Dict):
    """Add EXIF metadata"""
    try:
        subprocess.run([
            'exiftool', '-overwrite_original',
            '-TagsFromFile', str(series[0]['path']),
            '-all:all',
            f'-UserComment=Stacked from {len(series)} images',
            '-Software=OM-1 Stacking Pipeline v4.2',
            str(output_path)
        ], capture_output=True, timeout=10)
    except:
        pass

# ===== PROCESSING =====
def process_series_background(series_ids: List[int], config: Dict):
    """Process series in background"""
    global processing_active
    processing_active = True
    
    output_dir = Path(config['output_dir']).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_base = Path(config['temp_dir'])
    
    total = len(series_ids)
    success = 0
    
    for idx, sid in enumerate(series_ids):
        try:
            series_data = current_series_data[sid]
            series = [{'path': Path(img['path']), 'name': img['name']} for img in series_data['images']]
            
            socketio.emit('progress', {
                'current': idx + 1,
                'total': total,
                'percent': int((idx / total) * 100),
                'status': f"Processing {idx+1}/{total}",
                'log': f"→ Series {idx+1}: {len(series)} images"
            })
            
            temp_dir = temp_base / f"series_{sid}_{int(time.time())}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            prepared = prepare_images(series, temp_dir, config)
            
            socketio.emit('progress', {
                'current': idx + 1,
                'total': total,
                'percent': int((idx / total) * 100),
                'status': f"Stacking {idx+1}/{total}",
                'log': f"  Stacking {len(prepared)} images..."
            })
            
            output_path = output_dir / f"stack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            if stack_with_helicon(prepared, output_path, config):
                add_metadata(output_path, series, config)
                success += 1
                socketio.emit('progress', {
                    'current': idx + 1,
                    'total': total,
                    'percent': int(((idx+1) / total) * 100),
                    'status': f"Complete {idx+1}/{total}",
                    'log': f"  ✓ {output_path.name}"
                })
            else:
                socketio.emit('progress', {
                    'current': idx + 1,
                    'total': total,
                    'percent': int(((idx+1) / total) * 100),
                    'log': f"  ✗ Failed"
                })
            
            if not config.get('keep_temp'):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            log(f"Error: {e}", "ERROR")
            socketio.emit('progress', {
                'current': idx + 1,
                'total': total,
                'percent': int(((idx+1) / total) * 100),
                'log': f"  ✗ Error: {e}"
            })
    
    socketio.emit('complete', {'total': total, 'success': success, 'failed': total - success, 'time': 0})
    processing_active = False

# ===== API ROUTES =====
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sd-cards')
def get_sd_cards():
    try:
        return jsonify({'sd_cards': find_sd_cards()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan', methods=['POST'])
def scan_directory():
    """Scan with progress updates"""
    try:
        directory = Path(request.json.get('directory', '')).expanduser().resolve()
        
        if not directory.exists():
            return jsonify({'error': 'Directory not found'}), 404
        
        socketio.emit('scan_progress', {'step': 'finding', 'message': 'Finding images...'})
        
        images = find_images(directory)
        if not images:
            return jsonify({'error': 'No images found'}), 404
        
        socketio.emit('scan_progress', {'step': 'metadata', 'message': f'Reading metadata from {len(images)} images...'})
        
        config = load_config()
        series = detect_series(images, config)
        
        if not series:
            return jsonify({'error': 'No series detected'}), 404
        
        socketio.emit('scan_progress', {'step': 'thumbnails', 'message': f'Generating thumbnails for {len(series)} series...'})
        
        global current_series_data
        current_series_data = []
        
        for i, s in enumerate(series):
            socketio.emit('scan_progress', {
                'step': 'thumbnails',
                'message': f'Thumbnail {i+1}/{len(series)}...',
                'current': i+1,
                'total': len(series)
            })
            
            thumb = generate_thumbnail(s[0]['path'])
            current_series_data.append({
                'id': i,
                'image_count': len(s),
                'start_time': s[0]['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': s[-1]['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'duration': int((s[-1]['timestamp'] - s[0]['timestamp']).total_seconds()),
                'thumbnail': f'/api/thumbnail/{i}' if thumb else None,
                'images': [{'path': str(img['path']), 'name': img['name']} for img in s]
            })
        
        log(f"Scan complete: {len(current_series_data)} series")
        return jsonify({'series': current_series_data})
    
    except Exception as e:
        log(f"Scan error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/thumbnail/<int:series_id>')
def get_thumbnail(series_id):
    try:
        series = current_series_data[series_id]
        thumb = generate_thumbnail(Path(series['images'][0]['path']))
        if thumb:
            return send_file(thumb, mimetype='image/jpeg')
        return jsonify({'error': 'Not available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_api():
    global processing_active
    if processing_active:
        return jsonify({'error': 'Already processing'}), 400
    
    try:
        series_ids = request.json.get('series_ids', [])
        if not series_ids:
            return jsonify({'error': 'No series selected'}), 400
        
        config = load_config()
        
        import threading
        thread = threading.Thread(target=process_series_background, args=(series_ids, config))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'started', 'total': len(series_ids)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== HTML (gekürzt - nutze das von oben, ergänze nur scan_progress listener) =====
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OM-1 Stacking Pipeline</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        /* ... alle Styles von oben ... */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { opacity: 0.9; font-size: 1.1em; }
        .step {
            padding: 30px;
            border-bottom: 1px solid #eee;
            display: none;
        }
        .step.active { display: block; }
        .step h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin: 5px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .sd-cards, .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .sd-card, .series-card {
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .sd-card:hover, .series-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .selected {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
        }
        .series-thumbnail {
            width: 100%;
            height: 150px;
            background: #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3em;
            color: #ddd;
        }
        .series-thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .series-info {
            padding: 15px;
        }
        .progress-bar {
            height: 40px;
            background: #f0f0f0;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .log {
            background: #1e1e1e;
            color: #00ff00;
            padding: 20px;
            border-radius: 10px;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
            margin: 20px 0;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px;
        }
        .error {
            background: #fee;
            color: #c00;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .success {
            background: #efe;
            color: #060;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.2em;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔬 OM-1 Stacking Pipeline</h1>
            <p class="subtitle">v4.2 - With Live Progress</p>
        </header>
        
        <div id="step1" class="step active">
            <h2>📀 Select SD Card</h2>
            <div class="controls">
                <button class="btn" onclick="scanSDCards()">🔍 Scan SD Cards</button>
                <button class="btn" onclick="selectManual()">📁 Browse</button>
            </div>
            <div id="sdCardList" class="sd-cards"></div>
            <div id="error1" class="error" style="display:none;"></div>
        </div>
        
        <div id="step2" class="step">
            <h2>🖼️ Select Series</h2>
            <div class="controls">
                <button class="btn" onclick="selectAll()">✅ All</button>
                <button class="btn" onclick="selectNone()">❌ None</button>
                <button class="btn" onclick="startProcess()">🚀 Stack</button>
                <button class="btn" onclick="back()">← Back</button>
            </div>
            <div id="seriesGrid" class="series-grid"></div>
            <div id="error2" class="error" style="display:none;"></div>
        </div>
        
        <div id="step3" class="step">
            <h2>⚙️ Processing</h2>
            <div class="progress-bar">
                <div id="progressFill" class="progress-fill" style="width:0%;">0%</div>
            </div>
            <div id="log" class="log"></div>
        </div>
        
        <div id="step4" class="step">
            <h2>✅ Complete</h2>
            <div id="results" class="success"></div>
            <button class="btn" onclick="location.reload()">🔄 Again</button>
        </div>
    </div>
    
    <script>
        const socket = io();
        let seriesData = [];
        let selected = new Set();
        
        socket.on('scan_progress', (data) => {
            const grid = document.getElementById('seriesGrid');
            let html = `<div class="loading"><div class="spinner"></div><p><strong>${data.message}</strong></p>`;
            if (data.current && data.total) {
                const pct = Math.round((data.current / data.total) * 100);
                html += `<div style="width:300px;margin:20px auto;"><div class="progress-bar"><div class="progress-fill" style="width:${pct}%;">${pct}%</div></div></div>`;
            }
            html += '</div>';
            grid.innerHTML = html;
        });
        
        socket.on('progress', (data) => {
            const fill = document.getElementById('progressFill');
            const log = document.getElementById('log');
            fill.style.width = data.percent + '%';
            fill.textContent = data.percent + '%';
            if (data.log) {
                log.innerHTML += `<div>${data.log}</div>`;
                log.scrollTop = log.scrollHeight;
            }
        });
        
        socket.on('complete', (data) => {
            showStep(4);
            document.getElementById('results').innerHTML = `
                <h2>🎉 Done!</h2>
                <p><strong>${data.success}</strong> of <strong>${data.total}</strong> stacked</p>
            `;
        });
        
        function showStep(n) {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById('step' + n).classList.add('active');
        }
        
        async function scanSDCards() {
            const list = document.getElementById('sdCardList');
            list.innerHTML = '<div class="loading"><div class="spinner"></div><p>Scanning...</p></div>';
            
            const res = await fetch('/api/sd-cards');
            const data = await res.json();
            
            list.innerHTML = '';
            data.sd_cards.forEach(card => {
                const div = document.createElement('div');
                div.className = 'sd-card';
                div.innerHTML = `<h3>💾 ${card.name}</h3><p>${card.dcim}</p>`;
                div.onclick = () => selectCard(card.dcim, div);
                list.appendChild(div);
            });
        }
        
        async function selectCard(dir, el) {
            document.querySelectorAll('.sd-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
            await scanDir(dir);
        }
        
        function selectManual() {
            const path = prompt('Path:', '/Volumes/');
            if (path) scanDir(path);
        }
        
        async function scanDir(dir) {
            showStep(2);
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Scanning...</p></div>';
            
            const res = await fetch('/api/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({directory: dir})
            });
            
            const data = await res.json();
            if (data.error) {
                grid.innerHTML = `<div class="error">${data.error}</div>`;
                return;
            }
            
            seriesData = data.series;
            selected.clear();
            
            grid.innerHTML = '';
            seriesData.forEach((s, i) => {
                const card = document.createElement('div');
                card.className = 'series-card';
                card.innerHTML = `
                    <div class="series-thumbnail">
                        ${s.thumbnail ? `<img src="${s.thumbnail}?t=${Date.now()}">` : '📷'}
                    </div>
                    <div class="series-info">
                        <h3>Series ${i+1}</h3>
                        <p>📸 ${s.image_count} images</p>
                        <p>🕒 ${s.duration}s</p>
                    </div>
                `;
                card.onclick = () => toggle(i, card);
                grid.appendChild(card);
            });
        }
        
        function toggle(i, el) {
            if (selected.has(i)) {
                selected.delete(i);
                el.classList.remove('selected');
            } else {
                selected.add(i);
                el.classList.add('selected');
            }
        }
        
        function selectAll() {
            selected.clear();
            seriesData.forEach((_, i) => selected.add(i));
            document.querySelectorAll('.series-card').forEach(c => c.classList.add('selected'));
        }
        
        function selectNone() {
            selected.clear();
            document.querySelectorAll('.series-card').forEach(c => c.classList.remove('selected'));
        }
        
        async function startProcess() {
            if (selected.size === 0) {
                alert('Select at least one series');
                return;
            }
            
            showStep(3);
            document.getElementById('log').innerHTML = '<div>[INFO] Starting...</div>';
            
            await fetch('/api/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({series_ids: Array.from(selected)})
            });
        }
        
        function back() {
            showStep(1);
        }
        
        window.onload = scanSDCards;
    </script>
</body>
</html>
'''

# ===== MAIN =====
if __name__ == '__main__':
    print("\n" + "="*60)
    print("OM-1 Stacking Pipeline v4.2")
    print("="*60 + "\n")
    
    config = load_config()
    
    def open_browser():
        time.sleep(2.5)
        try:
            subprocess.run(['open', 'http://127.0.0.1:8080'], check=False)
            log("Browser opened")
        except Exception as e:
            log(f"Browser error: {e}", "WARNING")
    
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
    
    print("🌐 http://127.0.0.1:8080\n" + "="*60 + "\n")
    socketio.run(app, host='127.0.0.1', port=8080, debug=False, allow_unsafe_werkzeug=True)
