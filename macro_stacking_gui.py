#!/usr/bin/env python3
"""
OM-1 Macro Focus Stacking Pipeline v3.2
Automated workflow: SD Card → Series Detection → Focus Stacking → Output

NEW in v3.2:
- Full GUI mode (no terminal interaction)
- Matrix layout for many series (responsive grid)
- Smaller thumbnails, first image preview
- Progress tracking in GUI
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
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import io
import threading

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

CONFIG_FILE = Path.home() / '.stacking_config.yaml'
DEFAULT_CONFIG = Path(__file__).parent / 'examples' / 'config_default.yaml'

def load_config():
    """Load configuration from YAML file"""
    if not CONFIG_FILE.exists():
        if DEFAULT_CONFIG.exists():
            shutil.copy(DEFAULT_CONFIG, CONFIG_FILE)
        else:
            # Create minimal default config
            default = {
                'sd_card_mode': 'ask',
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
                'keep_temp': False
            }
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(default, f)
    
    with open(CONFIG_FILE) as f:
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
# SD Card Detection
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
            sd_cards.append(dcim)
    
    return sd_cards

# ═══════════════════════════════════════════════════════════
# Image Analysis
# ═══════════════════════════════════════════════════════════

def get_image_timestamp(image_path):
    """Extract timestamp from image EXIF data"""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-s3', str(image_path)],
            capture_output=True,
            check=True,
            timeout=5
        )
        
        try:
            timestamp_str = result.stdout.decode('utf-8').strip()
        except UnicodeDecodeError:
            timestamp_str = result.stdout.decode('latin-1', errors='ignore').strip()
        
        if not timestamp_str:
            return None
            
        return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
    
    except:
        return None

def find_image_series(dcim_path, config, progress_callback=None):
    """Group images into series based on time threshold"""
    time_threshold = config.get('time_threshold', 30)
    min_images = config.get('min_images', 3)
    
    # Find all ORF files
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
        if progress_callback:
            progress_callback(i, total, f"Analyzing {img.name}")
        
        timestamp = get_image_timestamp(img)
        if timestamp:
            image_data.append((img, timestamp))
    
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
    
    # Add last series
    if len(current_series) >= min_images:
        series.append(current_series)
    
    return series

# ═══════════════════════════════════════════════════════════
# Thumbnail Generation
# ═══════════════════════════════════════════════════════════

def generate_thumbnail(image_path, size=(150, 100)):
    """
    Generate thumbnail from RAW or JPG image
    Uses first image of series
    """
    try:
        # Check for OOC JPG first (much faster!)
        jpg_path = image_path.with_suffix('.JPG')
        if not jpg_path.exists():
            jpg_path = image_path.with_suffix('.jpg')
        
        if jpg_path.exists():
            img = Image.open(jpg_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
        
        # Fallback: Extract thumbnail from RAW
        result = subprocess.run(
            ['exiftool', '-b', '-PreviewImage', str(image_path)],
            capture_output=True,
            check=True,
            timeout=10
        )
        
        if result.stdout:
            img = Image.open(io.BytesIO(result.stdout))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
        
        return create_placeholder_image(size)
    
    except Exception as e:
        logger.debug(f"Thumbnail generation failed for {image_path.name}: {e}")
        return create_placeholder_image(size)

def create_placeholder_image(size=(150, 100)):
    """Create a placeholder image"""
    img = Image.new('RGB', size, color='#555555')
    return img

# ═══════════════════════════════════════════════════════════
# Main GUI Application
# ═══════════════════════════════════════════════════════════

class StackingPipelineGUI:
    """Full GUI application for the stacking pipeline"""
    
    def __init__(self):
        self.config = load_config()
        self.series = []
        self.selected_indices = []
        self.dcim_path = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("OM-1 Macro Focus Stacking Pipeline v3.2")
        self.root.geometry("1400x900")
        
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Show SD card selection first
        self._show_sd_selection()
        
    def _show_sd_selection(self):
        """Show SD card selection screen"""
        frame = tk.Frame(self.root, bg='#ecf0f1')
        frame.grid(row=0, column=0, sticky='nsew')
        
        # Center content
        center = tk.Frame(frame, bg='#ecf0f1')
        center.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(
            center,
            text="🔬 OM-1 Stacking Pipeline",
            font=('Arial', 24, 'bold'),
            bg='#ecf0f1',
            fg='#2c3e50'
        ).pack(pady=20)
        
        tk.Label(
            center,
            text="Select SD Card / Source Folder",
            font=('Arial', 14),
            bg='#ecf0f1',
            fg='#7f8c8d'
        ).pack(pady=10)
        
        # Find SD cards
        sd_cards = find_sd_cards()
        
        if sd_cards:
            for card in sd_cards:
                btn = tk.Button(
                    center,
                    text=f"📁 {card}",
                    font=('Arial', 12),
                    bg='#3498db',
                    fg='white',
                    padx=30,
                    pady=15,
                    command=lambda c=card: self._select_source(c, frame)
                )
                btn.pack(pady=5, fill='x')
        
        # Manual selection
        tk.Button(
            center,
            text="📂 Browse for Folder...",
            font=('Arial', 12),
            bg='#95a5a6',
            fg='white',
            padx=30,
            pady=15,
            command=lambda: self._browse_folder(frame)
        ).pack(pady=20, fill='x')
        
    def _browse_folder(self, current_frame):
        """Browse for manual folder selection"""
        folder = filedialog.askdirectory(title="Select DCIM Folder")
        if folder:
            self._select_source(Path(folder), current_frame)
    
    def _select_source(self, path, current_frame):
        """Source selected, start analysis"""
        self.dcim_path = path
        current_frame.destroy()
        self._show_analysis_screen()
    
    def _show_analysis_screen(self):
        """Show analysis progress screen"""
        frame = tk.Frame(self.root, bg='#ecf0f1')
        frame.grid(row=0, column=0, sticky='nsew')
        
        center = tk.Frame(frame, bg='#ecf0f1')
        center.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(
            center,
            text="🔍 Analyzing Images...",
            font=('Arial', 18, 'bold'),
            bg='#ecf0f1',
            fg='#2c3e50'
        ).pack(pady=20)
        
        self.progress_label = tk.Label(
            center,
            text="Starting...",
            font=('Arial', 12),
            bg='#ecf0f1',
            fg='#7f8c8d'
        )
        self.progress_label.pack(pady=10)
        
        self.progress_bar = ttk.Progressbar(
            center,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)
        
        # Start analysis in background thread
        thread = threading.Thread(target=self._analyze_images, args=(frame,))
        thread.daemon = True
        thread.start()
    
    def _analyze_images(self, current_frame):
        """Analyze images in background"""
        def progress_callback(current, total, message):
            self.root.after(0, lambda: self.progress_label.config(text=message))
            self.root.after(0, lambda: self.progress_bar.config(value=(current/total)*100))
        
        try:
            self.series = find_image_series(self.dcim_path, self.config, progress_callback)
            
            if not self.series:
                self.root.after(0, lambda: messagebox.showerror(
                    "No Series Found",
                    "No image series found in the selected folder."
                ))
                self.root.after(0, self.root.quit)
                return
            
            # Show series selection
            self.root.after(0, lambda: self._show_series_selection(current_frame))
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Analysis failed: {e}"
            ))
            self.root.after(0, self.root.quit)
    
    def _show_series_selection(self, current_frame):
        """Show series selection with thumbnails in matrix layout"""
        current_frame.destroy()
        
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header
        header = tk.Frame(main_frame, bg='#2c3e50', height=70)
        header.grid(row=0, column=0, sticky='ew')
        
        tk.Label(
            header,
            text=f"🔬 Found {len(self.series)} Series - Select which to stack",
            font=('Arial', 16, 'bold'),
            bg='#2c3e50',
            fg='white',
            pady=20
        ).pack()
        
        # Scrollable canvas for series grid
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.grid(row=1, column=0, sticky='nsew')
        
        canvas = tk.Canvas(canvas_frame, bg='#ecf0f1')
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#ecf0f1')
        
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Generate series cards in grid (4 columns)
        self.checkbox_vars = []
        self.selected_indices = list(range(len(self.series)))  # All selected by default
        
        cols = 4
        for i, s in enumerate(self.series):
            row = i // cols
            col = i % cols
            self._create_series_card_compact(scrollable_frame, i, s, row, col)
        
        # Footer with buttons
        footer = tk.Frame(main_frame, bg='#34495e', height=90)
        footer.grid(row=2, column=0, sticky='ew')
        
        button_frame = tk.Frame(footer, bg='#34495e')
        button_frame.pack(pady=20)
        
        # Select All / None
        tk.Button(
            button_frame,
            text="Select All",
            command=self._select_all,
            font=('Arial', 11),
            bg='#3498db',
            fg='white',
            padx=15,
            pady=8
        ).pack(side='left', padx=5)
        
        tk.Button(
            button_frame,
            text="Select None",
            command=self._select_none,
            font=('Arial', 11),
            bg='#95a5a6',
            fg='white',
            padx=15,
            pady=8
        ).pack(side='left', padx=5)
        
        # Start button
        self.start_button = tk.Button(
            button_frame,
            text=f"▶ Start Stacking ({len(self.selected_indices)} selected)",
            command=self._start_stacking,
            font=('Arial', 13, 'bold'),
            bg='#27ae60',
            fg='white',
            padx=25,
            pady=10
        )
        self.start_button.pack(side='left', padx=15)
        
        # Cancel
        tk.Button(
            button_frame,
            text="Cancel",
            command=self.root.quit,
            font=('Arial', 11),
            bg='#e74c3c',
            fg='white',
            padx=15,
            pady=8
        ).pack(side='left', padx=5)
    
    def _create_series_card_compact(self, parent, index, series_data, row, col):
        """Create compact series card for grid layout"""
        
        # Card frame
        card = tk.Frame(
            parent,
            relief=tk.RAISED,
            borderwidth=1,
            bg='white',
            padx=10,
            pady=10
        )
        card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
        
        # Get FIRST image for preview
        img_path = series_data[0][0]
        
        # Generate thumbnail (smaller: 150x100)
        thumb = generate_thumbnail(img_path, size=(150, 100))
        photo = ImageTk.PhotoImage(thumb)
        
        # Image label
        img_label = tk.Label(card, image=photo, bg='white')
        img_label.image = photo  # Keep reference!
        img_label.pack()
        
        # Info
        first_time = series_data[0][1].strftime('%H:%M:%S')
        last_time = series_data[-1][1].strftime('%H:%M:%S')
        duration = (series_data[-1][1] - series_data[0][1]).total_seconds()
        
        tk.Label(
            card,
            text=f"Serie {index + 1}",
            font=('Arial', 11, 'bold'),
            bg='white'
        ).pack(pady=(5, 2))
        
        tk.Label(
            card,
            text=f"📸 {len(series_data)} images",
            font=('Arial', 9),
            bg='white'
        ).pack()
        
        tk.Label(
            card,
            text=f"{first_time} ({duration:.0f}s)",
            font=('Arial', 8),
            bg='white',
            fg='#7f8c8d'
        ).pack()
        
        # Checkbox
        var = tk.BooleanVar(value=True)
        self.checkbox_vars.append(var)
        
        check = tk.Checkbutton(
            card,
            text="Stack",
            variable=var,
            font=('Arial', 9),
            bg='white',
            activebackground='white',
            command=lambda idx=index, v=var: self._on_toggle(idx, v)
        )
        check.pack(pady=3)
    
    def _on_toggle(self, index, var):
        """Handle checkbox toggle"""
        if var.get():
            if index not in self.selected_indices:
                self.selected_indices.append(index)
        else:
            if index in self.selected_indices:
                self.selected_indices.remove(index)
        
        # Update button text
        self.start_button.config(
            text=f"▶ Start Stacking ({len(self.selected_indices)} selected)"
        )
    
    def _select_all(self):
        """Select all series"""
        self.selected_indices = list(range(len(self.series)))
        for var in self.checkbox_vars:
            var.set(True)
        self.start_button.config(
            text=f"▶ Start Stacking ({len(self.selected_indices)} selected)"
        )
    
    def _select_none(self):
        """Deselect all series"""
        self.selected_indices = []
        for var in self.checkbox_vars:
            var.set(False)
        self.start_button.config(
            text=f"▶ Start Stacking (0 selected)"
        )
    
    def _start_stacking(self):
        """Start the stacking process"""
        if not self.selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one series to stack.")
            return
        
        # Get selected series
        selected_series = [self.series[i] for i in sorted(self.selected_indices)]
        
        # Close current window and start processing
        self.root.destroy()
        
        # Run processing (this will be in a new window or terminal output)
        self._run_processing(selected_series)
    
    def _run_processing(self, selected_series):
        """Run the actual stacking processing"""
        stats = {
            'series_found': len(self.series),
            'series_selected': len(selected_series),
            'images_processed': 0,
            'ooc_jpgs': 0,
            'conversions': 0,
            'successful': 0,
            'failed': 0,
            'total_time': 0
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting processing of {len(selected_series)} series")
        logger.info(f"{'='*60}\n")
        
        for i, series_data in enumerate(selected_series, 1):
            stats['ooc_jpgs'] = 0
            stats['conversions'] = 0
            
            process_series(series_data, i, len(selected_series), self.config, stats)
        
        # Print final statistics
        print_statistics(stats)
        
        messagebox.showinfo(
            "Processing Complete",
            f"Successfully created {stats['successful']} stacks!\n"
            f"Failed: {stats['failed']}\n"
            f"Total time: {stats['total_time']:.1f}s"
        )
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

# ═══════════════════════════════════════════════════════════
# Image Preparation & Stacking (same as v3.1)
# ═══════════════════════════════════════════════════════════

def convert_raw_to_jpg(raw_file, output_dir, config):
    """Convert ORF to JPG"""
    output_file = output_dir / f"{raw_file.stem}.jpg"
    quality = config.get('jpg_quality', 95)
    converter = config.get('jpg_converter', 'imagemagick')
    
    try:
        if converter == 'imagemagick':
            subprocess.run([
                'magick',
                str(raw_file),
                '-quality', str(quality),
                str(output_file)
            ], check=True, capture_output=True)
        elif converter == 'dcraw':
            dcraw_process = subprocess.Popen([
                'dcraw', '-c', '-w', '-q', '3', '-6', str(raw_file)
            ], stdout=subprocess.PIPE)
            
            subprocess.run([
                'magick', '-', '-quality', str(quality), str(output_file)
            ], stdin=dcraw_process.stdout, check=True, capture_output=True)
            
            dcraw_process.wait()
        else:
            logger.error(f"Unknown converter: {converter}")
            return None
        
        return output_file if output_file.exists() else None
    except:
        return None

def prepare_images_for_stacking(series_data, temp_dir, config, stats):
    """Prepare images: use OOC JPG or convert ORF"""
    prepared_images = []
    
    for orf_file, timestamp in series_data:
        jpg_ooc = orf_file.with_suffix('.JPG')
        if not jpg_ooc.exists():
            jpg_ooc = orf_file.with_suffix('.jpg')
        
        if jpg_ooc.exists():
            dest = temp_dir / jpg_ooc.name
            shutil.copy2(jpg_ooc, dest)
            prepared_images.append(dest)
            stats['ooc_jpgs'] += 1
            logger.debug(f"✓ Using OOC JPG: {jpg_ooc.name}")
        else:
            jpg_converted = convert_raw_to_jpg(orf_file, temp_dir, config)
            if jpg_converted:
                prepared_images.append(jpg_converted)
                stats['conversions'] += 1
                logger.debug(f"⚙ Converted: {orf_file.name}")
    
    return sorted(prepared_images)

def stack_images_helicon(image_dir, output_file, config):
    """Stack with Helicon Focus"""
    helicon_binary = Path(config['helicon_binary']).expanduser()
    
    if not helicon_binary.exists():
        logger.error(f"Helicon binary not found: {helicon_binary}")
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
        logger.info(f"Stacking with Helicon Focus (Method {method})...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and output_file.exists()
    except Exception as e:
        logger.error(f"Helicon failed: {e}")
        return False

def add_metadata(output_file, series_info, config):
    """Add EXIF metadata"""
    try:
        subprocess.run([
            'exiftool',
            '-overwrite_original',
            '-charset', 'filename=utf8',
            f'-ImageDescription=Focus stacked from {series_info["num_images"]} images',
            f'-Software=OM-1 Stacking Pipeline v3.2',
            f'-DateTimeOriginal={series_info["first_timestamp"]}',
            str(output_file)
        ], capture_output=True, check=True)
        return True
    except:
        return False

def notify_completion(filename):
    """macOS notification"""
    try:
        subprocess.run([
            'osascript', '-e',
            f'display notification "Created {filename}" with title "Stacking Complete"'
        ], check=False, capture_output=True)
        subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                      check=False, capture_output=True)
    except:
        pass

def process_series(series_data, series_num, total_series, config, stats):
    """Process one series"""
    start_time = time.time()
    first_timestamp = series_data[0][1]
    
    output_dir = Path(config['output_dir']).expanduser()
    temp_dir = Path(config['temp_dir']).expanduser() / f"series_{series_num}"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Serie {series_num}/{total_series}: {len(series_data)} images")
    logger.info(f"{'='*60}")
    
    try:
        prepared_images = prepare_images_for_stacking(series_data, temp_dir, config, stats)
        
        if not prepared_images:
            logger.error("No images prepared!")
            stats['failed'] += 1
            return False
        
        stats['images_processed'] += len(prepared_images)
        logger.info(f"✓ Prepared: {stats['ooc_jpgs']} OOC JPGs, {stats['conversions']} conversions")
        
        timestamp_str = first_timestamp.strftime('%Y%m%d_%H%M%S')
        output_format = config.get('output_format', 'jpg')
        output_file = output_dir / f"stack_{timestamp_str}.{output_format}"
        
        success = stack_images_helicon(temp_dir, output_file, config)
        
        if success and output_file.exists():
            series_info = {
                'num_images': len(prepared_images),
                'first_timestamp': first_timestamp.strftime('%Y:%m:%d %H:%M:%S')
            }
            add_metadata(output_file, series_info, config)
            
            elapsed = time.time() - start_time
            logger.info(f"✓ Stack created: {output_file.name} ({elapsed:.1f}s)")
            stats['successful'] += 1
            stats['total_time'] += elapsed
            
            notify_completion(output_file.name)
            return True
        else:
            logger.error("Stacking failed!")
            stats['failed'] += 1
            return False
    
    except Exception as e:
        logger.error(f"Error: {e}")
        stats['failed'] += 1
        return False
    
    finally:
        if not config.get('keep_temp', False):
            shutil.rmtree(temp_dir, ignore_errors=True)

def print_statistics(stats):
    """Print final stats"""
    print("\n" + "="*60)
    print("STACKING SUMMARY")
    print("="*60)
    print(f"Series found:       {stats['series_found']}")
    print(f"Series selected:    {stats['series_selected']}")
    print(f"Images processed:   {stats['images_processed']}")
    print(f"  - OOC JPGs:       {stats['ooc_jpgs']}")
    print(f"  - Conversions:    {stats['conversions']}")
    print(f"Stacks created:     {stats['successful']}")
    print(f"Failed:             {stats['failed']}")
    
    if stats['successful'] > 0:
        total_min = stats['total_time'] / 60
        avg_sec = stats['total_time'] / stats['successful']
        print(f"Total time:         {stats['total_time']:.1f}s ({total_min:.1f}m)")
        print(f"Avg time/stack:     {avg_sec:.1f}s")
    
    print("="*60)

# ═══════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════

def main():
    """Main entry point - full GUI mode"""
    app = StackingPipelineGUI()
    app.run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", str(e))
        sys.exit(1)
