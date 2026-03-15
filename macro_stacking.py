#!/usr/bin/env python3
"""
OM-1 Macro Focus Stacking Pipeline v3.0
Automated workflow: SD Card → Series Detection → Focus Stacking → Output

NEW in v3.0:
- Helicon Focus CLI support
- Smart JPG detection (prefer OOC JPG over RAW conversion)
- Faster workflow with JPG-based stacking
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

# Progress bar & interactive menu
from tqdm import tqdm
import inquirer

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
            logging.info(f"Created config file: {CONFIG_FILE}")
        else:
            logging.error(f"No config file found at {CONFIG_FILE}")
            sys.exit(1)
    
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

def select_sd_card(config):
    """Select SD card based on config mode"""
    mode = config.get('sd_card_mode', 'ask')
    
    if mode == 'manual':
        watch_dir = Path(config['watch_dir']).expanduser()
        if not watch_dir.exists():
            logger.error(f"Manual watch_dir not found: {watch_dir}")
            sys.exit(1)
        return watch_dir
    
    sd_cards = find_sd_cards()
    
    if not sd_cards:
        logger.error("No SD card found!")
        sys.exit(1)
    
    if mode == 'first':
        return sd_cards[0]
    
    if mode == 'ask':
        if len(sd_cards) == 1:
            return sd_cards[0]
        
        questions = [
            inquirer.List('sd_card',
                message="Select SD card",
                choices=[str(card) for card in sd_cards]
            )
        ]
        answer = inquirer.prompt(questions)
        return Path(answer['sd_card'])

# ═══════════════════════════════════════════════════════════
# Image Analysis
# ═══════════════════════════════════════════════════════════

def get_image_timestamp(image_path):
    """Extract timestamp from image EXIF data"""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-s3', str(image_path)],
            capture_output=True,
            check=True
        )
        
        # Robust decoding
        try:
            timestamp_str = result.stdout.decode('utf-8').strip()
        except UnicodeDecodeError:
            timestamp_str = result.stdout.decode('latin-1', errors='ignore').strip()
        
        if not timestamp_str:
            return None
            
        return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
    
    except subprocess.CalledProcessError:
        logger.warning(f"exiftool failed for {image_path.name}")
        return None
    except ValueError:
        logger.warning(f"Invalid timestamp format in {image_path.name}")
        return None
    except Exception as e:
        logger.warning(f"Could not read timestamp from {image_path.name}: {e}")
        return None

def find_image_series(dcim_path, config):
    """Group images into series based on time threshold"""
    time_threshold = config.get('time_threshold', 30)
    min_images = config.get('min_images', 3)
    
    # Find all ORF files (we'll check for JPGs later)
    images = []
    for root, dirs, files in os.walk(dcim_path):
        for file in files:
            if file.upper().endswith('.ORF'):
                images.append(Path(root) / file)
    
    if not images:
        logger.warning("No ORF files found!")
        return []
    
    logger.info(f"Found {len(images)} RAW images, analyzing timestamps...")
    
    # Get timestamps
    image_data = []
    for img in tqdm(images, desc="Reading EXIF data", unit="img"):
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
# Interactive Series Selection
# ═══════════════════════════════════════════════════════════

def select_series_to_stack(series):
    """Interactive menu to select which series to stack"""
    if not series:
        return []
    
    # Build choices
    choices = []
    for i, s in enumerate(series, 1):
        first_time = s[0][1].strftime('%H:%M:%S')
        last_time = s[-1][1].strftime('%H:%M:%S')
        choice_text = f"Serie {i}: {len(s)} Bilder ({first_time} - {last_time})"
        choices.append(choice_text)
    
    # Interactive selection
    questions = [
        inquirer.Checkbox('selected',
            message="Welche Serien stacken? (Space=auswählen, Enter=bestätigen)",
            choices=choices,
            default=choices  # All selected by default
        )
    ]
    
    answers = inquirer.prompt(questions)
    
    if not answers or not answers['selected']:
        logger.info("Keine Serien ausgewählt, abgebrochen.")
        return []
    
    # Map back to series indices
    selected_indices = [choices.index(s) for s in answers['selected']]
    return [series[i] for i in selected_indices]

# ═══════════════════════════════════════════════════════════
# Smart Image Preparation (NEW in v3.0)
# ═══════════════════════════════════════════════════════════

def convert_raw_to_jpg(raw_file, output_dir, config):
    """Convert ORF to JPG using ImageMagick or dcraw"""
    output_file = output_dir / f"{raw_file.stem}.jpg"
    quality = config.get('jpg_quality', 95)
    converter = config.get('jpg_converter', 'imagemagick')
    
    try:
        if converter == 'imagemagick':
            # Fast conversion with ImageMagick
            subprocess.run([
                'magick',
                str(raw_file),
                '-quality', str(quality),
                str(output_file)
            ], check=True, capture_output=True)
            
        elif converter == 'dcraw':
            # dcraw → stdout → ImageMagick
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
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed for {raw_file.name}: {e}")
        return None

def prepare_images_for_stacking(series_data, temp_dir, config, stats):
    """
    Smart image preparation:
    1. Check if OOC JPG exists
    2. If yes → copy JPG
    3. If no → convert ORF to JPG
    """
    prepared_images = []
    
    for orf_file, timestamp in tqdm(series_data, desc="Preparing images", unit="img"):
        # Check for OOC JPG (same name, different extension)
        jpg_ooc = orf_file.with_suffix('.JPG')
        if not jpg_ooc.exists():
            jpg_ooc = orf_file.with_suffix('.jpg')  # Try lowercase
        
        if jpg_ooc.exists():
            # Use OOC JPG directly
            dest = temp_dir / jpg_ooc.name
            shutil.copy2(jpg_ooc, dest)
            prepared_images.append(dest)
            stats['ooc_jpgs'] += 1
            logger.debug(f"✓ Using OOC JPG: {jpg_ooc.name}")
        else:
            # Convert ORF to JPG
            jpg_converted = convert_raw_to_jpg(orf_file, temp_dir, config)
            if jpg_converted:
                prepared_images.append(jpg_converted)
                stats['conversions'] += 1
                logger.debug(f"⚙ Converted: {orf_file.name} → {jpg_converted.name}")
            else:
                logger.warning(f"Failed to prepare: {orf_file.name}")
    
    return sorted(prepared_images)

# ═══════════════════════════════════════════════════════════
# Focus Stacking - Helicon Focus (NEW in v3.0)
# ═══════════════════════════════════════════════════════════

def stack_images_helicon(image_dir, output_file, config):
    """Stack images using Helicon Focus CLI"""
    helicon_binary = Path(config['helicon_binary']).expanduser()
    
    if not helicon_binary.exists():
        logger.error(f"Helicon binary not found: {helicon_binary}")
        return False
    
    # Method mapping: A=0, B=1, C=2
    method_map = {'A': 0, 'B': 1, 'C': 2}
    method = config.get('helicon_method', 'C')
    method_code = method_map.get(method.upper(), 2)
    
    # Build command
    cmd = [
        str(helicon_binary),
        '-silent',
        f'-mp:{method_code}',
        f'-rp:{config.get("helicon_radius", 8)}',
        f'-sp:{config.get("helicon_smoothing", 4)}',
        f'-save:{output_file}',
        str(image_dir)  # Helicon processes all images in folder
    ]
    
    # Optional: JPEG quality
    if str(output_file).lower().endswith('.jpg'):
        cmd.insert(2, f'-j:{config.get("output_quality", 95)}')
    
    # Optional: Save depth map
    if config.get('helicon_save_depthmap', False):
        cmd.insert(2, '-dmap')
    
    # Optional: No progress bar
    if not config.get('verbose', False):
        cmd.insert(2, '-noprogress')
    
    try:
        logger.info(f"Stacking with Helicon Focus (Method {method})...")
        
        if config.get('debug', False):
            logger.debug(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and output_file.exists():
            return True
        else:
            logger.error(f"Helicon stacking failed (return code {result.returncode})")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Helicon exception: {e}")
        return False

# ═══════════════════════════════════════════════════════════
# Focus Stacking - focus-stack (Fallback)
# ═══════════════════════════════════════════════════════════

def stack_images_focus_stack(image_files, output_file, config):
    """Stack images using focus-stack (original implementation)"""
    stacker_binary = Path(config['stacker_binary']).expanduser()
    
    if not stacker_binary.exists():
        logger.error(f"Stacker binary not found: {stacker_binary}")
        return False
    
    # Build command
    cmd = [
        str(stacker_binary),
        f'--output={output_file}',
        f'--consistency={config.get("consistency", 2)}',
        f'--denoise={config.get("denoise", 1.0)}'
    ]
    
    # Performance options
    if not config.get('use_opencl', False):
        cmd.append('--no-opencl')
    
    if config.get('threads', 0) > 0:
        cmd.append(f'--threads={config.get("threads")}')
    
    # Output options
    if config.get('save_steps', False):
        cmd.append('--save-steps')
    
    if str(output_file).lower().endswith('.jpg'):
        cmd.append(f'--jpgquality={config.get("output_quality", 95)}')
    
    if config.get('verbose', False):
        cmd.append('--verbose')
    
    # Input files
    cmd.extend([str(f) for f in image_files])
    
    try:
        logger.info(f"Stacking with focus-stack...")
        
        if config.get('debug', False):
            logger.debug(f"Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in process.stdout:
            line = line.strip()
            if line and config.get('verbose', False):
                logger.info(f"  {line}")
        
        process.wait()
        
        if process.returncode == 0 and output_file.exists():
            return True
        else:
            logger.error(f"Stacking failed (return code {process.returncode})")
            return False
            
    except Exception as e:
        logger.error(f"Stacking exception: {e}")
        return False

# ═══════════════════════════════════════════════════════════
# Metadata
# ═══════════════════════════════════════════════════════════

def add_metadata(output_file, series_info, config):
    """Add EXIF metadata to stacked image"""
    num_images = series_info['num_images']
    first_time = series_info['first_timestamp']
    stacker = config.get('stacker', 'unknown')
    
    try:
        subprocess.run([
            'exiftool',
            '-overwrite_original',
            '-charset', 'filename=utf8',
            f'-ImageDescription=Focus stacked from {num_images} images using {stacker}',
            f'-Software=OM-1 Stacking Pipeline v3.0',
            f'-DateTimeOriginal={first_time}',
            f'-Artist=Oliver Kuemmel',
            str(output_file)
        ], capture_output=True, check=True)
        
        logger.debug(f"Metadata added to {output_file.name}")
        return True
        
    except Exception as e:
        logger.warning(f"Could not add metadata: {e}")
        return False

# ═══════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════

def notify_completion(filename):
    """Send macOS notification"""
    try:
        subprocess.run([
            'osascript', '-e',
            f'display notification "Created {filename}" with title "Stacking Complete"'
        ], check=False, capture_output=True)
        subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                      check=False, capture_output=True)
    except:
        pass

# ═══════════════════════════════════════════════════════════
# Main Processing Pipeline
# ═══════════════════════════════════════════════════════════

def process_series(series_data, series_num, total_series, config, stats):
    """Process a single image series"""
    start_time = time.time()
    
    # Extract info
    first_timestamp = series_data[0][1]
    
    # Setup directories
    output_dir = Path(config['output_dir']).expanduser()
    temp_dir = Path(config['temp_dir']).expanduser() / f"series_{series_num}"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Serie {series_num}/{total_series}: {len(series_data)} images")
    logger.info(f"{'='*60}")
    
    try:
        # Smart image preparation (NEW in v3.0)
        prepared_images = prepare_images_for_stacking(series_data, temp_dir, config, stats)
        
        if not prepared_images:
            logger.error("No images prepared for stacking!")
            stats['failed'] += 1
            return False
        
        stats['images_processed'] += len(prepared_images)
        
        logger.info(f"✓ Prepared: {stats['ooc_jpgs']} OOC JPGs, {stats['conversions']} conversions")
        
        # Stack images
        timestamp_str = first_timestamp.strftime('%Y%m%d_%H%M%S')
        output_format = config.get('output_format', 'jpg')
        output_file = output_dir / f"stack_{timestamp_str}.{output_format}"
        
        # Choose stacker
        stacker = config.get('stacker', 'helicon').lower()
        
        if stacker == 'helicon':
            success = stack_images_helicon(temp_dir, output_file, config)
        else:
            success = stack_images_focus_stack(prepared_images, output_file, config)
        
        if success and output_file.exists():
            # Add metadata
            series_info = {
                'num_images': len(prepared_images),
                'first_timestamp': first_timestamp.strftime('%Y:%m:%d %H:%M:%S')
            }
            add_metadata(output_file, series_info, config)
            
            elapsed = time.time() - start_time
            logger.info(f"✓ Stack created: {output_file.name} ({elapsed:.1f}s)")
            stats['successful'] += 1
            stats['total_time'] += elapsed
            
            # macOS notification
            notify_completion(output_file.name)
            
            return True
        else:
            logger.error("Stacking failed!")
            stats['failed'] += 1
            return False
    
    except Exception as e:
        logger.error(f"Error processing series: {e}")
        stats['failed'] += 1
        return False
    
    finally:
        # Cleanup temp directory
        if not config.get('keep_temp', False):
            shutil.rmtree(temp_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════
# Statistics
# ═══════════════════════════════════════════════════════════

def print_statistics(stats):
    """Print final statistics"""
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
    """Main pipeline execution"""
    print("\n🔬 OM-1 Macro Focus Stacking Pipeline v3.0 (Helicon Edition)\n")
    
    # Load config
    config = load_config()
    
    # Statistics
    stats = {
        'series_found': 0,
        'series_selected': 0,
        'images_processed': 0,
        'ooc_jpgs': 0,
        'conversions': 0,
        'successful': 0,
        'failed': 0,
        'total_time': 0
    }
    
    # Select SD card
    dcim_path = select_sd_card(config)
    logger.info(f"Using: {dcim_path}")
    
    # Find series
    series = find_image_series(dcim_path, config)
    stats['series_found'] = len(series)
    
    if not series:
        logger.warning("No image series found!")
        return
    
    logger.info(f"\nFound {len(series)} series")
    
    # Dry run mode
    if config.get('dry_run', False):
        logger.info("\n[DRY RUN MODE - No actual stacking]")
        for i, s in enumerate(series, 1):
            first = s[0][1].strftime('%H:%M:%S')
            last = s[-1][1].strftime('%H:%M:%S')
            logger.info(f"Serie {i}: {len(s)} images ({first} - {last})")
        return
    
    # Interactive selection
    selected_series = select_series_to_stack(series)
    stats['series_selected'] = len(selected_series)
    
    if not selected_series:
        return
    
    # Process selected series
    for i, series_data in enumerate(selected_series, 1):
        process_series(series_data, i, len(selected_series), config, stats)
    
    # Print statistics
    print_statistics(stats)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
