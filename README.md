# 🚀 YouTube Intelligence Engine

**A Military-Grade AI System for Content Strategy & Viral Prediction.**

This application moves beyond basic keyword research. It uses **Vector Databases**, **Semantic Clustering (BERTopic)**, and **Multimodal AI (Llama 4 Vision)** to analyze thousands of videos, identify "Blue Ocean" niches, and critique thumbnails with professional design principles.

---

## 📋 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Prerequisites & Installation](#-prerequisites--installation)
3. [Configuration (The Keys)](#-configuration)
4. [Execution Sequence (How to Run)](#-execution-sequence)
5. [Automated Maintenance (GitHub Actions)](#-automated-maintenance-github-actions)
6. [Deploy on Streamlit Cloud](#-deploy-on-streamlit-cloud)

---

## 🏗️ System Architecture

The system is composed of core modules that must work in harmony:

* **`credentials.py`** *(Local Only)*: Stores sensitive API keys. **Do not commit this to GitHub.**
* **`secrets_loader.py`**: Resolves secrets from **environment variables** first, then falls back to `credentials.py` (for local development and Streamlit Cloud).
* **`config.py`**: A map of YouTube Categories to scan (e.g., Gaming, Tech, Bio-hacking).
* **`harvest_for_update.py` (The Scout)**: Scrapes YouTube API for trending videos and **smart-upserts** them to MongoDB (tracks `last_updated`, avoids duplicates).
* **`clean_data.py` (The Janitor)**: Sanitizes raw titles (removes emojis, tags) to prepare for AI training.
* **`analyze_topics.py` (The Brain)**: Uses BERTopic to cluster videos into semantic "Galaxies", saves `chart_topic_galaxy.html` locally, and **stores the galaxy map HTML in MongoDB** (`app_assets.topic_galaxy`) so the dashboard works on Streamlit Cloud without that file on disk.
* **`app.py` (The Dashboard)**: The Streamlit interface where users generate strategies, predict viral scores, and roast thumbnails. Loads the galaxy map from MongoDB first, then falls back to `chart_topic_galaxy.html` if present.

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
pip install -r requirements.txt
```

---

## 🔑 Configuration

Before running the engine, you must configure API keys.

### Option A — Local development (`credentials.py`)

1. Create a new file named **`credentials.py`** in the root folder.
2. Paste the following and replace with your actual keys:

```python
# credentials.py

# YouTube Data API v3 (Google Cloud Console)
YOUTUBE_API_KEY = "AIzaSy..."

# Groq API (Llama / vision & text for the main app)
GROQ_API_KEY = "gsk_..."

# MongoDB Atlas (read/write user)
MONGO_CONNECTION_STRING = "mongodb+srv://..."

# Optional — only if you use these scripts
# OPENAI_API_KEY = "sk-..."   # strategist_openai.py
# GEMINI_API_KEY = "AIza..."  # strategist.py, check_models.py
```

> **⚠️ SECURITY:** Never upload `credentials.py` to GitHub. It is listed in `.gitignore`.

### Option B — Environment variables (CI, Streamlit Cloud, GitHub Actions)

Set the same names as above (`MONGO_CONNECTION_STRING`, `YOUTUBE_API_KEY`, `GROQ_API_KEY`, etc.). `secrets_loader.py` reads these first.

**If your MongoDB connection string was ever committed to git, rotate the Atlas user password and update your secrets.**

---

## 🚀 Execution Sequence

Run these scripts **in order** to build or refresh the intelligence database:

### Step 1: The Harvest

Fetches channel/video data and upserts into MongoDB.

```bash
python harvest_for_update.py
```

* *Example output:* `✨ Total New Videos Discovered: …` and `📈 Total Videos Refreshed: …`

### Step 2: The Cleanup

Sanitizes titles for NLP.

```bash
python clean_data.py
```

* *Output:* `✨ SANITATION COMPLETE.`

### Step 3: The Brain (Training)

Trains BERTopic, writes `chart_topic_galaxy.html`, and syncs the HTML to MongoDB.

```bash
python analyze_topics.py
```

* *Output:* `✅ Saved: chart_topic_galaxy.html` and confirmation that the galaxy HTML was stored in MongoDB.

### Step 4: Launch Dashboard

```bash
streamlit run app.py
```

---

## 🛡️ Automated Maintenance (GitHub Actions)

The repository includes [`.github/workflows/refresh-intel.yml`](.github/workflows/refresh-intel.yml). It runs **weekly** (Sundays 06:00 UTC) and can be triggered manually (**Actions → Refresh Intel Data → Run workflow**).

**Required repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Used by |
|--------|---------|
| `MONGO_CONNECTION_STRING` | Pipeline + app |
| `YOUTUBE_API_KEY` | `harvest_for_update.py` |

The workflow runs: `harvest_for_update.py` → `clean_data.py` → `analyze_topics.py`.

**MongoDB Atlas:** allow inbound connections from GitHub-hosted runners (often simplest: temporarily allow `0.0.0.0/0` on your Atlas IP Access List for development; tighten later if needed).

---

## ☁️ Deploy on Streamlit Cloud

Deployment happens in the browser at **[share.streamlit.io](https://share.streamlit.io)**. Streamlit needs permission to read your GitHub repository (one-time authorization).

1. **Push** the latest code to GitHub (this project: **`zivanmisquitta1-sketch/YouTube_Intel`**).
2. Open **[share.streamlit.io](https://share.streamlit.io)** → **Create app** → **Yup, I have an app.**
3. Use **Paste GitHub URL** with your entrypoint, e.g.  
   `https://github.com/zivanmisquitta1-sketch/YouTube_Intel/blob/main/app.py`  
   or select the repo and set **Main file path** to **`app.py`**.
4. **Advanced settings** → set **Python** to **3.11** (optional but matches many local environments).
5. **Secrets** → paste TOML based on **[`secrets.toml.example`](secrets.toml.example)** with your real `MONGO_CONNECTION_STRING` and `GROQ_API_KEY`.
6. **Deploy.** First install can take several minutes (PyTorch, `sentence-transformers`, etc.).

Use **Manage app → Settings → Secrets** to change keys; the app restarts automatically.

**MongoDB Atlas:** allow **`0.0.0.0/0`** (or Streamlit’s outbound IPs per Atlas docs) so the cloud app can reach your cluster.

The dashboard reads the topic galaxy from **`youtube_analytics.app_assets`** (`_id: "topic_galaxy"`) after `analyze_topics.py` has run (locally or via GitHub Actions).

---

**Built with 🐍 Python, 🍃 MongoDB, and 🦙 Llama 4.**
