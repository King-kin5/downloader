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
            'cookiefile': 'cookies.txt',
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

    def _ensure_cookies_file(self):
        """Ensure cookies file exists"""
        if not os.path.exists('cookies.txt'):
            with open('cookies.txt', 'w') as f:
                f.write('')
            os.chmod('cookies.txt', 0o666)

    def _sanitize_title(self, title):
        """Sanitize the video title for safe filename usage"""
        return "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()

    def _handle_download_error(self, error):
        """Handle download errors with proper logging"""
        error_msg = str(error)
        app.logger.error(f"Download error: {error_msg}")
        app.logger.error(traceback.format_exc())
        
        if "Sign in to confirm you're not a bot" in error_msg:
            raise ValueError("YouTube bot detection triggered. Please try again later.")
        raise error

    def stream_audio(self):
        """Stream audio from YouTube video"""
        if not self.link:
            raise ValueError("No URL provided")
        
        self._ensure_cookies_file()
        
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
                
                title = self._sanitize_title(info.get('title', 'audio'))
                
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                
                if not audio_formats:
                    raise ValueError("No audio formats found")
                    
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                audio_url = best_audio['url']
                
                app.logger.info(f"Starting audio stream for: {title}")
                
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
            self._handle_download_error(e)

    def get_format_info(self, format_dict):
        """Helper method to get format information in a standardized way"""
        return {
            'height': format_dict.get('height', 0) or 0,
            'filesize': format_dict.get('filesize', 0) or format_dict.get('filesize_approx', 0) or 0,
            'is_combined': format_dict.get('vcodec', 'none') != 'none' and format_dict.get('acodec', 'none') != 'none',
            'vcodec': format_dict.get('vcodec', ''),
            'acodec': format_dict.get('acodec', ''),
            'format_id': format_dict.get('format_id', ''),
            'ext': format_dict.get('ext', ''),
            'tbr': format_dict.get('tbr', 0) or 0,
        }

    def stream_video(self):
        """Stream video from YouTube with a target resolution of 720p"""
        if not self.link:
            raise ValueError("No URL provided")
        
        self._ensure_cookies_file()
        
        ydl_opts = {
            **self.base_options,
            'format': 'bv*[height<=720]+ba/b[height<=720]',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.link, download=False)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = self._sanitize_title(info.get('title', 'video'))
                
                formats = info.get('formats', [])
                if not formats:
                    raise ValueError("No formats available for this video")

                # Filter and sort formats
                suitable_formats = []
                for f in formats:
                    format_info = self.get_format_info(f)
                    if (format_info['vcodec'] != 'none' and 
                        format_info['height'] <= 720 and 
                        format_info['height'] >= 480):
                        suitable_formats.append((f, format_info))

                if not suitable_formats:
                    ydl_opts['format'] = 'best[height<=720]'
                    info = ydl.extract_info(self.link, download=False)
                    best_format = info['formats'][-1]
                    suitable_formats = [(best_format, self.get_format_info(best_format))]

                # Sort formats by quality
                best_format, format_info = max(
                    suitable_formats,
                    key=lambda x: (
                        x[1]['height'],           # Prefer higher resolution up to 720p
                        x[1]['tbr'],             # Then higher bitrate
                        x[1]['is_combined'],     # Prefer combined formats
                        -x[1]['filesize']        # Prefer smaller files when all else is equal
                    )
                )
                
                app.logger.info(
                    f"Selected format: {format_info['format_id']}, "
                    f"Resolution: {format_info['height']}p, "
                    f"Filesize: {format_info['filesize']/1024/1024:.2f}MB"
                )

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
            self._handle_download_error(e)

# Error handler for the Flask app
@app.errorhandler(Exception)
def handle_error(error):
    error_msg = str(error)
    app.logger.error(f"An error occurred: {error_msg}", exc_info=True)
    
    if "Sign in to confirm you're not a bot" in error_msg:
        return {
            "error": "YouTube bot detection triggered. Please try again in a few minutes.",
            "details": error_msg
        }, 429
    
    return {
        "error": "An error occurred while processing your request",
        "details": error_msg
    }, 500