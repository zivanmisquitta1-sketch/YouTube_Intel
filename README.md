# 🚀 YouTube Intelligence Engine

**A Military-Grade AI System for Content Strategy & Viral Prediction.**

This application moves beyond basic keyword research. It uses **Vector Databases**, **Semantic Clustering (BERTopic)**, and **Multimodal AI (Llama 4 Vision)** to analyze thousands of videos, identify "Blue Ocean" niches, and critique thumbnails with professional design principles.

---

## 📋 Table of Contents

1. [System Architecture]
2. [Prerequisites & Installation]
3. [Configuration (The Keys)]
4. [Execution Sequence (How to Run)]
5. [Maintenance (Updating)]

---

## 🏗️ System Architecture

The system is composed of 6 core modules that must work in harmony:

* **`credentials.py`** *(Local Only)*: Stores sensitive API keys. **Do not commit this to GitHub.**
* **`config.py`**: A map of YouTube Categories to scan (e.g., Gaming, Tech, Bio-hacking).
* **`harvest.py` (The Scout)**: Scrapes YouTube API for trending videos and "Upserts" them to MongoDB to prevent duplicates.
* **`clean_data.py` (The Janitor)**: Sanitizes raw titles (removes emojis, tags) to prepare for AI training.
* **`analyze_topics.py` (The Brain)**: Uses BERTopic to cluster videos into semantic "Galaxies" and generates an interactive map.
* **`app.py` (The Dashboard)**: The Streamlit interface where users generate strategies, predict viral scores, and roast thumbnails.

---

## 🛠️ Prerequisites & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/YouTube_Intel.git
cd YouTube_Intel

```

### 2. Set Up Virtual Environment

It is recommended to run this project in an isolated environment.

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate

```

### 3. Install Dependencies

```bash
pip install streamlit pandas pymongo certifi openai sentence-transformers scikit-learn google-api-python-client isodate bertopic emoji

```

---

## 🔑 Configuration

Before running the engine, you must create the **Control Center** to hold your API keys.

1. Create a new file named **`credentials.py`** in the root folder.
2. Paste the following code inside and replace with your actual keys:

```python
# credentials.py

# 1. YouTube Data API v3 (From Google Cloud Console)
YOUTUBE_API_KEY = "AIzaSy..."

# 2. Groq API Key (For Llama 4 Vision & Text)
GROQ_API_KEY = "gsk_..."

# 3. MongoDB Connection String (From MongoDB Atlas)
# Ensure your user has read/write permissions
MONGO_CONNECTION_STRING = "mongodb+srv://..."

```

> **⚠️ SECURITY WARNING:** Never upload `credentials.py` to GitHub. It is already added to `.gitignore` for your safety.

---

## 🚀 Execution Sequence

To build the intelligence database, you must run the scripts **in this specific order**:

### Step 1: The Harvest

Runs the scraper to populate your MongoDB vault. It fetches the top 50 videos from every category in `config.py`.

```bash
python harvest.py

```

* *Output:* `✅ 50 New | ♻️ 12 Refreshed`

### Step 2: The Cleanup

Sanitizes the data (removes emojis, brackets) so the AI can understand the text.

```bash
python clean_data.py

```

* *Output:* `✨ SANITATION COMPLETE.`

### Step 3: The Brain (Training)

Trains the BERTopic model on your new data. This creates the "Niche Galaxy" map and tags every video with a topic ID.

```bash
python analyze_topics.py

```

* *Output:* `✅ Saved: chart_topic_galaxy.html`

### Step 4: Launch Dashboard

Starts the web interface.

```bash
streamlit run app.py

```

* *Result:* Opens the app in your default browser.

---

## 🛡️ Maintenance

To keep your "Trend Radar" accurate:

1. **Weekly Ritual:** Run `harvest.py`, `clean_data.py` and `analyze_topics.py` once a week.
2. **Upsert Logic:** The harvester automatically detects if a video already exists. If it does, it updates the view count (velocity) instead of creating a duplicate.

---

**Built with 🐍 Python, 🍃 MongoDB, and 🦙 Llama 4.**