#!/usr/bin/env python3
"""
OM-1 Macro Focus Stacking Pipeline - WEB EDITION v4.1
Automated workflow: SD Card → Series Detection → Focus Stacking → Output

NEW in v4.1:
- Auto-opens browser on start
- Live logging with detailed progress
- Real-time progress tracking
- Beautiful modern UI
"""

import os
import sys
import shutil
import subprocess
import yaml
import logging
from pathlib import Path
from datetime import datetime
import time
import hashlib
import threading
import base64
from io import BytesIO
import webbrowser

from flask import Flask, render_template_string, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from PIL import Image

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

CONFIG_FILE = Path.home() / '.stacking_config.yaml'
CACHE_DIR = Path.home() / '.stacking_cache' / 'thumbnails'

# In macro_stacking_web_v4.1.py, load_config() Funktion ändern:

def load_config():
    """Load configuration from YAML file with UTF-8 support"""
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
            'verbose': False,
            'debug': False,
        }
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with UTF-8 encoding
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default, f, default_flow_style=False, allow_unicode=True)
    
    # Read with UTF-8 encoding
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except UnicodeDecodeError:
        # Fallback: try with default encoding
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)

# ═══════════════════════════════════════════════════════════
# Logging Setup
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Flask App Setup
# ═══════════════════════════════════════════════════════════

app = Flask(__name__)
app.config['SECRET_KEY'] = 'om1-stacking-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
config = load_config()
series_data = []
processing_active = False

# ═══════════════════════════════════════════════════════════
# Image Analysis
# ═══════════════════════════════════════════════════════════

def find_sd_cards():
    """Find all mounted SD cards with DCIM folder"""
    volumes = Path('/Volumes')
    sd_cards = []
    
    if not volumes.exists():
        return sd_cards
    
    for volume in volumes.iterdir():
        dcim = volume / 'DCIM'
        if dcim.exists() and dcim.is_dir():
            sd_cards.append(str(dcim))
    
    return sd_cards

def get_image_timestamp(image_path):
    """Extract timestamp from image EXIF data"""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-s3', str(image_path)],
            capture_output=True,
            check=True,
            timeout=5
        )
        
        timestamp_str = result.stdout.decode('utf-8', errors='ignore').strip()
        if not timestamp_str:
            return None
            
        return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
    except:
        return None

def find_image_series(dcim_path, time_threshold=30, min_images=3):
    """Group images into series"""
    images = []
    for root, dirs, files in os.walk(dcim_path):
        for file in files:
            if file.upper().endswith('.ORF'):
                images.append(Path(root) / file)
    
    if not images:
        return []
    
    # Get timestamps
    image_data = []
    total = len(images)
    for i, img in enumerate(images):
        socketio.emit('analysis_progress', {
            'current': i + 1,
            'total': total,
            'message': f"Analyzing {img.name}"
        })
        
        timestamp = get_image_timestamp(img)
        if timestamp:
            image_data.append((str(img), timestamp))
    
    # Sort by timestamp
    image_data.sort(key=lambda x: x[1])
    
    # Group into series
    series = []
    current_series = [image_data[0]]
    
    for i in range(1, len(image_data)):
        prev_time = image_data[i-1][1]
        curr_time = image_data[i][1]
        time_diff = (curr_time - prev_time).total_seconds()
        
        if time_diff <= time_threshold:
            current_series.append(image_data[i])
        else:
            if len(current_series) >= min_images:
                series.append(current_series)
            current_series = [image_data[i]]
    
    if len(current_series) >= min_images:
        series.append(current_series)
    
    return series

# ═══════════════════════════════════════════════════════════
# Thumbnail Generation
# ═══════════════════════════════════════════════════════════

def get_cache_path(image_path):
    """Generate cache path for thumbnail"""
    img_path = Path(image_path)
    stat = img_path.stat()
    cache_key = f"{img_path.stem}_{stat.st_size}_{int(stat.st_mtime)}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
    
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{cache_hash}.jpg"

def generate_thumbnail(image_path, size=(200, 133)):
    """Generate thumbnail with caching"""
    try:
        img_path = Path(image_path)
        
        # 1. Check for OOC JPG
        jpg_path = img_path.with_suffix('.JPG')
        if not jpg_path.exists():
            jpg_path = img_path.with_suffix('.jpg')
        
        if jpg_path.exists():
            img = Image.open(jpg_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Return as base64
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode()
        
        # 2. Check cache
        cache_path = get_cache_path(image_path)
        if cache_path.exists():
            with open(cache_path, 'rb') as f:
                return base64.b64encode(f.read()).decode()
        
        # 3. Generate with ImageMagick
        result = subprocess.run([
            'magick',
            str(img_path) + '[0]',
            '-thumbnail', f'{size[0]}x{size[1]}',
            '-quality', '85',
            'jpg:-'
        ], capture_output=True, check=True, timeout=30)
        
        if result.stdout:
            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(result.stdout)
            
            return base64.b64encode(result.stdout).decode()
        
        return None
    
    except Exception as e:
        logger.debug(f"Thumbnail failed for {image_path}: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# Stacking Processing
# ═══════════════════════════════════════════════════════════

def convert_raw_to_jpg(raw_file, output_dir):
    """Convert ORF to JPG"""
    output_file = output_dir / f"{Path(raw_file).stem}.jpg"
    
    try:
        subprocess.run([
            'magick',
            str(raw_file),
            '-quality', '95',
            str(output_file)
        ], check=True, capture_output=True)
        
        return output_file if output_file.exists() else None
    except:
        return None

def prepare_images_for_stacking(series_images, temp_dir):
    """Prepare images: use OOC JPG or convert ORF"""
    prepared_images = []
    ooc_count = 0
    conv_count = 0
    
    for img_path in series_images:
        orf_file = Path(img_path)
        
        jpg_ooc = orf_file.with_suffix('.JPG')
        if not jpg_ooc.exists():
            jpg_ooc = orf_file.with_suffix('.jpg')
        
        if jpg_ooc.exists():
            dest = temp_dir / jpg_ooc.name
            shutil.copy2(jpg_ooc, dest)
            prepared_images.append(dest)
            ooc_count += 1
        else:
            jpg_converted = convert_raw_to_jpg(orf_file, temp_dir)
            if jpg_converted:
                prepared_images.append(jpg_converted)
                conv_count += 1
    
    return sorted(prepared_images), ooc_count, conv_count

def stack_images_helicon(image_dir, output_file):
    """Stack with Helicon Focus"""
    helicon_binary = Path(config['helicon_binary']).expanduser()
    
    if not helicon_binary.exists():
        return False
    
    method_map = {'A': 0, 'B': 1, 'C': 2}
    method = config.get('helicon_method', 'C')
    method_code = method_map.get(method.upper(), 2)
    
    cmd = [
        str(helicon_binary),
        '-silent',
        '-noprogress',
        f'-mp:{method_code}',
        f'-rp:{config.get("helicon_radius", 8)}',
        f'-sp:{config.get("helicon_smoothing", 4)}',
        f'-j:{config.get("output_quality", 95)}',
        f'-save:{output_file}',
        str(image_dir)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and output_file.exists()
    except:
        return False

def process_series_background(selected_indices):
    """Process selected series in background"""
    global processing_active
    processing_active = True
    
    stats = {
        'successful': 0,
        'failed': 0,
        'total_time': 0
    }
    
    selected_series = [series_data[i] for i in selected_indices]
    total = len(selected_series)
    
    socketio.emit('processing_log', {
        'message': f'Processing {total} series...',
        'level': 'info'
    })
    
    for i, series_dict in enumerate(selected_series):
        series_num = i + 1
        
        socketio.emit('processing_progress', {
            'current': i,
            'total': total,
            'message': f"Serie {series_num}/{total}: Starting...",
            'status': 'info'
        })
        
        start_time = time.time()
        
        # Extract images from dict
        series_images = series_dict['images']
        
        socketio.emit('processing_log', {
            'message': f'Serie {series_num}: {len(series_images)} images',
            'level': 'info'
        })
        
        # Get first image timestamp
        first_img_data = series_images[0]
        first_img_path = first_img_data['path']
        first_timestamp = datetime.fromisoformat(first_img_data['timestamp'])
        
        # Setup directories
        output_dir = Path(config['output_dir']).expanduser()
        temp_dir = Path(config['temp_dir']).expanduser() / f"series_{series_num}"
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Prepare images
            socketio.emit('processing_log', {
                'message': f'Serie {series_num}: Preparing images...',
                'level': 'info'
            })
            
            image_paths = [img['path'] for img in series_images]
            prepared_images, ooc_count, conv_count = prepare_images_for_stacking(image_paths, temp_dir)
            
            if not prepared_images:
                stats['failed'] += 1
                socketio.emit('processing_log', {
                    'message': f'Serie {series_num}: No images prepared!',
                    'level': 'error'
                })
                continue
            
            socketio.emit('processing_log', {
                'message': f'Serie {series_num}: Prepared {len(prepared_images)} images ({ooc_count} OOC JPG, {conv_count} converted)',
                'level': 'success'
            })
            
            # Stack
            timestamp_str = first_timestamp.strftime('%Y%m%d_%H%M%S')
            output_file = output_dir / f"stack_{timestamp_str}.jpg"
            
            socketio.emit('processing_log', {
                'message': f'Serie {series_num}: Stacking with Helicon Focus (Method {config.get("helicon_method", "C")})...',
                'level': 'info'
            })
            
            success = stack_images_helicon(temp_dir, output_file)
            
            if success:
                elapsed = time.time() - start_time
                stats['successful'] += 1
                stats['total_time'] += elapsed
                
                socketio.emit('processing_progress', {
                    'current': series_num,
                    'total': total,
                    'message': f"Serie {series_num}/{total}: Complete!",
                    'status': 'success'
                })
                
                socketio.emit('processing_log', {
                    'message': f'Serie {series_num}: Stack created in {elapsed:.1f}s → {output_file.name}',
                    'level': 'success'
                })
            else:
                stats['failed'] += 1
                socketio.emit('processing_log', {
                    'message': f'Serie {series_num}: Stacking failed!',
                    'level': 'error'
                })
        
        except Exception as e:
            logger.error(f"Error processing series {series_num}: {e}")
            stats['failed'] += 1
            socketio.emit('processing_log', {
                'message': f'Serie {series_num}: Error - {str(e)}',
                'level': 'error'
            })
        
        finally:
            if not config.get('keep_temp', False):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    processing_active = False
    socketio.emit('processing_complete', stats)

# ═══════════════════════════════════════════════════════════
# Web Routes
# ═══════════════════════════════════════════════════════════

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OM-1 Stacking Pipeline v4.1</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #ecf0f1;
            color: #2c3e50;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .step {
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .step h2 {
            margin-bottom: 20px;
            color: #667eea;
            font-size: 1.5em;
        }
        
        .sd-cards {
            display: grid;
            gap: 15px;
        }
        
        .sd-card {
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 1.1em;
            font-weight: bold;
            border: none;
            text-align: left;
        }
        
        .sd-card:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .series-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .series-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .series-card.selected {
            border-color: #667eea;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .series-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }
        
        .thumbnail {
            width: 100%;
            height: 133px;
            background: #f5f5f5;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        
        .thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .thumbnail.loading {
            color: #999;
            font-size: 0.9em;
        }
        
        .series-info {
            font-size: 0.9em;
        }
        
        .series-title {
            font-weight: bold;
            margin-bottom: 5px;
            color: #2c3e50;
        }
        
        .series-meta {
            color: #7f8c8d;
            font-size: 0.85em;
        }
        
        .checkbox-container {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .checkbox-container input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .checkbox-container label {
            cursor: pointer;
            font-weight: bold;
            color: #27ae60;
        }
        
        .actions {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .btn-primary {
            background: #27ae60;
            color: white;
            flex: 1;
        }
        
        .btn-primary:hover {
            background: #229954;
            box-shadow: 0 4px 15px rgba(39, 174, 96, 0.4);
        }
        
        .btn-secondary {
            background: #3498db;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #2980b9;
        }
        
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c0392b;
        }
        
        .progress-container {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #34495e;
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-success { color: #27ae60; }
        .log-error { color: #e74c3c; }
        .log-info { color: #3498db; }
        .log-warning { color: #f39c12; }
        
        .hidden { display: none; }
        
        @media (max-width: 768px) {
            .series-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 OM-1 Macro Focus Stacking Pipeline</h1>
        <p>Web Edition v4.1 - Modern, Fast, Beautiful</p>
    </div>
    
    <div class="container">
        <!-- Step 1: SD Card Selection -->
        <div id="step1" class="step">
            <h2>📁 Step 1: Select Source</h2>
            <div class="sd-cards" id="sdCards">
                <button class="sd-card" onclick="loadSDCards()">🔄 Scan for SD Cards</button>
            </div>
        </div>
        
        <!-- Step 2: Series Selection -->
        <div id="step2" class="step hidden">
            <h2>📸 Step 2: Select Series to Stack</h2>
            <div class="progress-container" id="analysisProgress">
                <div id="analysisMessage">Analyzing images...</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="analysisBar" style="width: 0%">0%</div>
                </div>
            </div>
            <div class="series-grid" id="seriesGrid"></div>
            <div class="actions">
                <button class="btn btn-secondary" onclick="selectAll()">Select All</button>
                <button class="btn btn-secondary" onclick="selectNone()">Select None</button>
                <button class="btn btn-primary" onclick="startStacking()">
                    ▶ Start Stacking (<span id="selectedCount">0</span> selected)
                </button>
            </div>
        </div>
        
        <!-- Step 3: Processing -->
        <div id="step3" class="step hidden">
            <h2>⚙️ Step 3: Processing Stacks</h2>
            
            <div class="progress-container">
                <div id="processingMessage" style="font-size: 1.1em; font-weight: bold; margin-bottom: 10px;">
                    Starting...
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="processingBar" style="width: 0%">0%</div>
                </div>
                <div style="margin-top: 10px; color: #7f8c8d; font-size: 0.9em;">
                    <span id="processingTime">Elapsed: 0s</span>
                </div>
            </div>
            
            <!-- Live Log -->
            <div style="background: #2c3e50; color: #ecf0f1; border-radius: 8px; padding: 20px; margin-top: 20px; font-family: 'Courier New', monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;" id="liveLog">
                <div style="color: #3498db;">🔬 Starting stacking pipeline...</div>
            </div>
        </div>
        
        <!-- Step 4: Complete -->
        <div id="step4" class="step hidden">
            <h2>✅ Complete!</h2>
            <div id="results"></div>
            <div class="actions">
                <button class="btn btn-primary" onclick="location.reload()">Start New Session</button>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let seriesData = [];
        let selectedIndices = [];
        let processingStartTime = null;
        let processingInterval = null;
        
        // Load SD cards
        function loadSDCards() {
            fetch('/api/sd_cards')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('sdCards');
                    container.innerHTML = '';
                    
                    if (data.cards.length === 0) {
                        container.innerHTML = '<p>No SD cards found. Please insert an SD card.</p>';
                        return;
                    }
                    
                    data.cards.forEach(card => {
                        const btn = document.createElement('button');
                        btn.className = 'sd-card';
                        btn.textContent = `📁 ${card}`;
                        btn.onclick = () => analyzeSeries(card);
                        container.appendChild(btn);
                    });
                });
        }
        
        // Analyze series
        function analyzeSeries(path) {
            document.getElementById('step1').classList.add('hidden');
            document.getElementById('step2').classList.remove('hidden');
            document.getElementById('analysisProgress').style.display = 'block';
            document.getElementById('seriesGrid').style.display = 'none';
            
            fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            })
            .then(r => r.json())
            .then(data => {
                seriesData = data.series;
                displaySeries();
            });
        }
        
        // Display series
        function displaySeries() {
            document.getElementById('analysisProgress').style.display = 'none';
            document.getElementById('seriesGrid').style.display = 'grid';
            
            const grid = document.getElementById('seriesGrid');
            grid.innerHTML = '';
            
            seriesData.forEach((series, idx) => {
                const card = document.createElement('div');
                card.className = 'series-card selected';
                card.dataset.index = idx;
                card.onclick = () => toggleSeries(idx);
                
                const firstImg = series.images[0];
                const lastImg = series.images[series.images.length - 1];
                const duration = Math.round((new Date(lastImg.timestamp) - new Date(firstImg.timestamp)) / 1000);
                
                card.innerHTML = `
                    <div class="thumbnail loading" id="thumb-${idx}">⏳ Loading...</div>
                    <div class="series-info">
                        <div class="series-title">Serie ${idx + 1}</div>
                        <div class="series-meta">📸 ${series.images.length} images</div>
                        <div class="series-meta">⏱️ ${duration}s</div>
                    </div>
                    <div class="checkbox-container">
                        <input type="checkbox" id="check-${idx}" checked>
                        <label for="check-${idx}">Stack</label>
                    </div>
                `;
                
                grid.appendChild(card);
                
                // Load thumbnail async
                loadThumbnail(idx, firstImg.path);
            });
            
            selectedIndices = [...Array(seriesData.length).keys()];
            updateSelectedCount();
        }
        
        // Load thumbnail
        function loadThumbnail(idx, imagePath) {
            fetch('/api/thumbnail', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: imagePath})
            })
            .then(r => r.json())
            .then(data => {
                const thumb = document.getElementById(`thumb-${idx}`);
                if (data.thumbnail) {
                    thumb.innerHTML = `<img src="data:image/jpeg;base64,${data.thumbnail}">`;
                    thumb.classList.remove('loading');
                } else {
                    thumb.textContent = 'RAW';
                    thumb.classList.remove('loading');
                }
            });
        }
        
        // Toggle series selection
        function toggleSeries(idx) {
            const card = document.querySelector(`.series-card[data-index="${idx}"]`);
            const checkbox = document.getElementById(`check-${idx}`);
            
            if (selectedIndices.includes(idx)) {
                selectedIndices = selectedIndices.filter(i => i !== idx);
                card.classList.remove('selected');
                checkbox.checked = false;
            } else {
                selectedIndices.push(idx);
                card.classList.add('selected');
                checkbox.checked = true;
            }
            
            updateSelectedCount();
        }
        
        function selectAll() {
            selectedIndices = [...Array(seriesData.length).keys()];
            document.querySelectorAll('.series-card').forEach(card => {
                card.classList.add('selected');
                const idx = card.dataset.index;
                document.getElementById(`check-${idx}`).checked = true;
            });
            updateSelectedCount();
        }
        
        function selectNone() {
            selectedIndices = [];
            document.querySelectorAll('.series-card').forEach(card => {
                card.classList.remove('selected');
                const idx = card.dataset.index;
                document.getElementById(`check-${idx}`).checked = false;
            });
            updateSelectedCount();
        }
        
        function updateSelectedCount() {
            document.getElementById('selectedCount').textContent = selectedIndices.length;
        }
        
        // Start stacking
        function startStacking() {
            if (selectedIndices.length === 0) {
                alert('Please select at least one series!');
                return;
            }
            
            document.getElementById('step2').classList.add('hidden');
            document.getElementById('step3').classList.remove('hidden');
            
            // Start timer
            processingStartTime = Date.now();
            processingInterval = setInterval(() => {
                const elapsed = Math.round((Date.now() - processingStartTime) / 1000);
                document.getElementById('processingTime').textContent = `Elapsed: ${elapsed}s`;
            }, 1000);
            
            addLogEntry('Starting stacking process...', 'info');
            addLogEntry(`Selected ${selectedIndices.length} series`, 'info');
            
            fetch('/api/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({indices: selectedIndices})
            });
        }
        
        function addLogEntry(message, level) {
            const log = document.getElementById('liveLog');
            const entry = document.createElement('div');
            entry.className = `log-entry log-${level}`;
            
            const timestamp = new Date().toLocaleTimeString();
            const icon = {
                'success': '✓',
                'error': '✗',
                'warning': '⚠',
                'info': '→'
            }[level] || '•';
            
            entry.textContent = `[${timestamp}] ${icon} ${message}`;
            log.appendChild(entry);
            
            // Auto-scroll to bottom
            log.scrollTop = log.scrollHeight;
        }
        
        // WebSocket events
        socket.on('analysis_progress', data => {
            const pct = Math.round((data.current / data.total) * 100);
            document.getElementById('analysisBar').style.width = pct + '%';
            document.getElementById('analysisBar').textContent = pct + '%';
            document.getElementById('analysisMessage').textContent = data.message;
        });
        
        socket.on('processing_progress', data => {
            const pct = Math.round((data.current / data.total) * 100);
            document.getElementById('processingBar').style.width = pct + '%';
            document.getElementById('processingBar').textContent = `${data.current}/${data.total}`;
            document.getElementById('processingMessage').textContent = data.message;
            
            // Add to live log
            addLogEntry(data.message, data.status || 'info');
        });
        
        socket.on('processing_log', data => {
            addLogEntry(data.message, data.level || 'info');
        });
        
        socket.on('processing_complete', data => {
            if (processingInterval) {
                clearInterval(processingInterval);
            }
            
            document.getElementById('step3').classList.add('hidden');
            document.getElementById('step4').classList.remove('hidden');
            
            const totalMin = (data.total_time / 60).toFixed(1);
            const avgSec = data.successful > 0 ? (data.total_time / data.successful).toFixed(1) : 0;
            
            document.getElementById('results').innerHTML = `
                <div style="background: #d4edda; border: 2px solid #28a745; border-radius: 8px; padding: 20px; margin-bottom: 15px;">
                    <p style="font-size: 1.3em; margin-bottom: 10px; color: #155724;">
                        ✅ Successfully created <strong>${data.successful}</strong> stack(s)!
                    </p>
                </div>
                ${data.failed > 0 ? `
                <div style="background: #f8d7da; border: 2px solid #dc3545; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                    <p style="color: #721c24;">❌ Failed: ${data.failed}</p>
                </div>
                ` : ''}
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px;">
                    <p><strong>⏱️ Total time:</strong> ${data.total_time.toFixed(1)}s (${totalMin}m)</p>
                    ${data.successful > 0 ? `<p><strong>⚡ Avg time/stack:</strong> ${avgSec}s</p>` : ''}
                </div>
            `;
        });
        
        // Auto-load on page load
        loadSDCards();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sd_cards')
def api_sd_cards():
    """Get available SD cards"""
    cards = find_sd_cards()
    return jsonify({'cards': cards})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyze images and find series"""
    global series_data
    
    data = request.json
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'No path provided'}), 400
    
    # Find series in background
    def analyze():
        global series_data
        series = find_image_series(path, 
            time_threshold=config.get('time_threshold', 30),
            min_images=config.get('min_images', 3)
        )
        
        # Format for JSON
        series_data = []
        for s in series:
            series_data.append({
                'images': [
                    {'path': img[0], 'timestamp': img[1].isoformat()}
                    for img in s
                ]
            })
    
    thread = threading.Thread(target=analyze)
    thread.start()
    thread.join()  # Wait for completion
    
    return jsonify({'series': series_data})

@app.route('/api/thumbnail', methods=['POST'])
def api_thumbnail():
    """Generate thumbnail for image"""
    data = request.json
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'No path provided'}), 400
    
    thumbnail = generate_thumbnail(path)
    return jsonify({'thumbnail': thumbnail})

@app.route('/api/process', methods=['POST'])
def api_process():
    """Start processing selected series"""
    data = request.json
    indices = data.get('indices', [])
    
    if not indices:
        return jsonify({'error': 'No series selected'}), 400
    
    # Start processing in background
    thread = threading.Thread(target=process_series_background, args=(indices,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})

# ═══════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════

def open_browser():
    """Open browser after short delay - works in bundled app"""
    time.sleep(1.5)
    try:
        # Use macOS 'open' command (more reliable in .app bundle)
        subprocess.run(['open', 'http://localhost:8080'], check=False)
    except:
        # Fallback to webbrowser
        import webbrowser
        webbrowser.open('http://localhost:8080')

def main():
    """Start web server"""
    print("\n" + "="*60)
    print("🔬 OM-1 Macro Focus Stacking Pipeline v4.1 - WEB EDITION")
    print("="*60)
    print("\n🌐 Starting web server...")
    print("📱 Server will be available at: http://localhost:8080")
    print("🌍 Browser should open automatically...")
    print("\n💡 If browser doesn't open, manually visit: http://localhost:8080")
    print("💡 Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    # Show macOS notification
    try:
        subprocess.run([
            'osascript', '-e',
            'display notification "Server starting at http://localhost:8080" '
            'with title "OM-1 Stacking Pipeline"'
        ], check=False, capture_output=True)
    except:
        pass
    
    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start server
    try:
        socketio.run(app, host='127.0.0.1', port=8080, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)