#!/usr/bin/env python3
"""
Vimeo Private Video Downloader - Command Line Version
Downloads private Vimeo videos using just a link
"""

import requests
import json
import re
import os
import argparse
import sys
import urllib.parse
from urllib.parse import parse_qs, urlparse
import time

class VimeoDownloaderCLI:
    def __init__(self):
        # Configure session with browser-like headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })
        
    def download_video(self, url, output_dir=None, quality='best'):
        """Download video from Vimeo URL"""
        print(f"Processing URL: {url}")
        
        # Parse the URL to extract video ID and other parameters
        video_id, unlock_hash, h_param, share_token = self.parse_vimeo_url(url)
        
        if not video_id:
            print("Error: Could not extract video ID from URL")
            return False
        
        print(f"Video ID: {video_id}")
        
        # First visit the actual video page to get cookies and other session data
        print("Visiting video page to establish session...")
        try:
            # Set referrer to a common website
            self.session.headers.update({"Referer": "https://www.google.com/"})
            
            # Visit the main video page first
            main_url = f"https://vimeo.com/{video_id}"
            if unlock_hash:
                main_url = f"https://vimeo.com/{video_id}/{unlock_hash}"
            
            main_response = self.session.get(main_url, timeout=30)
            # Don't raise_for_status here as some videos might redirect
            
            # Update referrer to the video page for subsequent requests
            self.session.headers.update({"Referer": main_url})
        except requests.exceptions.RequestException as e:
            # Continue even if this fails as we might still be able to get the config
            print(f"Note: Couldn't visit main video page: {str(e)}")
        
        # Build the config URL
        config_url = self.build_config_url(video_id, unlock_hash, h_param, share_token)
        
        # Get the video config data
        print("Fetching video information...")
        try:
            # Update headers specifically for the config request
            self.session.headers.update({
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            })
            
            response = self.session.get(config_url, timeout=30)
            response.raise_for_status()
            config_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching video data: {str(e)}")
            return False
        except json.JSONDecodeError:
            print("Error: Invalid JSON response from Vimeo")
            return False
            
        # Extract video title
        try:
            if 'video' in config_data and 'title' in config_data['video']:
                video_title = config_data['video']['title']
            else:
                video_title = f"vimeo_{video_id}"
        except Exception:
            video_title = f"vimeo_{video_id}"
            
        # Clean the filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
        
        # Extract streams
        streams = self.extract_streams(config_data)
        
        if not streams:
            print("Error: No video streams found")
            return False
            
        # Select the stream based on quality preference
        selected_stream = None
        
        if quality == 'best':
            # Sort by height (resolution) in descending order
            streams.sort(key=lambda x: x.get('height', 0), reverse=True)
            selected_stream = streams[0]
        elif quality == 'worst':
            # Sort by height (resolution) in ascending order
            streams.sort(key=lambda x: x.get('height', 0))
            selected_stream = streams[0]
        else:
            # Try to match the requested quality
            try:
                requested_height = int(quality) if quality.isdigit() else 0
                closest_stream = streams[0]
                min_diff = abs(closest_stream.get('height', 0) - requested_height)
                
                for stream in streams:
                    height = stream.get('height', 0)
                    diff = abs(height - requested_height)
                    if diff < min_diff:
                        min_diff = diff
                        closest_stream = stream
                        
                selected_stream = closest_stream
            except (ValueError, IndexError) as e:
                print(f"Error selecting quality: {str(e)}")
                if streams:
                    selected_stream = streams[0]
                else:
                    print("No video streams available")
                    return False
        
        # Determine output directory
        if not output_dir:
            output_dir = os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine file extension
        if 'mime' in selected_stream:
            ext = selected_stream['mime'].split('/')[-1]
        else:
            ext = 'mp4'
            
        # Create the output file path
        output_file = os.path.join(output_dir, f"{safe_title}.{ext}")
        
        # Download the video
        print(f"Downloading video: {video_title}")
        print(f"Resolution: {selected_stream.get('width', 'Unknown')}x{selected_stream.get('height', 'Unknown')}")
        print(f"Output file: {output_file}")
        
        return self.download_file(selected_stream['url'], output_file)
    
    def parse_vimeo_url(self, url):
        """Parse different Vimeo URL formats and extract video ID and access tokens"""
        video_id = None
        unlock_hash = None
        h_param = None
        share_token = None
        
        # Parse URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        query_params = parse_qs(parsed_url.query)
        
        # Extract h parameter if present
        if 'h' in query_params:
            h_param = query_params['h'][0]
            
        # Check for share token (private links)
        if parsed_url.fragment:
            fragment_params = parse_qs(parsed_url.fragment)
            
            if 'share' in fragment_params:
                share_token = fragment_params['share'][0]
        elif 'share' in query_params:
            share_token = query_params['share'][0]
        
        # Standard vimeo.com URL
        if parsed_url.netloc == 'vimeo.com':
            if len(path_parts) > 0:
                video_id = path_parts[0]
                
            # Check for the unlock hash in the path
            if len(path_parts) > 1 and not path_parts[1].startswith('?'):
                unlock_hash = path_parts[1]
                
        # Player URL format
        elif 'player.vimeo.com' in parsed_url.netloc:
            if len(path_parts) > 1 and path_parts[0] == 'video':
                video_id = path_parts[1]
                
            # Check for the unlock hash
            if len(path_parts) > 2:
                unlock_hash = path_parts[2]
                
        # Try to extract video ID from the URL using regex as fallback
        if not video_id:
            match = re.search(r'/(\d+)(?:/|\?|$)', url)
            if match:
                video_id = match.group(1)
                
        return video_id, unlock_hash, h_param, share_token
        
    def download_file(self, url, save_path):
        """Download a file with progress reporting"""
        try:
            with self.session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                # Get the file size in MB for display
                total_mb = total_size / (1024 * 1024)
                
                # Initialize variables for progress and speed calculation
                downloaded = 0
                start_time = time.time()
                chunk_count = 0
                last_print_time = start_time
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            chunk_count += 1
                            
                            # Calculate progress
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            
                            # Only update the display every 50 chunks or 0.5 seconds to avoid console spam
                            current_time = time.time()
                            if chunk_count % 50 == 0 or (current_time - last_print_time) > 0.5:
                                elapsed = current_time - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                eta = (total_size - downloaded) / speed if speed > 0 else 0
                                
                                # Format the speed for display
                                speed_str = self.format_speed(speed)
                                
                                # Display progress
                                print(f"\rProgress: {progress:.1f}% ({downloaded/(1024*1024):.1f} MB / {total_mb:.1f} MB) | Speed: {speed_str} | ETA: {eta:.1f}s", end="")
                                
                                last_print_time = current_time
                
                print("\nDownload complete!")
                return True
                
        except requests.exceptions.RequestException as e:
            print(f"\nError downloading file: {str(e)}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return False
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return False
    
    def format_speed(self, bytes_per_second):
        """Format bytes per second to human-readable format"""
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.1f} B/s"
        elif bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
    
    def build_config_url(self, video_id, unlock_hash=None, h_param=None, share_token=None):
        """Build the appropriate config URL based on available parameters"""
        # Base config URL
        if unlock_hash:
            config_url = f"https://player.vimeo.com/video/{video_id}/{unlock_hash}/config"
        else:
            config_url = f"https://player.vimeo.com/video/{video_id}/config"
        
        # Add query parameters if available
        params = {}
        
        if h_param:
            params['h'] = h_param
        if share_token:
            params['share'] = share_token
            
        # Add more browser-like parameters
        params.update({
            'autopause': '0',
            'byline': '0',
            'collections': '0',
            'context': 'Vimeo\u002525FFFFFFC',
            'default_to_hd': '1',
            'portrait': '0',
            'speed': '1',
            'title': '0',
            'transparent': '1',
            'app_id': '122963',  # Vimeo player app ID
            'player_id': 'player',
            'api': '1',
            'autoplay': '0'
        })
        
        # Convert params to URL query string
        if params:
            query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items()])
            config_url += '?' + query_string
            
        return config_url
        
    def extract_streams(self, config_data):
        """Extract video streams from various possible locations in the config"""
        streams = []
        
        # Print the keys of the response for debugging
        print(f"Response keys: {list(config_data.keys()) if isinstance(config_data, dict) else 'Not a dictionary'}")        
        
        # Check the standard location for progressive streams
        if 'request' in config_data:
            req_data = config_data['request']
            if 'files' in req_data and 'progressive' in req_data['files']:
                streams.extend(req_data['files']['progressive'])
            
        # Check alternate location sometimes used in newer responses
        if 'video' in config_data and 'progressive_download' in config_data['video']:
            if config_data['video']['progressive_download']:
                streams.extend(config_data['video']['progressive_download'])
                
        # Check for 'mime' key in stream choices
        if 'request' in config_data and 'files' in config_data['request']:
            file_info = config_data['request']['files']
            
            # Check for video/mp4 mime types
            if 'mime' in file_info:
                for mime_type, mime_streams in file_info['mime'].items():
                    if mime_type == 'video/mp4' and isinstance(mime_streams, list):
                        streams.extend(mime_streams)
        
        # Check nested streams in 'files' object (sometimes used by Vimeo)
        if 'request' in config_data and 'files' in config_data['request']:
            for key, value in config_data['request']['files'].items():
                if isinstance(value, list) and len(value) > 0:
                    if all(isinstance(item, dict) for item in value):
                        if 'url' in value[0] and ('width' in value[0] or 'height' in value[0]):
                            streams.extend(value)
        
        # Check for HLS streams that may contain downloadable segments
        if 'request' in config_data and 'files' in config_data['request']:
            file_info = config_data['request']['files']
            if 'hls' in file_info and 'url' in file_info['hls']:
                hls_url = file_info['hls']['url']
                print(f"Found HLS URL: {hls_url}") 
                # Note: To properly download HLS would require additional processing with ffmpeg
                # This is just to show the URL is found
        
        # Check for master.json for non-standard cases
        if 'player' in config_data and 'config_url' in config_data['player']:
            print(f"Found master config URL: {config_data['player']['config_url']}")    
        
        # Return unique streams based on URL
        unique_streams = []
        seen_urls = set()
        
        for stream in streams:
            if 'url' in stream and stream['url'] not in seen_urls:
                seen_urls.add(stream['url'])
                unique_streams.append(stream)
        
        if not unique_streams:
            print("No standard streams found. May need to use youtube-dl or yt-dlp for this video.")
                
        return unique_streams

def main():
    parser = argparse.ArgumentParser(description="Download private Vimeo videos using just a URL")
    parser.add_argument("url", help="Vimeo video URL")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: current directory)")
    parser.add_argument("-q", "--quality", default="best", help="Video quality: 'best', 'worst', or resolution height (e.g., '720')")
    
    args = parser.parse_args()
    
    downloader = VimeoDownloaderCLI()
    downloader.download_video(args.url, args.output_dir, args.quality)

if __name__ == "__main__":
    main()
