import re
import emoji
from pymongo import MongoClient
import certifi
from credentials import MONGO_CONNECTION_STRING


# --- CONNECT ---
client = MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=certifi.where())
db = client["youtube_analytics"]
collection = db["videos"]


def clean_text(text):
    """
    Surgical cleaning of YouTube Titles.
    1. Lowercase everything.
    2. Remove Emojis.
    3. Remove things in brackets like (Official Video) or [4K].
    4. Remove pipe symbols | and dashes - that separate channel names.
    5. Remove special characters but keep spaces.
    """
    if not text:
        return ""

    # 1. Lowercase
    text = text.lower()

    # 2. Remove Emojis
    text = emoji.replace_emoji(text, replace="")

    # 3. Remove text inside brackets () and []
    # This removes "(Official Music Video)" or "[4K]" which are noise
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)

    # 4. Remove common separator symbols
    text = re.sub(r"[|\-_]", " ", text)

    # 5. Remove non-alphanumeric characters (keep numbers and spaces)
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # 6. Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def run_cleaning_protocol():
    print("🧹 STARTING DATA SANITATION PROTOCOL...")

    videos = collection.find()
    total_videos = collection.count_documents({})
    processed = 0

    for video in videos:
        original_title = video.get("title", "")

        # Run the cleaning
        cleaned_title = clean_text(original_title)

        # Update the database with the NEW field
        collection.update_one(
            {"_id": video["_id"]}, {"$set": {"clean_title": cleaned_title}}, upsert=True
        )

        processed += 1
        if processed % 100 == 0:
            print(f"   > Cleaned {processed}/{total_videos} videos...")

    print(f"\n✨ SANITATION COMPLETE. {processed} videos updated.")
    print("   Sample Check:")
    print(f"   Original: {original_title}")
    print(f"   Cleaned:  {cleaned_title}")


if __name__ == "__main__":
    run_cleaning_protocol()
