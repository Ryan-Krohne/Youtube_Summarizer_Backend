import requests
from datetime import datetime, timedelta, timezone
import os
import re
from psycopg2 import pool
import random

youtube_channels = [
  {
    "channelName": "Marques Brownlee (MKBHD)",
    "channelId": "UCBJycsmduvYEL83R_U4JriQ"
  },
  {
    "channelName": "Louis Rossmann",
    "channelId": "UCl2mFZoRqjw_ELax4Yisf6w"
  },
  {
    "channelName": "Linus Tech Tips",
    "channelId": "UCXuqSBlHAE6Xw-yeJA0Tunw"
  },
  {
    "channelName": "Veritasium",
    "channelId": "UCHnyfMqiRRG1u-2MsSQLbXA"
  },
  {
    "channelName": "Kurzgesagt – In a Nutshell",
    "channelId": "UCsXVk37bltHxD1rDPwtNM8Q"
  },
  {
    "channelName": "Ali Abdaal",
    "channelId": "UCoOae5nYA7VqaXzerajD0lg"
  },
  {
    "channelName": "How Money Works",
    "channelId": "UCkCGANrihzExmu9QiqZpPlQ"
  },
  {
    "channelName": "ColdFusion",
    "channelId": "UC4QZ_LsYcvcq7qOsOhpAX4A"
  },
  {
    "channelName": "Wendover Productions",
    "channelId": "UC9RM-iSvTu1uPJb8X5yp3EQ"
  },
  {
    "channelName": "RealLifeLore",
    "channelId": "UCP5tjEmvPItGyLhmjdwP7Ww"
  },
  {
    "channelName": "The Food Theorists",
    "channelId": "UCHYoe8kQ-7Gn9ASOlmI0k6Q"
  }
]

DATABASE_URL = os.getenv("YOUTUBE_STATISTICS_DB_URL")

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)

youtube_data_key = os.getenv("youtube_data_api_key")

#100 units per search (expensive)
def get_top_videos(channel_id, max_results=3):
    one_month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds").replace('+00:00', 'Z')
    url = 'https://youtube.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'channelId': channel_id,
        'maxResults': max_results,
        'order': 'viewCount',
        'publishedAfter': one_month_ago,
        'type': 'video',
        'key': youtube_data_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    video_ids = [item['id']['videoId'] for item in data.get('items', [])]
    return video_ids

#1 unit per call (cheap)
def get_video_details(video_ids):
    if isinstance(video_ids, str):
        video_ids = [video_ids]  # wrap single ID into a list

    url = 'https://youtube.googleapis.com/youtube/v3/videos'
    params = {
        'part': 'snippet,contentDetails,statistics',
        'id': ','.join(video_ids),
        'key': youtube_data_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        content_details = item.get('contentDetails', {})

        results.append({
            "id": item.get("id"),
            "title": snippet.get("title"),
            "publishedAt": snippet.get("publishedAt"),
            "channelTitle": snippet.get("channelTitle"),
            "channelId": snippet.get("channelId"),
            "viewCount": stats.get("viewCount"),
            "likeCount": stats.get("likeCount"),
            "commentCount": stats.get("commentCount"),
            "duration": content_details.get("duration")  # ISO 8601 format
        })

    return results

def parse_duration(iso_duration):
    """Convert ISO 8601 YouTube duration (PT#M#S) to total minutes."""
    match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return 0
    minutes = int(match.group(1) or 0)
    seconds = int(match.group(2) or 0)
    return minutes + seconds / 60  # returns float minutes

def daily_trending_videos(channels=None, min_duration_minutes=4, top_x_per_channel=3):
    channels_to_use = channels or youtube_channels  # fallback to default global list
    all_videos = []

    for channel in channels_to_use:
        channel_id = channel["channelId"]
        top_video_ids = get_top_videos(channel_id, max_results=top_x_per_channel)

        for vid_id in top_video_ids:
            details_list = get_video_details(vid_id)
            if not details_list:
                continue

            details = details_list[0]
            duration_minutes = parse_duration(details["duration"])

            if duration_minutes >= min_duration_minutes:
                video_info = {
                    "id": vid_id,
                    "title": details["title"],
                    "channelTitle": details.get("channelTitle", channel["channelName"]),
                    "channel_id": details.get("channelId") or channel["channelId"],
                    "duration_minutes": round(duration_minutes, 2),
                    "views": int(details.get("viewCount") or 0),
                    "likes": int(details.get("likeCount") or 0),
                    "comments": int(details.get("commentCount") or 0),
                    "published_at": details.get("publishedAt") or datetime.now(timezone.utc).isoformat()
                }
                all_videos.append(video_info)

    all_videos.sort(key=lambda x: x["views"], reverse=True)
    return all_videos

def insert_trending_videos(video_list):
    """
    Insert or update a list of trending videos into the database using connection pooling.
    :param video_list: List of dictionaries from daily_trending_videos()
    """
    if not video_list:
        return

    conn = None
    try:
        # Get a connection from the pool
        conn = connection_pool.getconn()
        cur = conn.cursor()

        for video in video_list:
            cur.execute("""
                INSERT INTO trending_videos 
                    (video_id, title, channel_id, channel_name, duration_minutes, views, likes, comments, published_at, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (video_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    channel_name = EXCLUDED.channel_name,
                    channel_id = EXCLUDED.channel_id,
                    duration_minutes = EXCLUDED.duration_minutes,
                    views = EXCLUDED.views,
                    likes = EXCLUDED.likes,
                    comments = EXCLUDED.comments,
                    fetched_at = EXCLUDED.fetched_at
            """, (
                video["id"],
                video["title"],
                video.get("channel_id"),  # if you store channel_id
                video["channelTitle"],       # channel_name
                video["duration_minutes"],
                video.get("views", 0),
                video.get("likes", 0),
                video.get("comments", 0),
                video.get("published_at"),   # optional
                datetime.now(timezone.utc)
            ))

        conn.commit()
        cur.close()
    except Exception as e:
        print("Error inserting trending videos:", e)
        if conn:
            conn.rollback()
    finally:
        if conn:
            # Return connection to the pool
            connection_pool.putconn(conn)

def fetch_and_store_trending(youtube_channels, num_channels=5, min_duration=4, top_x=2):
    
    sampled_channels = random.sample(youtube_channels, k=min(num_channels, len(youtube_channels)))

    trending = daily_trending_videos(sampled_channels, min_duration, top_x)
    
    print(trending)

    insert_trending_videos(trending)

if __name__ == "__main__":
    fetch_and_store_trending(youtube_channels, 5)