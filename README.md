# VimeoGrab (Command Line Interface - v.1.0)

A Python utility for downloading Vimeo videos, including private and password-protected ones, using just a URL.

## Overview

This repository contains Python scripts for downloading Vimeo videos:

1. **vimeograb_cli.py** - A pure Python implementation that attempts to download videos directly from Vimeo's API
2. **vimeograb_core.py** - A more robust implementation that uses the `yt-dlp` library to handle various protection mechanisms
3. **vimeograb_gui.py** - (Coming soon) A graphical user interface for VimeoGrab

The recommended approach is to use `vimeograb_core.py` as it can bypass most of Vimeo's restrictions.

## Features

- Download both public and private Vimeo videos with a simple command
- Support for various video qualities and formats
- Real-time progress tracking with download speed and ETA
- Automatic installation of dependencies if needed
- Support for specific resolutions (e.g., 720p, 1080p)
- Format selection (MP4, WebM, MKV)

## Requirements

- Python 3.6+
- Internet connection
- The `vimeo_ytdl.py` script will automatically install `yt-dlp` if it's not already installed

## Installation

1. Clone or download this repository to your local machine
2. Ensure you have Python 3.6 or higher installed
3. (Optional) Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Unix/MacOS
   ```
4. Install dependencies (only needed for the direct API approach):
   ```
   pip install requests
   ```

## Usage

### Using vimeograb_core.py (Recommended)

This script uses `yt-dlp` to download videos, which is much more effective at handling Vimeo's protection mechanisms.

```bash
python vimeograb_core.py [video_url] [-o output_directory] [-q quality] [-f format]
```

#### Arguments:

- `video_url` (required): The URL of the Vimeo video to download
- `-o, --output-dir`: Directory to save the downloaded video (default: current directory)
- `-q, --quality`: Video quality to download:
  - `best` (default): Highest available quality
  - `worst`: Lowest available quality
  - A number (e.g., `720`): Specific resolution height
- `-f, --format`: Preferred video format: `mp4` (default), `webm`, or `mkv`

#### Examples:

```bash
# Download a video at best quality
python vimeograb_core.py https://vimeo.com/123456789

# Download to a specific directory
python vimeograb_core.py https://vimeo.com/123456789 -o C:\Videos

# Download at 720p resolution
python vimeograb_core.py https://vimeo.com/123456789 -q 720

# Download in webm format
python vimeograb_core.py https://vimeo.com/123456789 -f webm
```

### Using vimeograb_cli.py (Alternative)

This is a pure Python implementation that attempts to download videos directly from Vimeo's API.

```bash
python vimeograb_cli.py [video_url] [-o output_directory] [-q quality]
```

#### Arguments:

- `video_url` (required): The URL of the Vimeo video to download
- `-o, --output-dir`: Directory to save the downloaded video (default: current directory)
- `-q, --quality`: Video quality to download:
  - `best` (default): Highest available quality
  - `worst`: Lowest available quality
  - A number (e.g., `720`): Specific resolution height

#### Examples:

```bash
# Download a video at best quality
python vimeograb_cli.py https://vimeo.com/123456789

# Download to a specific directory at 720p
python vimeograb_cli.py https://vimeo.com/123456789 -o C:\Videos -q 720
```

## Troubleshooting

### 403 Forbidden Error with vimeograb_cli.py

If you encounter a 403 Forbidden error with the `vimeograb_cli.py` script, this means Vimeo is blocking direct access to their API. Switch to using the `vimeograb_core.py` script, which can bypass these restrictions.

### yt-dlp Installation Issues

If the automatic installation of `yt-dlp` fails, you can manually install it using:

```bash
pip install yt-dlp
```

### Video Format Selection

For best compatibility, use the MP4 format (`-f mp4`). If you need a specific resolution, use the `-q` option followed by the height (e.g., `-q 720` for 720p).

### Cookies for Private Videos

For some private videos that require login, you may need to use a cookies file. The script will automatically look for a cookies file at `~/.vimeo_cookies.txt`. You can generate this file using browser extensions like "Get cookies.txt" or "Cookie Quick Manager".

## How It Works

1. The script parses the provided Vimeo URL to extract the video ID and any authentication tokens
2. It then either:
   - Attempts to fetch the video configuration directly (vimeo_dl_cli.py), or
   - Uses yt-dlp to handle the video extraction (vimeo_ytdl.py)
3. The video is downloaded in the specified quality and format, with real-time progress tracking

## Legal Notice

This tool is intended for personal use only. Please respect copyright laws and terms of service when using this tool. Only download videos that you have the right to access and use.

## License

This project is provided as-is, for educational purposes. Use at your own risk.
