#!/usr/bin/env python3
"""
VimeoGrab Core v1.0 - Core functionality for downloading Vimeo videos
Uses yt-dlp to handle private and protected videos

Version: 1.0
Status: Stable
"""

import argparse
import os
import subprocess
import sys
import re
import time

def check_ytdl_installed():
    """Check if yt-dlp is installed and try to install it if not."""
    try:
        # Try to run yt-dlp version command
        subprocess.run(['yt-dlp', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("yt-dlp is not installed. Attempting to install...")
        
        try:
            # Try to install yt-dlp using pip
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          check=True)
            print("yt-dlp has been successfully installed.")
            return True
        except subprocess.SubprocessError as e:
            print(f"Failed to install yt-dlp: {str(e)}")
            print("Please install it manually with: pip install yt-dlp")
            return False

def get_cookies_path():
    """Get path to cookies file if it exists."""
    home_dir = os.path.expanduser("~")
    cookies_path = os.path.join(home_dir, ".vimeo_cookies.txt")
    
    if os.path.isfile(cookies_path):
        print(f"Using cookies file: {cookies_path}")
        return cookies_path
    return None

def sanitize_filename(filename):
    """Sanitize filename by removing invalid characters."""
    # Replace invalid characters with underscore
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def download_video(url, output_dir=None, quality='best', format_preference='mp4', verbose=False):
    """
    Download a Vimeo video using yt-dlp.
    
    Args:
        url (str): Vimeo video URL
        output_dir (str): Directory to save the downloaded video
        quality (str): Video quality to download ('best', 'worst', or resolution height)
        format_preference (str): Preferred video format ('mp4', 'webm', 'mkv')
        verbose (bool): Show verbose output
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    # Check if yt-dlp is installed
    if not check_ytdl_installed():
        return False
    
    # Set output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.getcwd()
    
    # Build yt-dlp command
    cmd = ['yt-dlp']
    
    # User-agent to mimic browser
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    cmd.extend(['--user-agent', user_agent])
    
    # Add cookies file if available
    cookies_path = get_cookies_path()
    if cookies_path:
        cmd.extend(['--cookies', cookies_path])
    
    # Set video quality based on user preference
    if quality == 'best':
        cmd.extend(['--format', f'bestvideo[ext={format_preference}]+bestaudio/best[ext={format_preference}]/best'])
    elif quality == 'worst':
        cmd.extend(['--format', f'worstvideo[ext={format_preference}]+worstaudio/worst[ext={format_preference}]/worst'])
    else:
        try:
            # Try to parse quality as a resolution height
            resolution = int(quality)
            cmd.extend(['--format', f'bestvideo[height<={resolution}][ext={format_preference}]+bestaudio/best[height<={resolution}][ext={format_preference}]/best'])
        except ValueError:
            print(f"Invalid quality: {quality}. Using best quality instead.")
            cmd.extend(['--format', f'bestvideo[ext={format_preference}]+bestaudio/best[ext={format_preference}]/best'])
    
    # Set output directory and filename template
    cmd.extend(['--paths', output_dir])
    cmd.extend(['--output', '%(title)s.%(ext)s'])
    
    # Add verbose flag if requested
    if verbose:
        cmd.append('--verbose')
    
    # Add video URL
    cmd.append(url)
    
    # Print command for debugging if verbose
    if verbose:
        # Mask parts of the URL for privacy if it has tokens
        masked_url = url
        if "?" in url or "&" in url:
            masked_url = re.sub(r'([?&][^=&]+)=([^&]{4})([^&]*)', r'\1=\2***', url)
        print(f"Running command: {' '.join(cmd).replace(url, masked_url)}")
    
    try:
        # Execute yt-dlp command and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Process and print output in real-time
        for line in process.stdout:
            print(line.strip())
        
        # Wait for the process to finish
        process.wait()
        
        # Check if download was successful
        if process.returncode == 0:
            print("\nDownload completed successfully!")
            return True
        else:
            print(f"\nError: yt-dlp process exited with code {process.returncode}")
            return False
    
    except Exception as e:
        print(f"Error executing yt-dlp: {str(e)}")
        return False

def main():
    """Main function to parse arguments and download video."""
    parser = argparse.ArgumentParser(description="Download Vimeo videos (including private ones) with yt-dlp")
    parser.add_argument("url", help="Vimeo video URL")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: current directory)")
    parser.add_argument("-q", "--quality", default="best", 
                        help="Video quality: 'best', 'worst', or resolution height (e.g., '720')")
    parser.add_argument("-f", "--format", default="mp4", choices=["mp4", "webm", "mkv"],
                        help="Preferred video format (default: mp4)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose output")
    
    args = parser.parse_args()
    
    download_video(args.url, args.output_dir, args.quality, args.format, args.verbose)

if __name__ == "__main__":
    main()
