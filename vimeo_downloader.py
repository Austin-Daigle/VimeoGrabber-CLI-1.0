import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import re
import json
import os
import urllib.parse
from threading import Thread
import time
import base64
from urllib.parse import parse_qs, urlparse

class VimeoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Vimeo Video Downloader")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TButton", font=("Arial", 10, "bold"))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TEntry", font=("Arial", 10))
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL input
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=10)
        
        url_label = ttk.Label(url_frame, text="Vimeo URL:")
        url_label.pack(side=tk.LEFT, padx=5)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Download button
        self.download_button = ttk.Button(main_frame, text="Download Video", command=self.start_download)
        self.download_button.pack(pady=15)
        
        # Progress frame (initially hidden)
        self.progress_frame = ttk.Frame(main_frame)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.progress_frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Speed label
        self.speed_var = tk.StringVar(value="Speed: 0 KB/s")
        self.speed_label = ttk.Label(self.progress_frame, textvariable=self.speed_var)
        self.speed_label.pack(fill=tk.X, pady=5)
        
        # Cancel button
        self.cancel_button = ttk.Button(self.progress_frame, text="Cancel", command=self.cancel_download)
        self.cancel_button.pack(pady=10)
        
        # Session and cancellation flag
        self.session = requests.Session()
        self.cancelled = False
        self.download_thread = None
        
        # Configure session with default headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        })

    def start_download(self):
        url = self.url_var.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a Vimeo URL")
            return
            
        if not (url.startswith("https://vimeo.com/") or url.startswith("https://player.vimeo.com/")):
            messagebox.showerror("Error", "Invalid Vimeo URL")
            return
            
        # Show progress frame and start download in a separate thread
        self.progress_frame.pack(fill=tk.X, expand=True)
        self.download_button.config(state="disabled")
        self.cancelled = False
        
        self.download_thread = Thread(target=self.download_video, args=(url,))
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def download_video(self, url):
        try:
            # Update status
            self.update_status("Getting video information...")
            
            # Clear any existing cookies
            self.session.cookies.clear()
            
            # Configure session
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "Referer": "https://vimeo.com/",
                "Origin": "https://vimeo.com",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            })
            
            # Parse and extract video information
            self.update_status("Parsing video URL...")
            video_info = self.parse_vimeo_url(url)
            
            if not video_info:
                self.show_error("Could not parse Vimeo URL. Please ensure it's a valid Vimeo video link.")
                return
                
            video_id = video_info["video_id"]
            unlock_hash = video_info.get("unlock_hash")
            share_token = video_info.get("share_token")
            h_param = video_info.get("h_param")
            
            # First, visit the main video page to get cookies and tokens
            video_page_url = f"https://vimeo.com/{video_id}"
            if unlock_hash:
                video_page_url = f"https://vimeo.com/{video_id}/{unlock_hash}"
            elif share_token:
                video_page_url = f"https://vimeo.com/{video_id}?share={share_token}"
            
            self.update_status(f"Visiting video page to get authentication cookies...")
            page_response = self.session.get(video_page_url)
            
            if page_response.status_code != 200:
                self.update_status("Warning: Could not access video page, but will try to continue...")
            
            # Now fetch the video configuration
            config_url = self.build_config_url(video_id, unlock_hash, h_param, share_token)
            
            self.update_status(f"Fetching video configuration from player API...")
            response = self.session.get(config_url)
            
            # Debug response
            if response.status_code != 200:
                error_text = f"Failed to get video config: HTTP {response.status_code}\n"
                try:
                    error_text += f"Error details: {response.text[:200]}"
                except:
                    pass
                    
                # Try one more time with a different approach
                self.update_status("Initial attempt failed, trying alternate method...")
                
                # Try the embed page approach
                embed_url = f"https://player.vimeo.com/video/{video_id}"
                if unlock_hash:
                    embed_url += f"/{unlock_hash}"
                
                self.session.get(embed_url)
                
                # Try the config URL again
                response = self.session.get(config_url)
                
                if response.status_code != 200:
                    self.show_error(error_text)
                    return
            
            # Parse the configuration
            try:
                config_data = response.json()
            except json.JSONDecodeError:
                self.show_error(f"Could not parse video configuration. Response was not valid JSON.")
                return
                
            # Extract video info
            try:
                video_data = config_data.get("video", {})
                video_title = video_data.get("title", f"vimeo_{video_id}")
                
                # Try different paths to find the video streams
                progressive_streams = self.extract_streams(config_data)
                
                if not progressive_streams:
                    self.show_error("No downloadable streams found in the video configuration. This video might be protected.")
                    return
                    
                # Get the highest quality stream
                best_stream = max(progressive_streams, key=lambda x: int(x.get("height", 0)))
                download_url = best_stream.get("url")
                
                if not download_url:
                    self.show_error("Could not find download URL")
                    return
                    
                # Clean up the title for use as filename
                safe_title = re.sub(r'[\\/*?:"<>|]', "", video_title).strip()
                suggested_filename = f"{safe_title}.mp4"
                
                # Ask user for save location
                self.update_status("Select where to save the video...")
                save_path = filedialog.asksaveasfilename(
                    initialfile=suggested_filename,
                    defaultextension=".mp4",
                    filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
                )
                
                if not save_path:
                    # User cancelled
                    self.reset_ui()
                    return
                    
                # Download the file
                self.download_file(download_url, save_path)
                
            except Exception as e:
                self.show_error(f"Error processing video data: {str(e)}")
                return
                
        except Exception as e:
            self.show_error(f"Download failed: {str(e)}")
    
    def parse_vimeo_url(self, url):
        """Parse different Vimeo URL formats and extract video ID and access tokens"""
        # Initialize result
        result = {}
        
        # Pattern for URLs with unlock hash: vimeo.com/325572565/9d31d005e2
        unlock_pattern = re.compile(r'vimeo\.com/(\d+)/([a-zA-Z0-9]+)')
        match = unlock_pattern.search(url)
        if match:
            result["video_id"] = match.group(1)
            result["unlock_hash"] = match.group(2)
            return result
            
        # Pattern for player URLs with hash: player.vimeo.com/video/123456789/abcdef
        player_hash_pattern = re.compile(r'player\.vimeo\.com/video/(\d+)/([a-zA-Z0-9]+)')
        match = player_hash_pattern.search(url)
        if match:
            result["video_id"] = match.group(1)
            result["unlock_hash"] = match.group(2)
            return result
            
        # Pattern for URLs with h parameter: vimeo.com/123456789?h=abcdef
        query_pattern = re.compile(r'vimeo\.com/(\d+)')
        match = query_pattern.search(url)
        if match:
            result["video_id"] = match.group(1)
            
            # Extract query parameters
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Check for h parameter
            if 'h' in query_params:
                result["h_param"] = query_params['h'][0]
            
            # Check for share token
            if 'share' in query_params:
                result["share_token"] = query_params['share'][0]
                
            return result
            
        # Standard player pattern: player.vimeo.com/video/123456789
        player_pattern = re.compile(r'player\.vimeo\.com/video/(\d+)')
        match = player_pattern.search(url)
        if match:
            result["video_id"] = match.group(1)
            return result
            
        # If nothing matched, check if we might have a simple numeric ID
        if url.strip().isdigit():
            result["video_id"] = url.strip()
            return result
            
        return None
    
    def download_file(self, url, save_path):
        try:
            # Prepare for download
            self.update_status(f"Downloading video...")
            
            # Stream the download to show progress
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024  # 1 MB
            
            downloaded = 0
            start_time = time.time()
            speeds = []
            
            with open(save_path, 'wb') as file:
                for data in response.iter_content(block_size):
                    if self.cancelled:
                        # Delete partial file
                        file.close()
                        os.remove(save_path)
                        self.root.after(0, self.reset_ui)
                        return
                    
                    # Write data
                    file.write(data)
                    downloaded += len(data)
                    
                    # Update progress
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    
                    # Calculate and update speed
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = downloaded / elapsed
                        speeds.append(speed)
                        # Use average of last 5 speed measurements
                        avg_speed = sum(speeds[-5:]) / min(5, len(speeds))
                        speed_text = self.format_speed(avg_speed)
                        self.root.after(0, lambda s=speed_text: self.speed_var.set(f"Speed: {s}"))
                    
                    # Update status with percentage
                    if total_size > 0:
                        percent = int(progress)
                        self.root.after(0, lambda p=percent: self.update_status(f"Downloading: {p}%"))
            
            # Download complete
            self.root.after(0, lambda: self.update_status("Download complete!"))
            self.root.after(0, lambda: messagebox.showinfo("Success", "Video downloaded successfully!"))
            self.root.after(0, self.reset_ui)
            
        except Exception as e:
            self.show_error(f"Download failed: {str(e)}")
    
    def update_status(self, message):
        self.root.after(0, lambda m=message: self.status_var.set(m))
    
    def show_error(self, message):
        self.root.after(0, lambda m=message: messagebox.showerror("Error", m))
        self.root.after(0, self.reset_ui)
    
    def reset_ui(self):
        self.progress_frame.pack_forget()
        self.download_button.config(state="normal")
        self.progress_var.set(0)
        self.speed_var.set("Speed: 0 KB/s")
        self.status_var.set("Ready")
    
    def cancel_download(self):
        self.cancelled = True
        self.update_status("Cancelling...")
    
    def format_speed(self, bytes_per_second):
        # Convert bytes per second to a human-readable format
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
            
        # Append other necessary parameters
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
        })
        
        # Convert params to URL query string
        if params:
            query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items()])
            config_url += '?' + query_string
            
        return config_url
        
    def extract_streams(self, config_data):
        """Extract video streams from various possible locations in the config"""
        streams = []
        
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
        
        # Return unique streams based on URL
        unique_streams = []
        seen_urls = set()
        
        for stream in streams:
            if 'url' in stream and stream['url'] not in seen_urls:
                seen_urls.add(stream['url'])
                unique_streams.append(stream)
                
        return unique_streams

def main():
    root = tk.Tk()
    app = VimeoDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
