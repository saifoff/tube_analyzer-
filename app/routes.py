from flask import Blueprint, render_template, request, jsonify
from app.youtube_service import YouTubeService

main_bp = Blueprint('main', __name__)
youtube_service = YouTubeService()

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/analyze-video', methods=['POST'])
def analyze_video():
    video_url = request.form.get('video_url')
    if not video_url:
        return jsonify({'error': 'Video URL is required'}), 400
    
    try:
        video_data = youtube_service.get_video_data(video_url)
        return jsonify(video_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/analyze-channel', methods=['POST'])
def analyze_channel():
    channel_url = request.form.get('channel_url')
    if not channel_url:
        return jsonify({'error': 'Channel URL is required'}), 400
    
    try:
        channel_data = youtube_service.get_channel_data(channel_url)
        return jsonify(channel_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/video-comments', methods=['POST'])
def get_video_comments():
    video_url = request.form.get('video_url')
    if not video_url:
        return jsonify({'error': 'Video URL is required'}), 400
    
    try:
        comments = youtube_service.get_video_comments(video_url)
        return jsonify(comments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/video-analytics', methods=['POST'])
def get_video_analytics():
    video_url = request.form.get('video_url')
    if not video_url:
        return jsonify({'error': 'Video URL is required'}), 400
    
    try:
        analytics = youtube_service.get_video_analytics(video_url)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500 