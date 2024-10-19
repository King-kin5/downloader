import yt_dlp
import requests
from .utils import sanitize_title
import logging

class YouTubeDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.logger = logging.getLogger(__name__)

    def get_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def fetch_video_data(self, video_url, audio_only=False):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'format': 'bestaudio[ext=m4a]/bestaudio/best' if audio_only else 'best[height<=720]/best',
                'http_headers': self.get_headers(),
                'socket_timeout': 30,
                'retries': 3
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"Extracting info for URL: {video_url}")
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    self.logger.error("No video information found")
                    return None

                video_data = {
                    'title': info.get('title', ''),
                    'duration': info.get('duration'),
                    'url': info.get('url'),
                    'ext': info.get('ext', 'mp4'),
                    'format_id': info.get('format_id'),
                    'filesize': info.get('filesize')
                }

                self.logger.info(f"Successfully fetched data for: {video_data['title']}")
                return video_data

        except Exception as e:
            self.logger.error(f"Error fetching video data: {str(e)}")
            return None

    def prepare_download_url(self, video_url, audio_only=False):
        try:
            video_data = self.fetch_video_data(video_url, audio_only)
            if not video_data:
                return None, None, "Error fetching video data"

            download_url = video_data['url']
            title = sanitize_title(video_data['title'])
            ext = 'mp3' if audio_only else video_data['ext']
            filename = f"{title}.{ext}"

            return download_url, filename, None

        except Exception as e:
            self.logger.error(f"Error preparing download: {str(e)}")
            return None, None, str(e)

    def get_download_stream(self, download_url):
        try:
            response = requests.get(
                download_url,
                headers=self.get_headers(),
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            return response

        except requests.RequestException as e:
            self.logger.error(f"Download stream error: {str(e)}")
            raise