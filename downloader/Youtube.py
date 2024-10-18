
import yt_dlp
from flask import current_app as app
import traceback
from flask import Flask
import requests

app = Flask(__name__)

class YouTubeDownloader:
    def __init__(self, link):
        self.link = link

    def stream_audio(self):
        if not self.link:
            raise ValueError("No URL provided")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.link, download=False)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = info.get('title', 'audio')
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                if not audio_formats:
                    raise ValueError("No audio formats found")
                    
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                audio_url = best_audio['url']
                
                def generate():
                    with requests.get(audio_url, stream=True) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                yield chunk

                return generate, title
            
            except Exception as e:
                app.logger.error(f"Error occurred while downloading audio: {str(e)}")
                app.logger.error(traceback.format_exc())
                raise
    def get_format_info(self, format_dict):
        """Helper method to get format information in a standardized way"""
        height = format_dict.get('height', 0) or 0
        filesize = format_dict.get('filesize', 0) or format_dict.get('filesize_approx', 0) or 0
        vcodec = format_dict.get('vcodec', '')
        acodec = format_dict.get('acodec', '')
        
        # Check if this is a combined format (has both video and audio)
        is_combined = vcodec != 'none' and acodec != 'none'
        
        return {
            'height': height,
            'filesize': filesize,
            'is_combined': is_combined,
            'vcodec': vcodec,
            'acodec': acodec,
            'format_id': format_dict.get('format_id', ''),
            'ext': format_dict.get('ext', ''),
            'tbr': format_dict.get('tbr', 0) or 0,  # Total bitrate
        }
    def stream_video(self, resolution=None):  # resolution parameter kept for compatibility but not used
        if not self.link:
            raise ValueError("No URL provided")
        
        target_height = 720  # Fixed to 720p
        
        ydl_opts = {
            'format': 'bv*[height<=720]+ba/b[height<=720]',  # Force 720p or lower
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.link, download=False)
                if info is None:
                    raise ValueError("Unable to extract video information")
                
                title = info.get('title', 'video')
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                formats = info.get('formats', [])
                if not formats:
                    raise ValueError("No formats available for this video")

                # Filter for 720p formats
                suitable_formats = []
                for f in formats:
                    format_info = self.get_format_info(f)
                    
                    # Skip formats without video or with 0 filesize
                    if (format_info['vcodec'] == 'none' or 
                        (format_info['filesize'] == 0 and format_info['tbr'] == 0)):
                        continue
                    
                    # Only consider formats close to 720p
                    if format_info['height'] <= 720 and format_info['height'] >= 480:  # Allow 480p as fallback
                        suitable_formats.append((f, format_info))

                if not suitable_formats:
                    # Fallback to best available format under 720p
                    ydl_opts['format'] = 'best[height<=720]'
                    info = ydl.extract_info(self.link, download=False)
                    best_format = info['formats'][-1]
                    format_info = self.get_format_info(best_format)
                    suitable_formats = [(best_format, format_info)]

                # Sort formats to prefer closest to 720p with good quality
                def format_sort_key(format_tuple):
                    f, info = format_tuple
                    quality_score = 0
                    
                    # Prefer formats closer to 720p
                    height_diff = abs(info['height'] - 720)
                    quality_score -= height_diff
                    
                    # Prefer higher bitrate within our constraints
                    quality_score += info['tbr']
                    
                    # Prefer combined formats
                    if info['is_combined']:
                        quality_score += 500
                        
                    return quality_score

                suitable_formats.sort(key=format_sort_key, reverse=True)
                best_format, format_info = suitable_formats[0]
                
                app.logger.info(f"Selected format: {format_info['format_id']}, "
                              f"Resolution: {format_info['height']}p, "
                              f"Filesize: {format_info['filesize']/1024/1024:.2f}MB")

                video_url = best_format['url']
                
                def generate():
                    with requests.get(video_url, stream=True) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                yield chunk

                return generate, title
            
            except Exception as e:
                app.logger.error(f"Error occurred while downloading video: {str(e)}")
                app.logger.error(traceback.format_exc())
                raise


    def log_progress(self, d):
        if d['status'] == 'downloading':
            app.logger.info(f"Downloading: {d['filename']} - {d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']}")
        elif d['status'] == 'finished':
            app.logger.info(f"Download finished: {d['filename']}")