#!/usr/bin/env python3
"""
Vimeo Private Video Downloader using yt-dlp
Downloads private/public Vimeo videos using just a link
"""

import argparse
import os
import sys
import subprocess
import re
import platform

def check_ytdlp_installed():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(['yt-dlp', '--version'], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE, 
                       check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_ytdlp():
    """Install yt-dlp using pip."""
    try:
        print("Installing yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'],
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=True)
        print("yt-dlp installed successfully!")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error installing yt-dlp: {str(e)}")
        return False

def download_vimeo_video(url, output_dir=None, quality='best', format_preference=None):
    """Download a Vimeo video using yt-dlp."""
    
    if not check_ytdlp_installed():
        print("yt-dlp not found. Attempting to install...")
        if not install_ytdlp():
            print("Failed to install yt-dlp. Please install manually: pip install yt-dlp")
            return False
    
    # Create output directory if it doesn't exist
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        os.chdir(output_dir)
    
    # Define the command based on parameters
    cmd = ['yt-dlp']
    
    # Add URL
    cmd.append(url)
    
    # Quality selection
    if quality == 'best':
        cmd.extend(['-f', 'bestvideo+bestaudio/best'])
    elif quality == 'worst':
        cmd.extend(['-f', 'worstvideo+worstaudio/worst'])
    elif quality.isdigit():
        # For specific resolution
        if format_preference == 'mp4':
            cmd.extend(['-f', f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[ext=mp4]/best'])
        else:
            cmd.extend(['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'])
    
    # Format preference
    if format_preference and quality != 'best' and quality != 'worst' and not quality.isdigit():
        if format_preference == 'mp4':
            cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
        elif format_preference == 'webm':
            cmd.extend(['-f', 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'])
    
    # Always merge formats if possible
    cmd.append('--merge-output-format')
    if format_preference == 'mp4':
        cmd.append('mp4')
    else:
        cmd.append('mkv')
    
    # Output file template
    cmd.extend(['-o', '%(title)s.%(ext)s'])
    
    # Add cookies if available
    cookie_file = os.path.join(os.path.expanduser('~'), '.vimeo_cookies.txt')
    if os.path.exists(cookie_file):
        cmd.extend(['--cookies', cookie_file])
    
    # Add verbose output
    cmd.append('--verbose')
    
    # Add user-agent
    cmd.extend(['--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'])
    
    # Print the command (with URL truncated for privacy)
    safe_url = re.sub(r'([?&](?:token|password|h|p)=)[^&]*', r'\1XXXXX', url)
    print(f"Running: {' '.join(cmd).replace(url, safe_url)}")
    
    try:
        # On Windows, we need to use shell=True to avoid console window popping up
        use_shell = platform.system() == "Windows"
        
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            shell=use_shell
        )
        
        # Print output in real-time
        for line in process.stdout:
            line = line.strip()
            print(line)
        
        # Wait for completion and get return code
        return_code = process.wait()
        
        if return_code == 0:
            print("\nDownload completed successfully!")
            return True
        else:
            print(f"\nError: yt-dlp exited with code {return_code}")
            return False
            
    except subprocess.SubprocessError as e:
        print(f"\nError executing yt-dlp: {str(e)}")
        return False
    except KeyboardInterrupt:
        print("\nDownload cancelled by user.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download Vimeo videos (public or private) using yt-dlp")
    parser.add_argument("url", help="Vimeo video URL")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: current directory)")
    parser.add_argument("-q", "--quality", default="best",
                        help="Video quality: 'best', 'worst', or maximum height (e.g., '720')")
    parser.add_argument("-f", "--format", choices=["mp4", "webm", "mkv"], default="mp4",
                        help="Preferred video format (default: mp4)")
    
    args = parser.parse_args()
    
    download_vimeo_video(args.url, args.output_dir, args.quality, args.format)

if __name__ == "__main__":
    main()
