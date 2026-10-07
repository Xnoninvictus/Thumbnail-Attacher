#!/usr/bin/env python3
"""
Batch-add thumbnails to ALL video files in this folder (no detection).
If a video already has a thumbnail, the old one is removed and replaced.

Requires: ffmpeg and ffprobe.
"""

import subprocess
import json
import os
import sys
import shutil
import tempfile
from pathlib import Path

# --- Configuration ---
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv', '.m4v'}
THUMBNAIL_TIMESTAMP = 1
THUMBNAIL_FORMAT = 'jpg'
THUMBNAIL_QUALITY = 5
RECURSIVE = False

FFMPEG_PATH  = None
FFPROBE_PATH = None

SCRIPT_DIR = Path(__file__).resolve().parent

IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')


# --------------------------------------------------------------------------
# Locate ffmpeg / ffprobe
# --------------------------------------------------------------------------
def _find_tool(name, hard_coded):
    exe = f"{name}.exe" if os.name == 'nt' else name
    if hard_coded and Path(hard_coded).is_file():
        return hard_coded
    local = SCRIPT_DIR / exe
    if local.is_file():
        return str(local)
    if os.name == 'nt':
        for c in [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / exe,
            Path("C:/ffmpeg/bin") / exe,
            Path("C:/Program Files/ffmpeg/bin") / exe,
            Path("C:/ProgramData/chocolatey/bin") / exe,
            Path.home() / "scoop" / "shims" / exe,
        ]:
            try:
                if c.is_file():
                    return str(c)
            except OSError:
                pass
    return shutil.which(name)


FFMPEG  = _find_tool("ffmpeg",  FFMPEG_PATH)
FFPROBE = _find_tool("ffprobe", FFPROBE_PATH)


def check_dependencies():
    missing = [n for n, p in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)) if not p]
    if missing:
        print(" ERROR: Could not find " + " and ".join(missing))
        print(" Install with:  winget install Gyan.FFmpeg -s winget")
        print(" Or drop ffmpeg.exe / ffprobe.exe next to this script.")
        if os.name == 'nt':
            input("Press Enter to close...")
        sys.exit(1)


# --------------------------------------------------------------------------
# Find existing thumbnails (so we can remove them)
# --------------------------------------------------------------------------
def find_existing_thumbnails(video_path):
    """
    Return list of stream indices that look like embedded thumbnails:
      - streams with attached_pic disposition  (MP4/MOV/M4V)
      - image attachment streams               (MKV/WebM cover.jpg)
    """
    cmd = [FFPROBE, '-v', 'quiet', '-print_format', 'json',
           '-show_streams', video_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(r.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []

    found = []
    for s in info.get('streams', []):
        idx = s.get('index')
        # 1. attached_pic disposition
        if s.get('disposition', {}).get('attached_pic') == 1:
            found.append(idx)
            continue
        # 2. MKV / WebM image attachment
        if s.get('codec_type') == 'attachment':
            tags = s.get('tags', {}) or {}
            mime = (tags.get('mimetype') or '').lower()
            fname = (tags.get('filename') or '').lower()
            if 'image' in mime or fname.endswith(IMAGE_EXTS):
                found.append(idx)
    return found


# --------------------------------------------------------------------------
# Core operations
# --------------------------------------------------------------------------
def extract_frame(video_path, output_path, timestamp=THUMBNAIL_TIMESTAMP):
    cmd = [FFMPEG, '-ss', str(timestamp), '-i', video_path,
           '-vframes', '1', '-q:v', str(THUMBNAIL_QUALITY), '-y', output_path]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return os.path.exists(output_path)
    except subprocess.CalledProcessError:
        cmd[2] = '1'
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return os.path.exists(output_path)
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Frame extraction failed: {e}")
            return False


def embed_thumbnail(video_path, image_path):
    """Remove any existing thumbnail(s) and embed the new one."""
    ext = Path(video_path).suffix.lower()
    old_thumbs = find_existing_thumbnails(video_path)
    if old_thumbs:
        print(f"  🗑️  Removing {len(old_thumbs)} existing thumbnail stream(s) "
              f"(indices: {old_thumbs})...")

    if ext == '.mkv':
        temp_output = video_path + '.tmp_thumb.mkv'
        cmd = [FFMPEG, '-i', video_path, '-map', '0']
        for idx in old_thumbs:
            cmd += ['-map', f'-0:{idx}']
        cmd += [
            '-attach', image_path,
            '-metadata:s:t', 'mimetype=image/jpeg',
            '-metadata:s:t', 'filename=cover.jpg',
            '-c', 'copy',
            '-y', temp_output
        ]
    else:
        temp_output = video_path + '.tmp_thumb.mp4'
        cmd = [FFMPEG, '-i', video_path, '-i', image_path, '-map', '0']
        for idx in old_thumbs:
            cmd += ['-map', f'-0:{idx}']
        cmd += [
            '-map', '1',
            '-c', 'copy',
            '-c:v:1', 'mjpeg',
            '-disposition:v:1', 'attached_pic',
            '-y', temp_output
        ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        os.replace(temp_output, video_path)
        return True
    except subprocess.CalledProcessError as e:
        # Show the real error message so debugging is possible
        err = e.stderr.decode(errors='replace') if e.stderr else str(e)
        print(f"  ❌ Embedding failed: {err.strip().splitlines()[-1] if err else e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return False


def process_video(video_path):
    name = Path(video_path).name
    print(f"Processing: {name}")

    with tempfile.NamedTemporaryFile(suffix=f'.{THUMBNAIL_FORMAT}',
                                     delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if extract_frame(video_path, tmp_path):
            print("  🖼️  Frame extracted. Embedding...")
            if embed_thumbnail(video_path, tmp_path):
                print("  ✅ Thumbnail added successfully.")
            else:
                print("  ❌ Failed to embed thumbnail.")
        else:
            print("  ❌ Could not extract a frame.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def collect_videos(folder):
    if RECURSIVE:
        return [f for f in folder.rglob('*')
                if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]
    return [f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]


def main():
    check_dependencies()

    target = Path(sys.argv[1]).resolve() if len(sys.argv) >= 2 else SCRIPT_DIR

    print(f"Using ffmpeg : {FFMPEG}")
    print(f"Using ffprobe: {FFPROBE}")
    print(f"Working dir  : {target}\n")

    if target.is_file():
        if target.suffix.lower() in VIDEO_EXTENSIONS:
            process_video(str(target))
    elif target.is_dir():
        files = collect_videos(target)
        if not files:
            print("No video files found.")
        else:
            print(f"Found {len(files)} video file(s).\n")
            for f in files:
                process_video(str(f))
                print()
    else:
        print(f"Path not found: {target}")
        sys.exit(1)

    print("Done.")
    if os.name == 'nt' and len(sys.argv) < 2:
        input("\nPress Enter to close...")


if __name__ == '__main__':
    main()
