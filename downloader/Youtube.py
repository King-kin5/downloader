import yt_dlp
from flask import current_app as app
import traceback
from flask import Flask
import requests
import os

app = Flask(__name__)

class YouTubeDownloader:
    def __init__(self, link):
        self.link = link
        self.base_options = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'cookiesfrombrowser': ('chrome',),  # Try to use Chrome cookies
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'player_skip': ['webpage'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }

    def stream_audio(self):
        """Stream audio from YouTube video"""
        if not self.link:
            raise ValueError("No URL provided")
        
        ydl_opts = {
            **self.base_options,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.link, download=False)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = "".join(c for c in info.get('title', 'audio') if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                
                if not audio_formats:
                    raise ValueError("No audio formats found")
                    
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                audio_url = best_audio['url']
                
                def generate():
                    try:
                        with requests.get(audio_url, stream=True, headers=self.base_options['http_headers']) as r:
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
        """Stream video from YouTube"""
        if not self.link:
            raise ValueError("No URL provided")
        
        ydl_opts = {
            **self.base_options,
            'format': 'best[height<=720]',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.link, download=False)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = "".join(c for c in info.get('title', 'video') if c.isalnum() or c in (' ', '-', '_')).rstrip()
                formats = info.get('formats', [])
                
                if not formats:
                    raise ValueError("No formats available for this video")

                best_format = formats[-1]  # yt-dlp sorts formats by quality
                video_url = best_format['url']
                
                def generate():
                    try:
                        with requests.get(video_url, stream=True, headers=self.base_options['http_headers']) as r:
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