from functools import wraps
from flask import Flask, current_app as app,  request
import yt_dlp
import requests
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import hashlib
from flask_limiter.util import get_remote_address
from flask_limiter import  Limiter


app = Flask(__name__)

#Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Track download history
download_history = {}

class YouTubeDownloader:
    def __init__(self, link):
        self.link = link
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.youtube.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Chromium";v="123", "Google Chrome";v="123"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }

    def simulate_human_behavior(self, driver):
        """Simulate realistic human viewing behavior"""
        try:
            time.sleep(random.uniform(3, 7))
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(2, 4))
            
            try:
                play_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ytp-play-button"))
                )
                play_button.click()
                time.sleep(random.uniform(1, 3))
            except:
                pass
            
            time.sleep(random.uniform(10, 30))
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            app.logger.error(f"Error in human behavior simulation: {str(e)}")

    def get_video_info(self):
        """Get video information using undetected-chromedriver"""
        driver = None
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            options.add_experimental_option('prefs', {
                'profile.default_content_setting_values.notifications': 2,
                'profile.managed_default_content_settings.images': 1,
                'profile.managed_default_content_settings.javascript': 1
            })
            
            driver = uc.Chrome(options=options)
            driver.set_window_size(1920, 1080)
            
            driver.get(self.link)
            self.simulate_human_behavior(driver)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            
            video_info = driver.execute_script("""
                return {
                    title: document.title,
                    videoElement: {
                        currentSrc: document.querySelector('video').currentSrc,
                        duration: document.querySelector('video').duration,
                    },
                    playerData: ytInitialPlayerResponse
                };
            """)
            
            return video_info
            
        except Exception as e:
            app.logger.error(f"Selenium error: {str(e)}")
            raise
        finally:
            if driver:
                driver.quit()

    def stream_audio(self):
        """Stream audio from YouTube video"""
        if not self.link:
            raise ValueError("No URL provided")

        try:
            return self._try_ytdlp_audio()
        except Exception as e:
            app.logger.error(f"yt-dlp method failed: {str(e)}")
            return self._try_selenium_audio()

    def stream_video(self):
        """Stream video from YouTube"""
        if not self.link:
            raise ValueError("No URL provided")

        try:
            return self._try_ytdlp_video()
        except Exception as e:
            app.logger.error(f"yt-dlp method failed: {str(e)}")
            return self._try_selenium_video()

    def _try_ytdlp_audio(self):
        """Try downloading audio using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'http_headers': self.headers,
            'socket_timeout': 30,
            'retries': 3,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'config', 'js'],
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            time.sleep(random.uniform(1, 3))
            info = ydl.extract_info(self.link, download=False)
            formats = info.get('formats', [])
            
            audio_formats = [
                f for f in formats 
                if f.get('acodec') != 'none' 
                and f.get('vcodec') == 'none'
                and f.get('ext') in ['m4a', 'mp3', 'wav']
            ]
            
            if not audio_formats:
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
            
            if not audio_formats:
                raise ValueError("No audio formats found")
            
            best_audio = max(
                audio_formats,
                key=lambda x: (x.get('abr', 0) or 0, x.get('filesize', 0) or 0)
            )
            
            title = "".join(
                c for c in info.get('title', 'audio') 
                if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            
            return self._create_content_generator(best_audio['url']), title

    def _try_ytdlp_video(self):
        """Try downloading video using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'http_headers': self.headers,
            'socket_timeout': 30,
            'retries': 3,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'config', 'js'],
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            time.sleep(random.uniform(1, 3))
            info = ydl.extract_info(self.link, download=False)
            
            format_id = info.get('format_id')
            formats = info.get('formats', [])
            selected_format = next(
                (f for f in formats if f.get('format_id') == format_id),
                None
            )
            
            if not selected_format:
                raise ValueError("No suitable video format found")

            title = "".join(
                c for c in info.get('title', 'video') 
                if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            
            return self._create_content_generator(selected_format['url']), title

    def _try_selenium_audio(self):
        """Fallback method using Selenium for audio"""
        video_info = self.get_video_info()
        
        if not video_info or not video_info.get('videoElement', {}).get('currentSrc'):
            raise ValueError("Could not extract audio information")
        
        audio_url = video_info['videoElement']['currentSrc']
        title = "".join(
            c for c in video_info.get('title', 'audio') 
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        
        return self._create_content_generator(audio_url), title

    def _try_selenium_video(self):
        """Fallback method using Selenium for video"""
        video_info = self.get_video_info()
        
        if not video_info or not video_info.get('videoElement', {}).get('currentSrc'):
            raise ValueError("Could not extract video information")
        
        video_url = video_info['videoElement']['currentSrc']
        title = "".join(
            c for c in video_info.get('title', 'video') 
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        
        return self._create_content_generator(video_url), title

    def _create_content_generator(self, url):
        """Create a generator for streaming content"""
        def generate():
            try:
                time.sleep(random.uniform(0.5, 2))
                
                with requests.get(
                    url, 
                    stream=True, 
                    headers=self.headers,
                    timeout=30
                ) as r:
                    r.raise_for_status()
                    
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            if random.random() < 0.01:
                                time.sleep(random.uniform(0.1, 0.3))
                            yield chunk
                            
            except requests.RequestException as e:
                app.logger.error(f"Streaming error: {str(e)}")
                raise

        return generate
def validate_youtube_url(url):
    """Validate YouTube URL format including support for Shorts"""
    app.logger.info(f"Validating URL: {url}")
    
    if not url:
        raise ValueError("No URL provided")
    
    valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        
        # Check if domain is valid
        if parsed.netloc not in valid_domains:
            raise ValueError("Invalid YouTube URL")
            
        # Handle different YouTube URL formats
        if 'watch?v=' in url:
            # Regular YouTube video
            video_id = parse_qs(parsed.query).get('v', [None])[0]
            if not video_id:
                raise ValueError("Invalid YouTube video URL format")
        elif 'youtu.be/' in url:
            # Shortened YouTube URL
            video_id = parsed.path.split('/')[-1]
            if not video_id:
                raise ValueError("Invalid shortened YouTube URL format")
        elif '/shorts/' in url:
            # YouTube Shorts
            video_id = parsed.path.split('/shorts/')[-1].split('?')[0]
            if not video_id:
                raise ValueError("Invalid YouTube Shorts URL format")
        else:
            raise ValueError("Unsupported YouTube URL format")
            
        # Additional validation for video ID format
        if not video_id or len(video_id) < 8:
            raise ValueError("Invalid video ID format")
            
        app.logger.info(f"URL validation successful. Video ID: {video_id}")
        return True
        
    except Exception as e:
        app.logger.error(f"URL validation failed: {str(e)}")
        raise ValueError("Invalid URL format")


def rate_limit_by_url(func):
    """Custom decorator for per-URL rate limiting"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        url = request.form.get('youtube_url')
        if url:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            current_time = time.time()
            
            download_history.clear()
            url_history = download_history.get(url_hash, [])
            url_history = [t for t in url_history if current_time - t < 3600]
            if len(url_history) >= 3:
                return "Rate limit exceeded for this video. Please try again later.", 429
            
            download_history[url_hash] = url_history + [current_time]
        
        return func(*args, **kwargs)
    return wrapper

def log_download(func):
    """Decorator to log download attempts"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        client_ip = get_remote_address()
        url = request.form.get('youtube_url')
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            app.logger.info(
                f"Download completed - IP: {client_ip}, "
                f"URL: {url}, Duration: {duration:.2f}s, "
                f"Timestamp: {datetime.now().isoformat()}"
            )
            
            return result
        except Exception as e:
            app.logger.error(
                f"Download failed - IP: {client_ip}, "
                f"URL: {url}, Error: {str(e)}, "
                f"Timestamp: {datetime.now().isoformat()}"
            )
            raise
    
    return wrapper