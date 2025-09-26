import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Target characters
TARGET_CHARACTERS = {
    "tywin_lannister": {
        "names": ["Tywin", "Lord Tywin", "Tywin Lannister", "Lord Lannister"],
        "show": "Game of Thrones",
        "context_clues": ["Father", "my lord"]
    },
    "chuck_mcgill": {
        "names": ["Chuck", "Charles McGill", "Charles", "McGill"],
        "show": "Better Call Saul",
        "context_clues": ["Brother", "Chuck"]
    },
    "general_partagaz": {
        "names": ["Partagaz", "Major Partagaz", "General"],
        "show": "Andor",
        "context_clues": ["General", "Sir"]
    },
    "logan_roy": {
        "names": ["Logan", "Logan Roy", "Mr. Roy"],
        "show": "Succession",
        "context_clues": ["Dad", "Father", "Pop"]
    }
}

# Scraping sources
SOURCES = {
    "scripts": [
        "https://springfieldspringfield.co.uk",
        "https://8flix.com",
        "https://subslikescript.com",
        "https://scrapsfromtheloft.com",
        "https://imsdb.com",
        "https://transcripts.foreverdreaming.org",
        "https://tvshowtranscripts.ourboard.org"
    ],
    "subtitles": [
        "https://www.opensubtitles.org",
        "https://subscene.com",
        "https://www.podnapisi.net",
        "https://yifysubtitles.ch"
    ],
    "books": [
        "https://z-lib.io",  # Use current mirrors
        "https://libgen.rs",
        "https://libgen.is",
        "https://archive.org",
        "https://www.gutenberg.org"
    ]
}

# Proxy configuration
PROXY_CONFIG = {
    "providers": {
        "brightdata": os.getenv("BRIGHTDATA_PROXY"),
        "smartproxy": os.getenv("SMARTPROXY_PROXY"),
        "proxy_cheap": os.getenv("PROXYCHEAP_PROXY")
    },
    "rotation": "per_request",
    "timeout": 30,
    "max_retries": 10,
    "backoff": False
}

# Anti-detection settings
STEALTH_CONFIG = {
    "headless": False,  # Run with GUI for better evasion
    "disable_blink": True,
    "random_viewport": True,
    "random_user_agent": True,
    "block_webrtc": True,
    "spoof_canvas": True,
    "spoof_webgl": True,
    "spoof_timezone": True,
    "mouse_movements": True,
    "typing_delays": True
}

# Captcha solving
CAPTCHA_CONFIG = {
    "2captcha_key": os.getenv("CAPTCHA_API_KEY"),
    "anticaptcha_key": os.getenv("ANTICAPTCHA_KEY"),
    "timeout": 120,
    "retry": 3
}

# Database configuration - Simple SQLite, no setup needed
DATABASE_CONFIG = {
    "sqlite": {
        "path": os.getenv("SQLITE_PATH", "data/moff_tarkin.db")
    }
}

# Concurrency settings
SCRAPING_CONFIG = {
    "max_concurrent": 20,
    "batch_size": 100,
    "queue_timeout": 300,
    "worker_timeout": 600
}

# User agents pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]