# Moff Tarkin - Character Scene Extraction Pipeline

Aggressive web scraping pipeline for extracting character scenes from TV scripts with advanced anti-detection features.

## Target Characters
- **Tywin Lannister** (Game of Thrones) - *0 scenes extracted*
- **Chuck McGill** (Better Call Saul) - *52 scenes extracted*
- **General Partagaz** (Andor) - *8 scenes extracted*
- **Logan Roy** (Succession) - *20 scenes extracted*

**Total: 80 scenes in database**

## Features

### Anti-Detection
- Undetected Chrome driver bypassing automation detection
- TLS fingerprint evasion
- Residential proxy rotation
- Cloudflare bypass (cloudscraper + FlareSolverr)
- Canvas/WebGL fingerprint randomization
- Human-like behavior simulation
- Captcha solving (reCAPTCHA, hCaptcha, Turnstile)

### Data Sources
- Multiple script databases (Springfield, 8FLiX, Subslikescript)
- Subtitle files (OpenSubtitles, Subscene)
- Book sources (Z-Library, Libgen, Archive.org)
- Fan wikis and transcripts

### Storage
- SQLite database (no setup required)
- Built-in caching and deduplication
- File system for raw HTML backup

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JS-heavy sites)
playwright install
```

## Configuration

1. Copy `.env.example` to `.env` (optional)
2. Add proxy credentials (optional for better success rate)
3. Add captcha solving API keys (optional for captcha bypass)

The system works out-of-the-box without any configuration. SQLite database is created automatically.

## Usage

### Test extraction for single character
```bash
python main.py --test
```

### Extract specific character
```bash
python main.py --character tywin_lannister
python main.py --character chuck_mcgill
python main.py --character general_partagaz
python main.py --character logan_roy
```

### Extract all characters
```bash
python main.py --all
```

### Override show name
```bash
python main.py --character chuck_mcgill --show "better call saul"
```

## Architecture (Cleaned)

```
moff-tarkin/
├── main.py                 # Main entry point
├── config/                 # Configuration
│   └── settings.py         # Target characters and scraping settings
├── models/                 # Data models
│   └── scene.py            # Scene and dialogue data structures
├── scrapers/               # Web scraping modules
│   ├── base_scraper.py     # Base scraper with anti-detection
│   └── script_scrapers.py  # Site-specific scrapers
├── storage/                # Database and file storage
│   └── database.py         # SQLite database management
├── utils/                  # Anti-detection utilities
│   ├── antidetect.py       # Browser fingerprinting and evasion
│   └── captcha_solver.py   # Captcha solving integration
├── data/                   # Data storage
│   └── complete_scenes.db  # SQLite database (80 scenes)
├── logs/                   # Extraction logs
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
└── .env.example            # Environment variables template
```

## Key Components

### StealthBrowser
- Undetected Chrome with stealth patches
- Playwright with stealth plugins
- Pyppeteer with evasion

### ProxyRotator
- Health checking
- Automatic rotation
- Failed proxy tracking

### CaptchaSolver
- 2captcha integration
- AntiCaptcha support
- Multiple fallback services

### CharacterSceneExtractor
- Character name matching
- Context clue detection
- Scene boundary detection

## Data Schema

```json
{
  "scene_id": "unique_id",
  "character": "chuck_mcgill",
  "show": "Better Call Saul",
  "season": 1,
  "episode": 1,
  "episode_code": "S01E01",
  "episode_title": "Uno",
  "scene_text": "...",
  "dialogue_json": "[...]",
  "location": "Law office",
  "participants": "['Chuck', 'Jimmy']",
  "source_url": "...",
  "extraction_date": "2025-09-26",
  "word_count": 3608
}
```

## Current Status

- **Database**: `data/complete_scenes.db` (1.6 MB)
- **Extracted Scenes**: 80 total
  - Chuck McGill: 52 scenes
  - Logan Roy: 20 scenes
  - General Partagaz: 8 scenes
  - Tywin Lannister: 0 scenes (extraction failed/incomplete)
- **Average Scene Length**: ~3,600 words
- **Data Quality**: Valid, real transcript data

## Performance

- 20+ concurrent scrapers
- No rate limiting between different IPs
- Aggressive retry with proxy rotation
- Response caching for deduplication
- Batch processing support

## Notes

- Bypasses robots.txt restrictions
- Ignores SSL certificate errors
- Uses residential proxies for better success rate
- Stores all raw HTML for reprocessing
- Automatic captcha solving when detected