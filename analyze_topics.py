from datetime import datetime, timezone

from bertopic import BERTopic
from pymongo import MongoClient
import certifi

from secrets_loader import get_mongo_connection_string


# --- CONNECT ---
client = MongoClient(get_mongo_connection_string(), tlsCAFile=certifi.where())
db = client["youtube_analytics"]
collection = db["videos"]
assets = db["app_assets"]


def run_semantic_analysis():
    print("🧠 LOADING DATA FOR DEEP INTEL (BERTopic Engine)...")

    # 1. Fetch only videos that have a valid 'clean_title'
    cursor = collection.find({"clean_title": {"$ne": ""}})
    videos = list(cursor)

    # Extract just the text for training
    docs = [v["clean_title"] for v in videos]
    print(
        f"   > Training model on {len(docs)} documents. (This may take 1-2 minutes...)"
    )

    # 2. Initialize and Train BERTopic
    # 'all-MiniLM-L6-v2' is the standard for speed/accuracy balance
    topic_model = BERTopic(embedding_model="all-MiniLM-L6-v2", verbose=True)
    topics, probs = topic_model.fit_transform(docs)

    # 3. Get Topic Info
    freq = topic_model.get_topic_info()
    print("\n📊 TOPIC DISCOVERY REPORT:")
    print(freq.head(10))  # Print top 10 discovered niches

    # 4. Generate the "Galaxy" Map
    print("\n   > Generating Interactive Map...")
    fig = topic_model.visualize_topics()
    fig.write_html("chart_topic_galaxy.html")
    print("     ✅ Saved: chart_topic_galaxy.html")

    with open("chart_topic_galaxy.html", "r", encoding="utf-8") as f:
        galaxy_html = f.read()
    assets.update_one(
        {"_id": "topic_galaxy"},
        {
            "$set": {
                "html": galaxy_html,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    print("     ✅ Stored galaxy map HTML in MongoDB (app_assets.topic_galaxy)")

    # 5. WRITE BACK TO MONGODB (The "Enrichment" Step)
    print("\n💾 ENRICHING DATABASE WITH TOPIC IDs...")

    updates = 0
    # We zip the videos with their discovered topics to update them
    for i, video in enumerate(videos):
        topic_id = topics[i]

        # -1 means "Outlier" (No clear topic). We skip those.
        if topic_id != -1:
            # Get the human-readable name (e.g., "0_minecraft_hardcore_survival")
            # BERTopic returns a list of tuples, we just want the name of the topic
            topic_info = topic_model.get_topic(topic_id)
            if topic_info:
                # Construct a label from the top 3 words
                top_words = "_".join([word[0] for word in topic_info[:3]])
                topic_label = f"{topic_id}_{top_words}"

                collection.update_one(
                    {"_id": video["_id"]},
                    {"$set": {"topic_id": int(topic_id), "topic_label": topic_label}},
                    upsert=True,
                )
                updates += 1

    print(
        f"✅ DATABASE UPDATE COMPLETE. {updates} videos now have 'Semantic Intelligence'."
    )


if __name__ == "__main__":
    run_semantic_analysis()
