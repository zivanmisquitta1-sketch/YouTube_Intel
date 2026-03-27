from googleapiclient.discovery import build
from pymongo import MongoClient
import certifi
import isodate  # <--- NEW: To parse duration
from config import CATEGORY_MAP
from secrets_loader import get_mongo_connection_string, get_youtube_api_key


# --- SETUP ---
youtube = build("youtube", "v3", developerKey=get_youtube_api_key())
client = MongoClient(get_mongo_connection_string(), tlsCAFile=certifi.where())
db = client["youtube_analytics"]
collection = db["videos"]


def get_top_channels(category_id):
    """Scouts for the top 10 trending channels in a category."""
    print(f"   > Scouting channels...")
    try:
        request = youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            regionCode="US",
            videoCategoryId=category_id,
            maxResults=50,
        )
        response = request.execute()
    except Exception as e:
        print(f"   ⚠️  SKIPPING Category (Error: {e})")
        return []

    unique_channels = []
    seen_ids = set()

    for item in response.get("items", []):
        channel_id = item["snippet"]["channelId"]
        channel_title = item["snippet"]["channelTitle"]

        if channel_id not in seen_ids:
            unique_channels.append((channel_title, channel_id))
            seen_ids.add(channel_id)

        if len(unique_channels) >= 10:
            break

    return unique_channels


def get_channel_videos(channel_id):
    """Fetches the stats + DURATION + TAGS for the latest 50 videos."""
    # 1. Get Upload Playlist ID
    res = youtube.channels().list(id=channel_id, part="contentDetails").execute()
    playlist_id = res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 2. Get Video IDs
    res = (
        youtube.playlistItems()
        .list(playlistId=playlist_id, part="contentDetails", maxResults=50)
        .execute()
    )
    video_ids = [item["contentDetails"]["videoId"] for item in res["items"]]

    # 3. Get Video Stats AND Content Details (for Duration)
    stats_res = (
        youtube.videos()
        .list(
            id=",".join(video_ids),
            part="snippet,statistics,contentDetails",  # <--- NEW PART ADDED
        )
        .execute()
    )

    cleaned_videos = []
    for item in stats_res["items"]:
        try:
            # Stats
            views = int(item["statistics"].get("viewCount", 0))
            likes = int(item["statistics"].get("likeCount", 0))
            comments = int(item["statistics"].get("commentCount", 0))

            # Duration Processing
            raw_duration = item["contentDetails"]["duration"]
            duration_sec = isodate.parse_duration(raw_duration).total_seconds()

            # Logic: Is it a Short? (< 61 seconds to be safe)
            is_short = True if duration_sec < 61 else False

            video = {
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],  # <--- NEW
                "tags": item["snippet"].get("tags", []),  # <--- NEW
                "channel": item["snippet"]["channelTitle"],
                "views": views,
                "likes": likes,
                "comments": comments,
                "published_at": item["snippet"]["publishedAt"],
                "duration_seconds": duration_sec,  # <--- NEW
                "is_short": is_short,  # <--- NEW
            }
            cleaned_videos.append(video)
        except Exception as e:
            continue

    return cleaned_videos


def run_harvest():
    print("🚀 STARTING HARVEST V2.0 (SMART UPDATE)...")

    total_new = 0
    total_updated = 0

    for cat_name, cat_id in CATEGORY_MAP.items():
        print(f"\n📂 Processing Category: {cat_name}")
        channels = get_top_channels(cat_id)

        for channel_name, channel_id in channels:
            print(f"   --> Scanning: {channel_name}")
            videos = get_channel_videos(channel_id)

            new_count = 0
            upd_count = 0

            for video in videos:
                video["category"] = cat_name

                # THE SMART UPSERT
                result = collection.update_one(
                    {"video_id": video["video_id"]},
                    {
                        "$set": video,
                        "$currentDate": {"last_updated": True},  # <--- STAMPS THE TIME
                    },
                    upsert=True,
                )

                # Check if it was an Insert or an Update
                if result.matched_count > 0:
                    upd_count += 1
                else:
                    new_count += 1

            total_new += new_count
            total_updated += upd_count
            print(f"       ✅ {new_count} New | ♻️ {upd_count} Refreshed")

    print(f"\n🏁 HARVEST COMPLETE!")
    print(f"   ✨ Total New Videos Discovered: {total_new}")
    print(f"   📈 Total Videos Refreshed:      {total_updated}")


if __name__ == "__main__":
    run_harvest()
