import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

class YouTubeService:
    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def extract_video_id(self, video_url):
        """Extract video ID from YouTube URL."""
        parsed_url = urlparse(video_url)
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
        raise ValueError('Invalid YouTube URL')

    def extract_channel_id(self, channel_url):
        """Extract channel ID from YouTube URL."""
        parsed_url = urlparse(channel_url)
        path_parts = parsed_url.path.split('/')
        
        # Handle different URL formats
        if 'youtube.com' not in parsed_url.hostname and 'youtu.be' not in parsed_url.hostname:
            raise ValueError('Invalid YouTube URL')

        # Handle @username format
        if path_parts[1].startswith('@'):
            try:
                # First, search for the channel by handle
                request = self.youtube.search().list(
                    part='snippet',
                    q=path_parts[1],
                    type='channel',
                    maxResults=1
                )
                response = request.execute()
                if response['items']:
                    return response['items'][0]['snippet']['channelId']
                raise ValueError('Channel not found')
            except Exception as e:
                raise ValueError(f'Error finding channel: {str(e)}')

        # Handle /channel/ID format
        if 'channel' in path_parts:
            return path_parts[path_parts.index('channel') + 1]
            
        # Handle /c/custom-name format or /user/username format
        if 'c' in path_parts or 'user' in path_parts:
            try:
                # Get channel ID by username or custom URL
                request = self.youtube.search().list(
                    part='snippet',
                    q=path_parts[-1],
                    type='channel',
                    maxResults=1
                )
                response = request.execute()
                if response['items']:
                    return response['items'][0]['snippet']['channelId']
                raise ValueError('Channel not found')
            except Exception as e:
                raise ValueError(f'Error finding channel: {str(e)}')
                
        raise ValueError('Invalid YouTube channel URL format')

    def get_video_data(self, video_url):
        """Get basic video information."""
        video_id = self.extract_video_id(video_url)
        request = self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response['items']:
            raise ValueError('Video not found')
            
        video = response['items'][0]
        return {
            'title': video['snippet']['title'],
            'description': video['snippet']['description'],
            'publishedAt': video['snippet']['publishedAt'],
            'viewCount': video['statistics']['viewCount'],
            'likeCount': video['statistics'].get('likeCount', 0),
            'commentCount': video['statistics'].get('commentCount', 0),
            'duration': video['contentDetails']['duration']
        }

    def get_channel_data(self, channel_url):
        """Get channel information."""
        channel_id = self.extract_channel_id(channel_url)
        request = self.youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        )
        response = request.execute()
        
        if not response['items']:
            raise ValueError('Channel not found')
            
        channel = response['items'][0]
        return {
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'],
            'publishedAt': channel['snippet']['publishedAt'],
            'subscriberCount': channel['statistics'].get('subscriberCount', '0'),
            'videoCount': channel['statistics']['videoCount'],
            'viewCount': channel['statistics']['viewCount']
        }

    def get_video_comments(self, video_url, max_results=100):
        """Get video comments."""
        video_id = self.extract_video_id(video_url)
        request = self.youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=max_results,
            order='relevance'
        )
        response = request.execute()
        
        comments = []
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'author': comment['authorDisplayName'],
                'text': comment['textDisplay'],
                'publishedAt': comment['publishedAt'],
                'likeCount': comment['likeCount']
            })
        return comments

    def get_video_analytics(self, video_url):
        """Get video analytics data."""
        video_id = self.extract_video_id(video_url)
        video_data = self.get_video_data(video_url)
        
        # For public API, we can only get basic analytics
        return {
            'views': video_data['viewCount'],
            'likes': video_data['likeCount'],
            'comments': video_data['commentCount'],
            'engagement_rate': self._calculate_engagement_rate(
                int(video_data['viewCount']),
                int(video_data['likeCount']),
                int(video_data['commentCount'])
            )
        }

    def _calculate_engagement_rate(self, views, likes, comments):
        """Calculate engagement rate."""
        if views == 0:
            return 0
        return ((likes + comments) / views) * 100 