from flask import Flask, render_template, request, send_file, Response, render_template, stream_with_context, jsonify, redirect
from downloader.facebookdownloader import FacebookVideoDownloader
from config import API_URL
import requests
from io import BytesIO
from downloader.utils import sanitize_title
from downloader.Youtube import YouTubeDownloader, log_download, rate_limit_by_url, validate_youtube_url
import logging
import traceback
import os
from flask_limiter.util import get_remote_address
from flask_limiter import  Limiter
import time
app = Flask(__name__, static_folder='static',
template_folder='templates')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
downloader = FacebookVideoDownloader(API_URL)

# Add root route handler that redirects to home

@app.route('/')
def index():
    try:
        # Log template directory information
        template_dir = os.path.join(app.root_path, 'templates')
        logger.info(f"Template directory path: {template_dir}")
        logger.info(f"Template directory exists: {os.path.exists(template_dir)}")
        if os.path.exists(template_dir):
            logger.info(f"Template directory contents: {os.listdir(template_dir)}")
        
        return render_template('homepage.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/home')
def home():
    try:
        template_dir = os.path.join(app.root_path, 'templates')
        logger.info(f"Template directory path: {template_dir}")
        logger.info(f"Template directory exists: {os.path.exists(template_dir)}")
        if os.path.exists(template_dir):
            logger.info(f"Template directory contents: {os.listdir(template_dir)}")
            
        return render_template('homepage.html')
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/debug-info')
def debug_info():
    """Route to show debug information"""
    try:
        template_dir = os.path.join(app.root_path, 'templates')
        static_dir = os.path.join(app.root_path, 'static')
        
        debug_info = {
            'app_root_path': app.root_path,
            'template_folder': app.template_folder,
            'template_dir_exists': os.path.exists(template_dir),
            'template_dir_contents': os.listdir(template_dir) if os.path.exists(template_dir) else [],
            'static_dir_exists': os.path.exists(static_dir),
            'static_dir_contents': os.listdir(static_dir) if os.path.exists(static_dir) else [],
            'environment': app.config.get('ENV'),
            'debug_mode': app.debug,
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/facebook')
def facebook_page():
    return render_template('facebook.html')

@app.route('/youtube')
def youtube_page():
    return render_template('youtube.html')

@app.route('/instagram')
def instagram_page():
    return render_template('instagram.html')

@app.route('/tiktok')
def titok_page():
    return render_template('tiktok.html')



# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/download_youtube_audio', methods=['POST'])
@log_download
def download_youtube_audio():
    try:
        video_url = request.form.get('youtube_url')
        app.logger.info(f"Received URL: {video_url}")
        
        validate_youtube_url(video_url)
        app.logger.info("YouTube URL validated successfully.")
        
        downloader = YouTubeDownloader(video_url)
        app.logger.info("Initialized YouTubeDownloader.")
        
        generate, title = downloader.stream_audio()
        app.logger.info(f"Audio stream generated for title: {title}")
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        app.logger.info(f"Sanitized title for filename: {safe_title}")
        
        filename = f"{safe_title}_{int(time.time())}.mp3"
        app.logger.info(f"Final filename: {filename}")
        
        response = Response(
            stream_with_context(generate()),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "audio/mpeg",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        app.logger.info("Response created successfully.")
        return response

    except ValueError as e:
        app.logger.error(f"ValueError in download_youtube_audio: {str(e)}")
        return str(e), 400
    except Exception as e:
        app.logger.error(f"Error in download_youtube_audio: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "An error occurred while processing your request", 500


@app.route('/download_youtube_video', methods=['POST'])
@log_download
def download_youtube_video():
    try:
        video_url = request.form.get('youtube_url')
        app.logger.info(f"Received URL: {video_url}")
        validate_youtube_url(video_url)
        app.logger.info("YouTube URL validated successfully.")
        
        downloader = YouTubeDownloader(video_url)
        app.logger.info("Initialized YouTubeDownloader.")
        
        generate, title = downloader.stream_video()
        app.logger.info(f"Video stream generated for title: {title}")
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        app.logger.info(f"Sanitized title for filename: {safe_title}")
        
        filename = f"{safe_title}_{int(time.time())}.mp4"
        app.logger.info(f"Final filename: {filename}")
        
        response = Response(
            stream_with_context(generate()),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "video/mp4",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff"
            }
        )
        app.logger.info("Response created successfully.")
        return response

    except ValueError as e:
        app.logger.error(f"ValueError in download_youtube_video: {str(e)}")
        return str(e), 400
    except Exception as e:
        app.logger.error(f"Error in download_youtube_video: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "An error occurred while processing your request", 500


@app.route('/download_facebook_video', methods=['POST'])
def download_facebook_video():
    video_url = request.form.get('video_url')
    video_data = downloader.fetch_video_data(video_url)

    if not video_data:
        return "Error: Unable to fetch video data", 400

    hd_url = video_data.get('hd')
    video_title = sanitize_title(video_data.get('title', 'downloaded_video')) + '.mp4'
    try:
        response = requests.get(hd_url, stream=True)

        if response.status_code != 200:
            return "Error: Unable to download video", 500

        video_buffer = BytesIO()

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                video_buffer.write(chunk)

        video_buffer.seek(0)

        return send_file(
            video_buffer,
            as_attachment=True,
            download_name=video_title,
            mimetype='video/mp4'
        )

    except requests.RequestException as e:
        return f"Error occurred while downloading video: {e}", 500

if __name__ == '__main__':
    app.run()