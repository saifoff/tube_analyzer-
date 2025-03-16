import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from collections import Counter
import re
from textblob import TextBlob

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

    def _analyze_video_performance_timeline(self, video_data):
        """Analyze video performance metrics over time."""
        published_date = datetime.strptime(video_data['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
        current_date = datetime.utcnow()
        days_since_upload = (current_date - published_date).days

        # Calculate daily average metrics
        total_views = int(video_data['viewCount'])
        total_likes = int(video_data['likeCount'])
        total_comments = int(video_data['commentCount'])

        # Create timeline data points
        timeline_data = {
            'upload_date': published_date.strftime('%Y-%m-%d'),
            'days_active': days_since_upload,
            'daily_averages': {
                'views': round(total_views / max(days_since_upload, 1), 2),
                'likes': round(total_likes / max(days_since_upload, 1), 2),
                'comments': round(total_comments / max(days_since_upload, 1), 2)
            },
            'total_metrics': {
                'views': total_views,
                'likes': total_likes,
                'comments': total_comments
            },
            'performance_data': {
                'dates': [],
                'metrics': {
                    'views': [],
                    'engagement': []
                }
            }
        }

        # Generate estimated performance data points
        num_points = min(30, days_since_upload)  # Show up to 30 data points
        if num_points > 0:
            interval = days_since_upload / num_points
            for i in range(num_points + 1):
                point_date = published_date + timedelta(days=i * interval)
                progress_ratio = i / num_points
                
                # Estimate metrics using a typical viral decay curve
                estimated_views = total_views * (1 - (1 - progress_ratio) ** 2)
                estimated_engagement = ((total_likes + total_comments) / max(estimated_views, 1)) * 100

                timeline_data['performance_data']['dates'].append(point_date.strftime('%Y-%m-%d'))
                timeline_data['performance_data']['metrics']['views'].append(round(estimated_views))
                timeline_data['performance_data']['metrics']['engagement'].append(round(estimated_engagement, 2))

        return timeline_data

    def get_video_performance(self, video_url):
        """Get detailed video performance metrics."""
        video_id = self.extract_video_id(video_url)
        
        # Get video details
        video_data = self.get_video_data(video_url)
        
        # Get video comments for sentiment analysis
        comments = self.get_video_comments(video_url)
        
        # Perform sentiment analysis on comments
        sentiment_data = self._analyze_comments_sentiment(comments)
        
        # Calculate engagement metrics
        engagement_data = self._calculate_engagement_metrics(video_data)
        
        # Analyze performance timeline
        timeline_data = self._analyze_video_performance_timeline(video_data)
        
        # Extract and analyze tags
        tags_data = self._analyze_video_tags(video_data.get('tags', []))
        
        return {
            'basic_metrics': video_data,
            'sentiment_analysis': sentiment_data,
            'engagement_metrics': engagement_data,
            'tags_analysis': tags_data,
            'timeline_data': timeline_data
        }

    def get_channel_analytics(self, channel_url):
        """Get detailed channel analytics."""
        channel_id = self.extract_channel_id(channel_url)
        
        # Get basic channel info
        channel_data = self.get_channel_data(channel_url)
        
        # Get channel's videos
        videos_data = self._get_channel_videos(channel_id)
        
        # Analyze upload frequency
        upload_analysis = self._analyze_upload_frequency(videos_data)
        
        # Analyze video performance trends
        performance_trends = self._analyze_performance_trends(videos_data)
        
        return {
            'basic_info': channel_data,
            'upload_analysis': upload_analysis,
            'performance_trends': performance_trends,
            'recent_videos': videos_data[:10]  # Last 10 videos
        }

    def _get_channel_videos(self, channel_id, max_results=50):
        """Get channel's videos with detailed metrics."""
        try:
            # First get playlist ID of channel uploads
            channels_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channels_response['items']:
                return []
                
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist
            videos = []
            request = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=max_results
            )
            
            while request and len(videos) < max_results:
                response = request.execute()
                
                # Get detailed info for each video
                for item in response['items']:
                    video_id = item['contentDetails']['videoId']
                    video_details = self.youtube.videos().list(
                        part='snippet,statistics,contentDetails',
                        id=video_id
                    ).execute()
                    
                    if video_details['items']:
                        videos.append(video_details['items'][0])
                
                request = self.youtube.playlistItems().list_next(request, response)
                
            return videos
            
        except Exception as e:
            print(f"Error fetching channel videos: {str(e)}")
            return []

    def _analyze_upload_frequency(self, videos_data):
        """Analyze channel's upload frequency patterns."""
        if not videos_data:
            return {
                'average_frequency': 0,
                'total_videos': 0,
                'frequency_trend': 'No data available'
            }
            
        # Sort videos by publish date
        publish_dates = [
            datetime.strptime(video['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            for video in videos_data
        ]
        publish_dates.sort()
        
        if len(publish_dates) < 2:
            return {
                'average_frequency': 0,
                'total_videos': 1,
                'frequency_trend': 'Insufficient data'
            }
            
        # Calculate average days between uploads
        time_diffs = [(publish_dates[i+1] - publish_dates[i]).days 
                     for i in range(len(publish_dates)-1)]
        avg_frequency = sum(time_diffs) / len(time_diffs)
        
        # Analyze trend
        recent_freq = sum(time_diffs[:5]) / 5 if len(time_diffs) >= 5 else avg_frequency
        old_freq = sum(time_diffs[-5:]) / 5 if len(time_diffs) >= 5 else avg_frequency
        
        if recent_freq < old_freq:
            trend = 'Increasing upload frequency'
        elif recent_freq > old_freq:
            trend = 'Decreasing upload frequency'
        else:
            trend = 'Stable upload frequency'
            
        return {
            'average_frequency': round(avg_frequency, 1),
            'total_videos': len(videos_data),
            'frequency_trend': trend
        }

    def _analyze_performance_trends(self, videos_data):
        """Analyze performance trends across videos."""
        if not videos_data:
            return {
                'view_trend': 'No data',
                'engagement_trend': 'No data',
                'top_performing_videos': []
            }
            
        # Calculate metrics for each video
        video_metrics = []
        for video in videos_data:
            stats = video['statistics']
            engagement = self._calculate_engagement_rate(
                int(stats.get('viewCount', 0)),
                int(stats.get('likeCount', 0)),
                int(stats.get('commentCount', 0))
            )
            
            video_metrics.append({
                'title': video['snippet']['title'],
                'views': int(stats.get('viewCount', 0)),
                'engagement_rate': engagement,
                'published_at': video['snippet']['publishedAt']
            })
            
        # Sort by views to get top performing videos
        top_videos = sorted(video_metrics, key=lambda x: x['views'], reverse=True)[:5]
        
        # Analyze trends
        recent_videos = sorted(video_metrics, key=lambda x: x['published_at'])[-5:]
        old_videos = sorted(video_metrics, key=lambda x: x['published_at'])[:5]
        
        avg_recent_views = sum(v['views'] for v in recent_videos) / len(recent_videos)
        avg_old_views = sum(v['views'] for v in old_videos) / len(old_videos)
        
        view_trend = 'Increasing' if avg_recent_views > avg_old_views else 'Decreasing'
        
        return {
            'view_trend': view_trend,
            'top_performing_videos': top_videos,
            'average_views': sum(v['views'] for v in video_metrics) / len(video_metrics)
        }

    def _analyze_comments_sentiment(self, comments):
        """Analyze sentiment of video comments."""
        if not comments:
            return {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'total_comments': 0,
                'negative_comments': []
            }
            
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        negative_comments = []
        
        for comment in comments:
            blob = TextBlob(comment['text'])
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                sentiments['positive'] += 1
            elif polarity < -0.1:
                sentiments['negative'] += 1
                # Store negative comments with their polarity score
                negative_comments.append({
                    'text': comment['text'],
                    'author': comment['author'],
                    'polarity': polarity,
                    'published_at': comment['publishedAt']
                })
            else:
                sentiments['neutral'] += 1
                
        total = len(comments)
        
        # Sort negative comments by polarity (most negative first) and take top 10
        negative_comments.sort(key=lambda x: x['polarity'])
        top_negative_comments = negative_comments[:10]
        
        return {
            'positive': (sentiments['positive'] / total) * 100,
            'negative': (sentiments['negative'] / total) * 100,
            'neutral': (sentiments['neutral'] / total) * 100,
            'total_comments': total,
            'negative_comments': top_negative_comments
        }

    def _analyze_video_tags(self, tags):
        """Analyze video tags and their effectiveness."""
        if not tags:
            return {
                'total_tags': 0,
                'top_tags': [],
                'tag_recommendations': ['Add relevant tags to improve visibility']
            }
            
        # Count tag frequency
        tag_counter = Counter(tags)
        
        # Get top tags
        top_tags = tag_counter.most_common(5)
        
        return {
            'total_tags': len(tags),
            'top_tags': top_tags,
            'tag_recommendations': [
                'Use specific, relevant tags',
                'Include trending topics in tags',
                'Use a mix of broad and specific tags'
            ]
        }

    def _calculate_engagement_metrics(self, video_data):
        """Calculate detailed engagement metrics."""
        views = int(video_data['viewCount'])
        likes = int(video_data['likeCount'])
        comments = int(video_data['commentCount'])
        
        if views == 0:
            return {
                'engagement_rate': 0,
                'like_rate': 0,
                'comment_rate': 0,
                'overall_score': 0
            }
            
        return {
            'engagement_rate': ((likes + comments) / views) * 100,
            'like_rate': (likes / views) * 100,
            'comment_rate': (comments / views) * 100,
            'overall_score': ((likes * 2 + comments * 3) / views) * 100
        } 