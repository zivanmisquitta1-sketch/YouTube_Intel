import streamlit as st
import pandas as pd
from pymongo import MongoClient
import certifi
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit.components.v1 as components
import datetime
import math
import base64
from secrets_loader import get_groq_api_key, get_mongo_connection_string


# --- PAGE SETUP ---
st.set_page_config(page_title="YouTube Intel Engine", layout="wide", page_icon="🚀")


# --- CACHED RESOURCES ---
@st.cache_resource
def init_connections():
    client = MongoClient(get_mongo_connection_string(), tlsCAFile=certifi.where())
    ai_client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=get_groq_api_key(),
    )
    return client, ai_client


@st.cache_resource
def load_search_engine():
    """Load the brain for the Semantic Router"""
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


@st.cache_data
def load_topics(_client):
    db = _client["youtube_analytics"]
    collection = db["videos"]
    topics = list(
        collection.aggregate(
            [
                {"$match": {"topic_label": {"$exists": True}}},
                {"$group": {"_id": "$topic_label", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
        )
    )
    return [t["_id"] for t in topics]


# Initialize
client, ai_client = init_connections()
search_model = load_search_engine()
available_topics = load_topics(client)

if "topic_embeddings" not in st.session_state:
    st.session_state.topic_embeddings = search_model.encode(available_topics)

# --- HELPER FUNCTIONS ---


def encode_image(uploaded_file):
    """Converts uploaded image to Base64 for the AI Vision model"""
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def check_relevance_with_ai(user_query, matched_topic):
    """
    Asks Llama 3: Is this database topic a good proxy for the user's idea?
    """
    system_prompt = """
    You are a Data Relevance Validator.
    Your Job: Determine if the Database Topic is a valid proxy/reference for the User Query.
    
    Rules:
    - If the topics are in the same genre/niche (e.g. "Minecraft" vs "Roblox"), output YES.
    - If the topics are unrelated (e.g. "Cooking" vs "Gaming"), output NO.
    - Be permissive with "Vibes" (e.g. "Funny Skits" matches "Comedy").
    
    OUTPUT FORMAT: 
    Start with either "YES" or "NO", then a brief explanation.
    """

    user_prompt = f"User Query: '{user_query}'\nDatabase Topic: '{matched_topic}'"

    try:
        response = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content
        # Check if the AI said YES
        is_relevant = content.strip().upper().startswith("YES")
        return is_relevant, content
    except:
        # If API fails, default to allowing it
        return True, "AI Validation Failed (Defaulting to Allow)"


def calculate_niche_velocity(videos):
    """
    Calculates 'Heat' based on Velocity (if dates exist) or Raw Volume (Logarithmic).
    """
    if not videos:
        return 0, "Unknown"

    # Get current time
    now = datetime.datetime.now()

    total_velocity = 0
    valid_videos = 0

    for v in videos:
        try:
            # Attempt to parse date (Handle multiple formats)
            pub_date = v.get("publishedAt", "")
            if pub_date:
                # If it's already a datetime object (from Mongo)
                if isinstance(pub_date, datetime.datetime):
                    pub_dt = pub_date
                # If it's a string (e.g. '2023-01-01T...')
                elif isinstance(pub_date, str):
                    # Cut off time info if needed (simple parse)
                    pub_dt = datetime.datetime.strptime(pub_date[:10], "%Y-%m-%d")
                else:
                    continue  # Unknown format

                days_old = (now - pub_dt).days
                if days_old < 1:
                    days_old = 1

                velocity = v["views"] / days_old
                total_velocity += velocity
                valid_videos += 1
        except:
            continue

    # --- FALLBACK: LOGARITHMIC VOLUME SCALE ---
    if valid_videos == 0:
        # If no dates, we measure "Niche Depth" (Raw Size)
        avg_views = sum(v["views"] for v in videos) / len(videos)

        # Log Logic:
        # 10k views -> Score 40
        # 100k views -> Score 50
        # 1M views -> Score 60
        # 100M views -> Score 80+
        if avg_views < 1000:
            return 10, "❄️ Cold (Micro-Niche)"

        # Calculate Log10 score (Base score for 1M is ~60)
        log_score = int(math.log10(avg_views) * 10)
        final_score = min(max(log_score, 10), 99)  # Cap at 99

        return final_score, "🗿 Evergreen (High Volume)"

    # --- REAL VELOCITY SCORING ---
    avg_velocity = total_velocity / valid_videos

    # Velocity tiers (Views Per Day)
    if avg_velocity > 10000:
        return 100, "🔥 INFERNO (Trending Now)"
    if avg_velocity > 5000:
        return 90, "🔥 Hot"
    if avg_velocity > 1000:
        return 75, "📈 Rising"
    if avg_velocity > 100:
        return 50, "🐢 Steady"
    return 25, "❄️ Cold"


def calculate_viral_score(user_query, topic_confidence, niche_velocity):
    """
    Predicts viral potential (0-100)
    Formula: (Confidence * 0.4) + (Velocity * 0.4) + (Power Words * 0.2)
    """
    # 1. Power Word Bonus
    power_words = [
        "100 days",
        "tutorial",
        "explained",
        "only",
        "vs",
        "impossible",
        "secret",
        "hack",
        "how to",
    ]
    word_bonus = 0
    for w in power_words:
        if w in user_query.lower():
            word_bonus += 10
    word_bonus = min(word_bonus, 20)  # Max 20 points

    # 2. Weighted Score
    # We cap confidence at 100 (it might be higher from vector math)
    safe_conf = min(topic_confidence, 100)

    final_score = (safe_conf * 0.4) + (niche_velocity * 0.4) + word_bonus

    # 3. Tier Ranking
    if final_score > 85:
        rank = "S-Tier (Viral Goldmine)"
    elif final_score > 70:
        rank = "A-Tier (Strong Contender)"
    elif final_score > 50:
        rank = "B-Tier (Consistent)"
    else:
        rank = "C-Tier (High Risk)"

    return int(final_score), rank


# --- THE ROUTER LOGIC ---
def find_best_niche(user_query):
    # 1. Encode User Query
    query_embedding = search_model.encode([user_query])

    # 2. Calculate Similarity
    similarities = cosine_similarity(query_embedding, st.session_state.topic_embeddings)

    # 3. Identify Best Match
    best_idx = similarities.argmax()
    best_topic = available_topics[best_idx]
    confidence = similarities[0][best_idx] * 100

    return best_topic, confidence


# --- UI LAYOUT ---
st.title("🚀 YouTube Intelligence Engine")
st.markdown("---")

col1, col2 = st.columns([2, 1])
with col1:
    user_query = st.text_input(
        "💡 Describe your video idea:",
        placeholder="e.g., 'Funny moments in Minecraft survival'",
    )
with col2:
    # We update session state immediately on change so we don't lose the selection
    content_type = st.radio(
        "Format Strategy:",
        ["Shorts (Viral Loop)", "Long-Form (Storytelling)"],
        index=0,
        key="content_type_radio",
    )

if st.button("Generate Professional Strategy", type="primary"):

    if not user_query:
        st.warning("⚠️ Please describe your video idea first.")
        st.stop()

    # Save context for persistence
    st.session_state.content_type_selection = content_type

    # 1. RETRIEVAL
    with st.spinner("🔍 Scanning database..."):
        best_topic, confidence = find_best_niche(user_query)

    # 2. VALIDATION
    if confidence > 20:
        with st.spinner(f"🤔 Validating match: '{best_topic}'..."):
            is_relevant, reason = check_relevance_with_ai(user_query, best_topic)
    else:
        is_relevant = False
        reason = "Confidence score too low for AI validation."

    # 3. METRICS & DASHBOARD
    is_blue_ocean = False
    context_text = ""

    if is_relevant:
        # Fetch Data First
        collection = client["youtube_analytics"]["videos"]
        cursor = (
            collection.find({"topic_label": best_topic}).sort("views", -1).limit(10)
        )
        examples = list(cursor)

        # --- NEW: CALCULATE METRICS ---
        velocity_score, velocity_label = calculate_niche_velocity(examples)
        viral_score, viral_rank = calculate_viral_score(
            user_query, confidence, velocity_score
        )

        # Save metrics to session state so they persist when we click 'Roast'
        st.session_state.dashboard_metrics = {
            "confidence": confidence,
            "velocity_label": velocity_label,
            "velocity_score": velocity_score,
            "viral_score": viral_score,
            "viral_rank": viral_rank,
            "reason": reason,
            "best_topic": best_topic,
        }

        context_text = "\n".join(
            [f"- {v['title']} ({v['views']:,} views)" for v in examples[:5]]
        )
    else:
        is_blue_ocean = True
        st.warning(
            f"⚠️ **Data Gap:** '{best_topic}' not relevant. Switching to Blue Ocean Mode."
        )
        context_text = "NO INTERNAL DATA. USE GENERAL KNOWLEDGE."

        # Default metrics for Blue Ocean
        st.session_state.dashboard_metrics = {
            "confidence": 0,
            "velocity_label": "Unknown",
            "velocity_score": 0,
            "viral_score": 45,
            "viral_rank": "Blue Ocean (Unknown Territory)",
            "reason": "Blue Ocean",
            "best_topic": "General",
        }

    # 4. GENERATE STRATEGY
    if "Shorts" in content_type:
        system_role = (
            "You are a YouTube Shorts Expert. Prioritize: 60s retention, Looping hooks."
        )
        thumbnail_prompt = "Describe the FIRST FRAME (Visual Hook) to stop the scroll."
        structure_prompt = "Pacing (0-60s) with a specific Loop transition."
        tags_prompt = "Suggest relevent tags for better wide-spread reach (#shorts, #podcast, #gaming, #motivation, etc.)"
    else:
        system_role = (
            "You are a Long-Form Strategist. Prioritize: Click-Through Rate (CTR)."
        )
        thumbnail_prompt = "Describe a High-CTR Thumbnail (Contrast, Emotion)."
        structure_prompt = "Story Structure (Intro, Conflict, Payoff)."
        tags_prompt = "Suggest relevent tags for better wide-spread reach (#minecraft, #celebrity, #ronaldo, #scam, #gossip, etc.)"

    # 5. GENERATE STRATEGY
    prompt = f"""
    USER REQUEST: {user_query}
    MODE: {"BLUE OCEAN" if is_blue_ocean else "DATA-BACKED (Proxy Strategy)"}
    MATCHED DATABASE TOPIC: {best_topic}
    
    CONTEXT DATA:
    {context_text}
    
    TASK: Generate a {content_type} strategy.
    
    CRITICAL INSTRUCTION:
    - If DATA-BACKED: Explicitly mention how the user can apply the principles from '{best_topic}' to their idea (Transfer Learning).
    - If BLUE OCEAN: Ignore the database and use general excellence standards.
    
    OUTPUT FORMAT (Markdown):
    1. **3 Viral Title Hooks**
    2. **Visual Strategy**: {thumbnail_prompt}
    3. **Content Gap**: {"Global market gap" if is_blue_ocean else "What is missing in your vault data?"}
    4. **Script Outline**: {structure_prompt}
    5. **Potential Tags**: {tags_prompt}
    """

    with st.spinner("🧠 Drafting Strategy..."):
        try:
            completion = ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            # Save strategy to session state
            st.session_state.generated_strategy = completion.choices[0].message.content
        except Exception as e:
            st.error(f"AI Error: {e}")

# --- DISPLAY RESULTS (PERSISTENT LAYER) ---
# This block runs on every refresh if data exists in session_state

if "dashboard_metrics" in st.session_state:
    metrics = st.session_state.dashboard_metrics

    st.markdown("### 📊 Viral Prediction Engine")
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            label="🎯 AI Confidence",
            value=f"{metrics['confidence']:.1f}%",
            delta="Match Quality",
        )
    with m2:
        st.metric(
            label="🔥 Niche Velocity",
            value=metrics["velocity_label"],
            delta=f"{metrics['velocity_score']}/100 Heat",
        )
    with m3:
        # Color code the viral score
        score_color = "normal"
        if metrics["viral_score"] > 80:
            score_color = "off"  # Streamlit hack for 'green' isn't direct, but high numbers look good
        st.metric(
            label="🚀 Viral Potential",
            value=f"{metrics['viral_score']}/100",
            delta=metrics["viral_rank"],
        )

    st.progress(metrics["viral_score"] / 100)

    with st.expander("🔎 Why this score?"):
        st.write(
            f"**Topic Match:** {metrics['confidence']:.1f}% (AI identified '{metrics["best_topic"]}')"
        )
        st.write(
            f"**Niche Heat:** {metrics["velocity_label"]} (Based on recent view velocity)"
        )
        st.write(f"**Validation:** {metrics["reason"]}")

    st.markdown("---")


if "generated_strategy" in st.session_state:
    st.subheader("📋 The Blueprint")
    st.markdown(st.session_state.generated_strategy)

    # --- SUB-PHASE 2: THE THUMBNAIL EVALUATOR (NEW FEATURE) ---
    # Only show if Long-Form was selected
    selected_mode = st.session_state.get(
        "content_type_selection", "Shorts"
    )  # Default to Shorts to be safe

    if "Long-Form" in selected_mode:
        st.markdown("---")
        st.header("📸 Thumbnail Evaluator (Beta)")
        st.caption(
            "Upload your thumbnail drafts to get AI-powered feedback on CTR potential."
        )

        eval_mode = st.radio(
            "Select Mode:", ["🔥 Roast & Fix", "⚔️ A/B Battle"], horizontal=True
        )

        if eval_mode == "🔥 Roast & Fix":
            uploaded_file = st.file_uploader(
                "Upload your Draft Thumbnail", type=["jpg", "png", "jpeg"]
            )

            if uploaded_file and st.button("Roast My Thumbnail"):
                with st.spinner("👀 Analyzing pixels..."):
                    base64_image = encode_image(uploaded_file)
                    vision_prompt = """
                    You are a harsh but helpful YouTube Thumbnail Critic. 
                    Analyze this image for: 
                    1. Text Legibility (Can it be read on mobile?)
                    2. Emotion/Face (Is it expressive?)
                    3. Contrast (Does it pop?)
                    4. Irresistible Hook (Will it hook the viewer at first glance?)
                    
                    OUTPUT:
                    - **Score:** X/10
                    - **The Roast:** One ruthless and funny sentence about what is wrong.
                    - **The Fix:** Detailed and specific instructions to improve CTR. Almost like you are guiding the user on how to create an unmissable thumbnail.
                    """

                    try:
                        response = ai_client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": vision_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/jpeg;base64,{base64_image}"
                                            },
                                        },
                                    ],
                                }
                            ],
                        )
                        st.success("Analysis Complete!")
                        st.markdown(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Vision API Error: {e}")

        elif eval_mode == "⚔️ A/B Battle":
            c1, c2 = st.columns(2)
            with c1:
                img_a = st.file_uploader("Thumbnail A", type=["jpg", "png"])
            with c2:
                img_b = st.file_uploader("Thumbnail B", type=["jpg", "png"])

            if img_a and img_b and st.button("Start Battle"):
                with st.spinner("⚔️ Simulating CTR Battle..."):
                    b64_a = encode_image(img_a)
                    b64_b = encode_image(img_b)
                    battle_prompt = """
                    Compare these two YouTube thumbnails. 
                    Which one will have a higher Click-Through Rate (CTR)? 
                    Explain why based on color, contrast, hook-factor, and curiosity gap. 
                    
                    OUTPUT:
                    - **Winner:** (A or B)
                    - **Reasoning:** Why it won.
                    """

                    try:
                        response = ai_client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": battle_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/jpeg;base64,{b64_a}"
                                            },
                                        },
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/jpeg;base64,{b64_b}"
                                            },
                                        },
                                    ],
                                }
                            ],
                        )
                        # st.balloons()
                        st.markdown(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Vision API Error: {e}")


# ROW 3: The Map (Always visible for exploration)
st.markdown("---")
with st.expander("🌌 Explore the Galaxy Map (Visual Database)", expanded=False):
    html_data = None
    try:
        doc = client["youtube_analytics"]["app_assets"].find_one(
            {"_id": "topic_galaxy"}
        )
        if doc and doc.get("html"):
            html_data = doc["html"]
    except Exception:
        pass
    if not html_data:
        try:
            with open("chart_topic_galaxy.html", "r", encoding="utf-8") as f:
                html_data = f.read()
        except OSError:
            pass
    if html_data:
        components.html(html_data, height=600, scrolling=True)
    else:
        st.write("Map not generated yet.")
