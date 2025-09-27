# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

moff-tarkin is an RL-based character decision-making AI training pipeline. **Currently in data extraction stage only** - the codebase focuses on scraping and extracting character scenes from TV/movie scripts. The goal is training a base model to embody strategic thinking patterns of fictional characters for business decision-making applications, capturing complete thought processes rather than dialogue mimicry.

Target characters:
- Tywin Lannister (Game of Thrones) - ruthless long-term thinking
- Chuck McGill (Better Call Saul) - rigid principled reasoning
- General Partagaz (Andor) - methodical operational control
- Logan Roy (Succession) - aggressive power dynamics

## Common Commands

### Running the extraction pipeline
```bash
# Extract scenes for specific character
python main.py --character tywin_lannister

# Extract all characters
python main.py --all

# Test extraction
python main.py --test
```

### Database operations
```bash
# Check scene counts by character
sqlite3 data/complete_scenes.db "SELECT character, COUNT(*) FROM complete_scenes GROUP BY character;"

# View recent extractions
sqlite3 data/complete_scenes.db "SELECT scene_id, character, episode_title FROM complete_scenes ORDER BY extraction_date DESC LIMIT 10;"
```

### Development setup
```bash
# Create virtual environment (if needed)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers if using playwright
playwright install chromium
```

## Architecture

### Data Pipeline Flow
1. **Scene Extraction** (`main.py` → `scrapers/script_scrapers.py`) ✅ IMPLEMENTED
   - Scrapes scripts from multiple sources using anti-detection techniques
   - Extracts character-specific scenes with dialogue and context
   - Stores raw scenes in SQLite database

2. **Decision Trace Generation** (planned)
   - Takes raw scenes from database
   - Uses LLM to extract decision points and synthesize internal monologue
   - Formats as: situation → internal monologue → decision → justification
   - Generates character-consistent decision traces for training

3. **Training Pipeline** (planned)
   - MoE-style RL approach with learnable routers (model determines its own expert activations)
   - Multiple experts activated per forward pass with weighted contributions
   - GRPO-based training with character-specific reward functions
   - Constitutional AI using detailed character behavioral specifications for critique
   - LLM-as-judge evaluation using character specs rather than general prompts

### Key Components

- **`scrapers/`**: Web scraping with anti-detection (undetected-chromedriver, playwright, stealth techniques)
- **`storage/database.py`**: SQLite storage manager for scenes
- **`models/scene.py`**: Scene data models and collections
- **`config/settings.py`**: Character definitions, scraping sources, anti-detection configs

### Database Schema

`complete_scenes` table stores extracted scenes with:
- scene_id, character, show, season, episode info
- scene_text (raw), dialogue_json (structured)
- location, participants, source_url
- extraction metadata

## Current Status

**Data Extraction Phase** ✅ - This is where the project currently stands:
- Scene extraction pipeline is built and functional
- 113 scenes extracted across characters:
  - Chuck McGill: 52 scenes
  - Tywin Lannister: 33 scenes
  - Logan Roy: 20 scenes
  - General Partagaz: 8 scenes
- Focus is on gathering raw scene data from various sources

**Not Yet Implemented:**
- Decision trace generation from scenes
- Training pipeline with MoE-style RL approach
- Character-specific reward functions and behavioral specifications
- Constitutional AI critique system
- LLM-as-judge evaluation framework
- Context length management for training data
- Scalable data generation pipeline for decision traces

## Key Training Considerations

### Architecture Design
- **Learnable Routers**: Let the model determine its own expert activations, not manual assignment
- **Multi-Expert Activation**: Multiple experts contribute with learned weights per forward pass
- **No Pre-trained Router Interference**: Avoid modifying existing router weights which would break the model

### Training Challenges
- **Character Consistency**: Maintaining authentic decision patterns across traces
- **Context Length Management**: Balancing detailed character specs with prompt constraints
- **Reward Function Differentiation**: Optimizing distinct rewards for each character archetype
- **Scalable Data Generation**: Building efficient pipelines for decision trace extraction

### End Goal
Models that provide strategic business advice through distinct character lenses while maintaining authentic decision-making patterns - not just dialogue style but complete reasoning processes.

## Anti-Detection Note

The scrapers use aggressive anti-detection techniques including:
- Rotating proxies (configured via environment variables)
- Headless browser stealth modes
- Canvas/WebGL fingerprint spoofing
- Captcha solving services integration

These are configured in `config/settings.py` under `STEALTH_CONFIG` and `PROXY_CONFIG`.