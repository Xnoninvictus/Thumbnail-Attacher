# Video Thumbnail Attacher

A pair of single-file Python utilities that batch-embed cover images (thumbnails) into video files using `ffmpeg` and `ffprobe`. They differ only in policy:

- **`TAlacking.py`** — *safe mode.* Detects existing embedded thumbnails and only processes videos that don't already have one. Everything else is skipped untouched.
- **`TAall.py`** — *force mode.* Processes every video, removing any existing thumbnail streams and replacing them with a fresh frame grabbed at a configured timestamp.

Both scripts work on MP4, MKV, MOV, AVI, WebM, FLV, WMV, and M4V — and handle the two different ways thumbnails are stored: an `attached_pic` video stream (MP4/MOV/M4V style) and an image *attachment* stream (MKV/WebM `cover.jpg` style).

---

## Table of Contents

1. [What They Do](#what-they-do)
2. [Which Script Should I Use?](#which-script-should-i-use)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Configuration Options](#configuration-options)
7. [How the Code Works](#how-the-code-works)
8. [Thumbnail Detection Logic](#thumbnail-detection-logic)
9. [Embedding Logic](#embedding-logic)
10. [Building a Standalone Executable](#building-a-standalone-executable)
11. [Troubleshooting](#troubleshooting)
12. [Known Limitations](#known-limitations)
13. [Extending the Scripts](#extending-the-scripts)
14. [License](#license)

---

## What They Do

At their core, both scripts:

1. **Locate `ffmpeg` and `ffprobe`** — either from a hard-coded path, next to the script, in common install locations (WinGet, Chocolatey, Scoop, `C:\ffmpeg\bin`, etc.), or on `PATH`.
2. **Enumerate video files** in a target folder (or a single file passed as an argument).
3. **Grab a single frame** from each video at a configured timestamp using `ffmpeg`.
4. **Embed that frame** into the video as a thumbnail — the right way for the container format (attached_pic for MP4-family, image attachment for MKV).
5. **Replace the original file** atomically with `os.replace()` after the operation succeeds.
6. **Clean up** temporary files — even if the process is interrupted.

The result: Windows Explorer, macOS Finder, and Linux file managers all show a real cover image on the video file instead of a generic icon or an auto-generated frame.

---

## Which Script Should I Use?

| | `only_to_without_thumbnails.py` | `to_all.py` |
|---|---|---|
| **Behavior** | Skips videos that already have a thumbnail | Processes every video |
| **Re-encodes?** | No — stream copy | No — stream copy |
| **Removes existing thumbs?** | No | Yes |
| **Use case** | First-time pass over a mixed library | Force-refresh every thumbnail |
| **Risk** | Very low — untouched files stay untouched | Slightly higher — every file is rewritten |
| **Detects existing thumbnail?** | Yes (to decide whether to skip) | Yes (to know what to remove) |

If you're running this for the first time on a large library, start with **`only_to_without_thumbnails.py`**. If you later decide you don't like the chosen timestamp and want to regenerate everything, run **`to_all.py`**.

---

## Requirements

- **Python 3.7+** (standard library only — no `pip install` needed).
- **`ffmpeg`** and **`ffprobe`** available on the system. Either:
  - On `PATH`, **or**
  - In the same folder as the script, **or**
  - In a standard install location (auto-detected on Windows), **or**
  - Hard-coded in the script via `FFMPEG_PATH` / `FFPROBE_PATH`.

### Installing FFmpeg

| OS | Command |
|----|---------|
| Windows (WinGet) | `winget install Gyan.FFmpeg -s winget` |
| Windows (Chocolatey) | `choco install ffmpeg` |
| Windows (Scoop) | `scoop install ffmpeg` |
| macOS (Homebrew) | `brew install ffmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` |
| Arch | `sudo pacman -S ffmpeg` |

Alternatively, download a static build from [ffmpeg.org](https://ffmpeg.org/download.html) and drop `ffmpeg.exe` / `ffprobe.exe` next to the script.

---

## Installation

No install step. Just save the script(s) wherever you want to run them.

```bash
# Optional: make executable on Linux/macOS
chmod +x Thumbnail_Attacher_only_to_without_thumbnails.py
chmod +x Thumbnail_Attacher_to_all.py
```

If you want to run them from anywhere:

```bash
sudo cp Thumbnail_Attacher_only_to_without_thumbnails.py /usr/local/bin/thumb-safe
sudo cp Thumbnail_Attacher_to_all.py /usr/local/bin/thumb-force
```

---

## Usage

### Default behavior — process the script's own folder

Drop the script into a folder full of videos and run it:

```bash
python3 Thumbnail_Attacher_only_to_without_thumbnails.py
```

It will process every video file in that same folder. On Windows, if you double-click the script (or run it with no args), the window stays open at the end with `Press Enter to close...` so you can read the output.

### Process a specific folder

```bash
python3 Thumbnail_Attacher_only_to_without_thumbnails.py "D:\Videos"
```

```bash
python3 Thumbnail_Attacher_to_all.py ~/Movies/2024
```

### Process a single file

```bash
python3 Thumbnail_Attacher_to_all.py ./clip.mp4
```

### Example output

```
Using ffmpeg : C:\ffmpeg\bin\ffmpeg.exe
Using ffprobe: C:\ffmpeg\bin\ffprobe.exe
Working dir  : D:\Videos

Found 12 video file(s).

Skipping: intro.mp4
  ✅ Already has an embedded thumbnail (attached_pic (stream #2 mjpeg))

Processing: lecture_01.mp4
  ℹ️  no embedded thumbnail found — generating one.
  🖼️  Frame extracted. Embedding...
  ✅ Thumbnail added successfully.

Processing: travel.mkv
  ℹ️  no embedded thumbnail found — generating one.
  🖼️  Frame extracted. Embedding...
  ✅ Thumbnail added successfully.

Done.
```

For `to_all.py` you'll also see lines like:

```
  🗑️  Removing 1 existing thumbnail stream(s) (indices: [2])...
```

---

## Configuration Options

Both scripts expose the same config block at the top. Edit these constants to change behavior:

```python
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv', '.m4v'}
THUMBNAIL_TIMESTAMP = 1
THUMBNAIL_FORMAT = 'jpg'
THUMBNAIL_QUALITY = 5
RECURSIVE = False
```

| Option | Default | Meaning |
|--------|---------|---------|
| `VIDEO_EXTENSIONS` | 8 common formats | Set of file extensions to scan. Add `.ts`, `.m2ts`, `.ogv`, etc. if you need them. |
| `THUMBNAIL_TIMESTAMP` | `1` (second) | Where in the video to grab the frame. `1` avoids the very first frame, which is often a black fade-in. Use `5` or `10` for talking-head content where the first second is a title card. |
| `THUMBNAIL_FORMAT` | `'jpg'` | Temporary frame format. `jpg` is smallest; `png` preserves detail better but is larger. `webp` works if your ffmpeg build supports it. |
| `THUMBNAIL_QUALITY` | `5` | For JPEG: `1` = best, `31` = worst. `5` is a good balance. |
| `RECURSIVE` | `False` | If `True`, walks subfolders (`rglob`). If `False`, only the top level of the target folder. |
| `FFMPEG_PATH` | `None` | Hard-code an absolute path if auto-detection fails. |
| `FFPROBE_PATH` | `None` | Same for ffprobe. |

The "only" script also has:

| Option | Default | Meaning |
|--------|---------|---------|
| `VERBOSE` | `True` | Print *why* a file was skipped (which detection method matched). |
| `SKIP_IF_EXPLORER_CACHE` | `False` | Reserved — see note below. Leave `False` normally. |

> **About `SKIP_IF_EXPLORER_CACHE`:** Windows Explorer sometimes shows a thumbnail even when the video file has none embedded — it generates one on the fly from the video's first frame. Setting this to `True` would (in a future version) attempt to distinguish "real embedded thumbnail" from "Explorer-generated preview." For now the flag is a no-op; the detector always relies on ffprobe metadata, which is the ground truth.

---

## How the Code Works

Both scripts share the same structure. Below is the **"only"** script; differences in **"to all"** are noted.

### 1. Dependency discovery — `_find_tool(name, hard_coded)`

Searches for `ffmpeg` / `ffprobe` in this order:

1. The hard-coded path (if provided).
2. The script's own directory.
3. On Windows: WinGet Links, `C:\ffmpeg\bin`, `C:\Program Files\ffmpeg\bin`, Chocolatey's bin, and Scoop's shims.
4. `PATH` via `shutil.which()`.

Returns the first hit, or `None`. `check_dependencies()` then prints a friendly error and exits if anything is missing.

### 2. Thumbnail detection — `detect_embedded_thumbnail(video_path)` *(only in the "only" script)*

Runs `ffprobe -show_streams -show_format -print_format json` on the file and checks **four different signals** that a thumbnail is present (see [Thumbnail Detection Logic](#thumbnail-detection-logic) below). Returns `(has_thumb: bool, reason: str)`.

### 3. Existing thumbnail enumeration — `find_existing_thumbnails(video_path)` *(only in the "to all" script)*

Similar ffprobe call, but instead of returning a boolean it returns a **list of stream indices** that look like thumbnails, so `ffmpeg -map -0:<idx>` can strip them.

### 4. Frame extraction — `extract_frame(video_path, output_path, timestamp)`

```python
ffmpeg -ss <timestamp> -i <video> -vframes 1 -q:v <quality> -y <output.jpg>
```

- `-ss` **before** `-i` seeks fast (keyframe-based). At 1 second this is essentially instant even on 4K files.
- `-vframes 1` stops after one frame.
- **Retry:** if the first attempt fails (e.g. the video is shorter than the timestamp), the code retries with `-ss 1`. If that also fails, the file is reported as a failure.

### 5. Embedding — `embed_thumbnail(video_path, image_path)`

Branches on the container format:

**MKV / WebM (attachment style):**

```bash
ffmpeg -i in.mkv -attach cover.jpg \
       -metadata:s:t mimetype=image/jpeg \
       -metadata:s:t filename=cover.jpg \
       -c copy -y out.mkv
```

In "to all" mode, `-map 0` and `-map -0:<idx>` for each old thumbnail stream are added before `-attach` so old covers are stripped first.

**MP4 / MOV / M4V / everything else (attached_pic style):**

```bash
ffmpeg -i in.mp4 -i cover.jpg \
       -map 0 -map 1 \
       -c copy -c:v:1 mjpeg \
       -disposition:v:1 attached_pic \
       -y out.mp4
```

The image becomes a **second video stream** marked `attached_pic`. Players ignore it during playback but file managers read it as the cover. `-c copy` means the real video stream is never re-encoded — the operation is nearly instantaneous regardless of file size.

In "to all" mode, old `attached_pic` streams are removed with `-map -0:<idx>` before the new image is mapped in.

> **Note on AVI/WMV:** These older containers don't have a standard "embedded thumbnail" concept. ffmpeg may still accept the operation, but file managers may not display the result. The script processes them anyway; use at your own discretion.

### 6. Atomic replace — `os.replace(temp_output, video_path)`

The output is written to `video_path + '.tmp_thumb.<ext>'` and then swapped in with `os.replace()`. On the same filesystem this is atomic — if the script is interrupted mid-write, the original file is untouched.

### 7. Per-file driver — `process_video(video_path)`

- **"only":** checks `detect_embedded_thumbnail()`; skips if present.
- **"to all":** calls `find_existing_thumbnails()` (to know what to strip) then always proceeds.

Both write the extracted frame to a `tempfile.NamedTemporaryFile`, run `embed_thumbnail()`, and clean up the temp file in a `finally:` block.

### 8. Collection — `collect_videos(folder)`

`rglob('*')` if `RECURSIVE`, `iterdir()` otherwise; filters by `VIDEO_EXTENSIONS`.

### 9. Entry point — `main()`

Resolves the target path (arg 1 or the script directory), prints the resolved tool paths, then dispatches: single file → `process_video()`, directory → loop over `collect_videos()`.

---

## Thumbnail Detection Logic

`detect_embedded_thumbnail()` in the "only" script checks four signals in order:

### 1. `attached_pic` disposition (MP4 / MOV / M4V)

```python
if s.get('disposition', {}).get('attached_pic') == 1:
    return True, f"attached_pic (stream #{s.get('index')} {s.get('codec_name')})"
```

The classic MP4-style cover. `ffprobe` reports `attached_pic: 1` on the stream's `disposition` object.

### 2. Matroska / WebM attachment streams (MKV cover art)

```python
if s.get('codec_type') == 'attachment':
    tags = s.get('tags', {}) or {}
    mime = (tags.get('mimetype') or '').lower()
    fname = (tags.get('filename') or '').lower()
    if 'image' in mime or fname.endswith(IMAGE_EXTS):
        return True, f"mkv attachment ({fname or mime})"
```

MKV doesn't use `attached_pic` — it stores the cover as a separate "attachment" stream whose `mimetype` is `image/jpeg` or `image/png` and whose `filename` tag is usually `cover.jpg`. Both are checked.

### 3. Format-level metadata tags

```python
for tag in ('cover', 'coverart', 'cover_art', 'thumbnail', 'thumb'):
    if tag in lower_tags:
        return True, f"metadata tag '{lower_tags[tag]}'"
```

Some MP4/MOV files store the cover as a tag inside the container's `format.tags` rather than as a stream. This catches those.

### 4. Extra image-like video streams

```python
video_streams = [s for s in streams if s.get('codec_type') == 'video']
if len(video_streams) > 1:
    for s in video_streams[1:]:
        if s.get('duration') in (None, '0.000000', '0'):
            return True, f"extra image stream #{s.get('index')}"
```

Rare, but some encoders create a second video stream with no duration just to hold the cover. This catches that.

If none of the four match, the file is treated as **thumbnail-less** and gets processed.

`find_existing_thumbnails()` in the "to all" script uses the same first two signals, but returns a list of indices instead of a boolean.

---

## Embedding Logic

### Why two different commands?

MP4-family containers and MKV-family containers store covers in fundamentally different ways:

| | MP4 / MOV / M4V | MKV / WebM |
|---|---|---|
| Cover stored as | A second **video stream** marked `attached_pic` | A **file attachment** named `cover.jpg` |
| ffmpeg flag | `-disposition:v:1 attached_pic` | `-attach cover.jpg` |
| Metadata | (implicit) | `-metadata:s:t mimetype=image/jpeg -metadata:s:t filename=cover.jpg` |
| Container change | Bitstream filter may adjust hdlr box | None |
| Players | Ignore it during playback | Ignore it during playback |
| File managers | Show as icon thumbnail | Show as icon thumbnail |

The script detects `Path(video_path).suffix.lower() == '.mkv'` (WebM is treated as MKV since they share the container lineage — if you find WebM needs different handling, adjust that check).

### Why `-c copy`?

The video and audio streams are copied bit-for-bit. Only the container is rewritten. This means:

- **Speed** — a 4 GB file is processed in under a second.
- **Zero quality loss** — no re-encode.
- **No CPU load** — no encoder is invoked.

The only stream that gets re-encoded is the new thumbnail image itself (`-c:v:1 mjpeg`), which is tiny.

### Why write to a temp file?

Because ffmpeg can't edit a file in place — it reads input, writes output. The temp-file approach guarantees that:

1. If ffmpeg crashes, the original file is intact.
2. If the disk fills up, the original file is intact.
3. If you Ctrl+C, the original file is intact.

Only after ffmpeg exits successfully is `os.replace()` called.

---

## Building a Standalone Executable

If you want to hand these scripts to a non-Python user, package them with **PyInstaller**. Because the scripts are pure Python with no third-party deps, the only real dependency to consider is **bundling ffmpeg itself** so the recipient doesn't have to install it.

### Option A — Leave ffmpeg external (simplest)

The resulting `.exe` is tiny (~7 MB) but requires the user to have ffmpeg installed.

```bash
pip install pyinstaller
pyinstaller --onefile --name ThumbnailAttacher-safe Thumbnail_Attacher_only_to_without_thumbnails.py
pyinstaller --onefile --name ThumbnailAttacher-force Thumbnail_Attacher_to_all.py
```

Output lands in `dist/`.

### Option B — Bundle ffmpeg + ffprobe inside the executable

Bigger (~80–120 MB), but truly self-contained. Requires a small tweak: PyInstaller unpacks bundled data to a temp dir, so the script needs to look there.

1. Download static ffmpeg builds for the target OS.
2. Place `ffmpeg.exe` / `ffprobe.exe` (or their Unix equivalents) next to the `.py` files.
3. Modify `SCRIPT_DIR` detection in both scripts to also check `sys._MEIPASS`:

    ```python
    def get_base_dir():
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent

    SCRIPT_DIR = get_base_dir()
    ```

4. Build with `--add-binary`:

    ```bash
    pyinstaller --onefile \
      --name ThumbnailAttacher-safe \
      --add-binary "ffmpeg.exe;." \
      --add-binary "ffprobe.exe;." \
      Thumbnail_Attacher_only_to_without_thumbnails.py
    ```

    On macOS/Linux use `:` instead of `;` in the `--add-binary` values:

    ```bash
    --add-binary "ffmpeg:." --add-binary "ffprobe:."
    ```

### Option C — Nuitka (faster, smaller)

```bash
pip install nuitka
python -m nuitka --onefile --standalone \
  --include-data-files=ffmpeg=ffmpeg \
  --include-data-files=ffprobe=ffprobe \
  Thumbnail_Attacher_only_to_without_thumbnails.py
```

### Cross-platform builds

PyInstaller does **not** cross-compile. You must build on the target OS:

| Target | Build on |
|--------|----------|
| Windows `.exe` | Windows |
| macOS binary | macOS |
| Linux binary | Linux |

Use GitHub Actions with a matrix of `windows-latest`, `macos-latest`, `ubuntu-latest` to produce all three at once.

### Adding an icon (Windows)

```bash
pyinstaller --onefile --name ThumbnailAttacher-safe ^
            --icon=thumb.ico ^
            Thumbnail_Attacher_only_to_without_thumbnails.py
```

### Drag-and-drop convenience

Create a `.bat` (Windows) or `.command` (macOS) shim so users can drag a folder onto the executable:

```bat
@echo off
"%~dp0ThumbnailAttacher-safe.exe" "%~1"
pause
```

---

## Troubleshooting

| Symptom | Cause & fix |
|---------|-------------|
| **`ERROR: Could not find ffmpeg and ffprobe`** | ffmpeg isn't installed or isn't on `PATH`. Install it (see [Requirements](#requirements)) or set `FFMPEG_PATH` / `FFPROBE_PATH` in the script. |
| **"Frame extraction failed"** | The video is shorter than `THUMBNAIL_TIMESTAMP`. Lower it to `0`. The script already retries at `1` second. |
| **"Embedding failed"** | Usually an unsupported container or a malformed stream map. The "to all" script prints the last line of ffmpeg's stderr — read it. Common cause: exotic codecs or multi-angle video. |
| **Thumbnail not visible in Explorer** | Windows caches thumbnails aggressively. Right-click the folder → *Refresh*, or restart Explorer, or clear `%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db`. |
| **Thumbnail visible in VLC but not Explorer** | The stream was added but not marked `attached_pic` — usually a sign that a non-MP4 container was used with the MP4 code path. Check the file extension. |
| **MKV shows "cover.jpg" as a subtitle** | Old players sometimes mislabel attachments. Re-run the script; the `-metadata:s:t filename=cover.jpg` tag is what tells the player it's a cover. |
| **Script processes 0 files** | Either the folder has no videos, or `RECURSIVE = False` and files are in subfolders. Set `RECURSIVE = True` or move files up. |
| **Original file disappears** | Should never happen — the script writes to a temp file and uses `os.replace()`. If it does, check the folder for `*.tmp_thumb.*` leftovers and rename one back. |
| **"Only" script skips everything** | That's working as intended — every file already has a thumbnail. Switch to `to_all.py` if you want to regenerate. |
| **Slow operation** | It shouldn't be — streams are copied, not re-encoded. If it is slow, you're probably on a network drive. Copy locally first. |

Run with a single file argument to test on one video before committing to a whole folder:

```bash
python3 Thumbnail_Attacher_to_all.py ./sample.mp4
```

---

## Known Limitations

- **AVI and WMV don't have a standard cover-art convention.** The script will embed something, but most file managers won't display it.
- **WebM is treated as MKV.** Most tools accept this, but WebM's spec is stricter — Google's own players may ignore the attachment. If you need WebM-specific handling, branch on `'.webm'` separately.
- **Recursive mode is all-or-nothing.** Set `RECURSIVE = True` if you want subfolders, `False` for top-level only. There's no per-depth control.
- **No dry-run mode.** The script acts immediately. On a large library, test on a copy first.
- **No confirmation prompt** in `to_all.py` — it will overwrite every file it touches. Back up first if you're nervous.
- **Double-encode warning:** running the script twice in a row on the same file is safe (the "to all" version strips the old cover), but each run rewrites the container. Avoid running it in a loop.
- **Non-ASCII filenames** work on modern Python, but Windows terminals with the legacy code page can render them as `?`. The operation still succeeds.
- **No multi-track subtitle handling.** If the source has subtitles, they're preserved by `-c copy` but the thumbnail mapping may shift their stream indices. Playable, but cosmetic metadata may be off.
- **No way to pick a frame interactively.** The timestamp is fixed in config. If you need to hand-pick a frame, use a GUI like [MKVToolNix GUI](https://mkvtoolnix.download/) or [MP4Box](https://gpac.wp.imt.fr/mp4box/).

---

## Extending the Scripts

### Change the thumbnail timestamp per file

Replace the fixed `THUMBNAIL_TIMESTAMP` with a heuristic — e.g. grab the frame at 10% of the duration:

```python
def smart_timestamp(video_path):
    r = subprocess.run(
        [FFPROBE, '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'json', video_path],
        capture_output=True, text=True, check=True)
    dur = float(json.loads(r.stdout)['format']['duration'])
    return max(1, min(dur * 0.1, 30))
```

Then pass that to `extract_frame()`.

### Use a custom image instead of an extracted frame

Replace `extract_frame(video_path, tmp_path)` with a copy of your own image:

```python
shutil.copy('my_cover.jpg', tmp_path)
```

Great for adding uniform branding to a series.

### Skip files that already have a matching sidecar `.jpg`

```python
if Path(video_path).with_suffix('.jpg').exists():
    return  # or skip
```

Useful when you maintain your own set of covers next to the videos.

### Parallel processing

Wrap `process_video()` calls in a `concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as ex:
    ex.map(process_video, files)
```

Since ffmpeg is a subprocess, this scales well. Watch disk I/O on spinning drives.

### Add a `--dry-run` flag

Parse `sys.argv` with `argparse` and short-circuit before calling `embed_thumbnail()`:

```python
import argparse
ap = argparse.ArgumentParser()
ap.add_argument('path', nargs='?', default=SCRIPT_DIR)
ap.add_argument('--dry-run', action='store_true')
args = ap.parse_args()
```

---

## License

MIT License. Use, modify, and redistribute freely.

---

## Contributing

Pull requests welcome for:

- WebM-specific attachment handling.
- A `--dry-run` flag.
- Interactive frame selection (curses TUI or a preview PNG).
- Sidecar-image support (`.jpg` next to the video).
- A single unified script with a `--force` flag replacing the two-file split.

Please test any changes against MP4, MOV, MKV, and WebM inputs before opening a PR.
