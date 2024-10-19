from flask import Flask, current_app as app
import yt_dlp
import traceback
import requests
import os
import random
import time

app = Flask(__name__)

class YouTubeDownloader:
    def __init__(self, link):
        self.link = link
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        self.base_options = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'config', 'js'],
                    'max_comments': [0],
                }
            },
            'socket_timeout': 15,
            'format': 'bestaudio/best',
            'geo_bypass': True,
            'allow_unplayable_formats': True,
            'no_check_certificates': True,
            'prefer_insecure': True,
            'http_headers': self._get_random_headers()
        }

    def _get_random_headers(self):
        user_agent = random.choice(self.user_agents)
        return {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.youtube.com',
            'Referer': 'https://www.youtube.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'trailers'
        }

    def _extract_with_retry(self, ydl, max_retries=3):
        for attempt in range(max_retries):
            try:
                # Rotate headers for each attempt
                ydl._download_retcode = 0
                ydl.params['http_headers'] = self._get_random_headers()
                
                info = ydl.extract_info(self.link, download=False)
                if info:
                    return info
                
            except yt_dlp.utils.DownloadError as e:
                if 'Sign in to confirm' in str(e) and attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 3))  # Random delay between attempts
                    continue
                elif attempt == max_retries - 1:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

    def stream_audio(self):
        """Stream audio from YouTube video with fallback options"""
        if not self.link:
            raise ValueError("No URL provided")
        
        ydl_opts = {
            **self.base_options,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'extract_flat': 'in_playlist',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = self._extract_with_retry(ydl)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = "".join(c for c in info.get('title', 'audio') if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                
                if not audio_formats:
                    audio_formats = [f for f in formats if f.get('acodec') != 'none']
                
                if not audio_formats:
                    raise ValueError("No audio formats found")
                    
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                audio_url = best_audio['url']
                
                def generate():
                    try:
                        headers = self._get_random_headers()
                        with requests.get(audio_url, stream=True, headers=headers, timeout=15) as r:
                            r.raise_for_status()
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    yield chunk
                    except requests.RequestException as e:
                        app.logger.error(f"Streaming error: {str(e)}")
                        raise

                return generate, title
            
        except Exception as e:
            app.logger.error(f"Error occurred while downloading audio: {str(e)}")
            app.logger.error(traceback.format_exc())
            raise

    def stream_video(self):
        """Stream video from YouTube with fallback options"""
        if not self.link:
            raise ValueError("No URL provided")
        
        ydl_opts = {
            **self.base_options,
            'format': 'best[height<=720]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'extract_flat': 'in_playlist',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = self._extract_with_retry(ydl)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = "".join(c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                formats = info.get('formats', [])
                # Try to get a format that's likely to work
                format_priority = ['22', '18', '135', '134', 'best']
                selected_format = None
                
                for fmt in format_priority:
                    selected_format = next((f for f in formats if f.get('format_id') == fmt), None)
                    if selected_format:
                        break
                
                if not selected_format:
                    selected_format = max(formats, key=lambda f: f.get('height', 0) or 0)

                if not selected_format:
                    raise ValueError("No suitable format found")

                video_url = selected_format['url']
                
                def generate():
                    try:
                        headers = self._get_random_headers()
                        with requests.get(video_url, stream=True, headers=headers, timeout=15) as r:
                            r.raise_for_status()
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    yield chunk
                    except requests.RequestException as e:
                        app.logger.error(f"Streaming error: {str(e)}")
                        raise

                return generate, title
            
        except Exception as e:
            app.logger.error(f"Error occurred while downloading video: {str(e)}")
            app.logger.error(traceback.format_exc())
            raise