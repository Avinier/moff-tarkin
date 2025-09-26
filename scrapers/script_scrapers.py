import asyncio
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from loguru import logger
import sys
sys.path.append('..')

from scrapers.base_scraper import BaseScraper
from config.settings import TARGET_CHARACTERS

class SpringfieldScraper(BaseScraper):
    """Scraper for Springfield Springfield scripts"""

    def __init__(self):
        super().__init__(name="springfield", use_browser=False)
        self.base_url = "https://springfieldspringfield.co.uk"

    async def get_show_episodes(self, show_name: str) -> List[str]:
        """Get all episode URLs for a show"""
        show_slug = show_name.lower().replace(" ", "-")
        url = f"{self.base_url}/episode_scripts.php?tv-show={show_slug}"

        html = await self.fetch(url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        episodes = []

        for link in soup.select('a[href*="view_episode_scripts"]'):
            episode_url = self.base_url + link.get('href')
            episodes.append(episode_url)

        logger.info(f"Found {len(episodes)} episodes for {show_name}")
        return episodes

    async def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape episode script"""
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # Extract episode info
        title = soup.select_one('h1')
        title_text = title.text if title else "Unknown"

        # Extract script content
        script_div = soup.select_one('.scrolling-script-container')
        if not script_div:
            return None

        script_text = script_div.get_text(strip=True)

        # Save raw content
        self.save_raw(url, html)

        return {
            'url': url,
            'title': title_text,
            'script': script_text,
            'source': 'springfield'
        }

class EightFlixScraper(BaseScraper):
    """Scraper for 8FLiX scripts"""

    def __init__(self):
        super().__init__(name="8flix", use_browser=True)  # May need browser for JS
        self.base_url = "https://8flix.com"

    async def search_show(self, show_name: str) -> Optional[str]:
        """Search for show and get URL"""
        search_url = f"{self.base_url}/search?q={show_name.replace(' ', '+')}"
        html = await self.fetch(search_url)

        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')
        # Find first matching show
        show_link = soup.select_one('a[href*="/tvshow/"]')
        if show_link:
            return self.base_url + show_link.get('href')

        return None

    async def get_season_episodes(self, show_url: str) -> List[str]:
        """Get all episodes from show page"""
        html = await self.fetch(show_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        episodes = []

        # Find all transcript links
        for link in soup.select('a[href*="transcript"]'):
            episode_url = link.get('href')
            if not episode_url.startswith('http'):
                episode_url = self.base_url + episode_url
            episodes.append(episode_url)

        return episodes

    async def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape episode transcript"""
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title = soup.select_one('h1, .episode-title')
        title_text = title.text if title else "Unknown"

        # Extract transcript
        transcript_div = soup.select_one('.transcript-content, .content, article')
        if not transcript_div:
            return None

        # Parse dialogue and actions
        scenes = self._parse_transcript(transcript_div)

        self.save_raw(url, html)

        return {
            'url': url,
            'title': title_text,
            'scenes': scenes,
            'source': '8flix'
        }

    def _parse_transcript(self, content_div) -> List[Dict[str, Any]]:
        """Parse transcript into scenes"""
        scenes = []
        current_scene = None

        for element in content_div.children:
            if not hasattr(element, 'name'):
                continue

            text = element.get_text(strip=True)

            # Scene heading detection
            if re.match(r'^(INT\.|EXT\.|SCENE)', text, re.I):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {
                    'location': text,
                    'dialogue': [],
                    'actions': []
                }

            # Character dialogue
            elif element.name in ['b', 'strong'] or text.isupper():
                if current_scene:
                    character = text.rstrip(':')
                    current_scene['dialogue'].append({'character': character, 'lines': []})

            # Dialogue lines
            elif current_scene and current_scene['dialogue']:
                current_scene['dialogue'][-1]['lines'].append(text)

            # Action lines
            elif current_scene:
                current_scene['actions'].append(text)

        if current_scene:
            scenes.append(current_scene)

        return scenes

class SubslikescriptScraper(BaseScraper):
    """Scraper for Subslikescript"""

    def __init__(self):
        super().__init__(name="subslikescript", use_browser=False)
        self.base_url = "https://subslikescript.com"

    async def search_show(self, show_name: str) -> List[str]:
        """Search for show episodes"""
        search_url = f"{self.base_url}/search?q={show_name.replace(' ', '_')}"
        html = await self.fetch(search_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        episodes = []

        for link in soup.select('a[href*="/series/"]'):
            episode_url = link.get('href')
            if not episode_url.startswith('http'):
                episode_url = self.base_url + episode_url
            episodes.append(episode_url)

        return episodes

    async def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape episode/movie transcript"""
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title = soup.select_one('h1')
        title_text = title.text if title else "Unknown"

        # Extract transcript
        transcript_div = soup.select_one('.full-script')
        if not transcript_div:
            return None

        # Parse lines
        dialogue_lines = []
        for line in transcript_div.stripped_strings:
            dialogue_lines.append(line)

        # Identify character lines (usually in caps or followed by colon)
        parsed_dialogue = self._parse_dialogue(dialogue_lines)

        self.save_raw(url, html)

        return {
            'url': url,
            'title': title_text,
            'dialogue': parsed_dialogue,
            'source': 'subslikescript'
        }

    def _parse_dialogue(self, lines: List[str]) -> List[Dict[str, str]]:
        """Parse dialogue lines into character-text pairs"""
        dialogue = []
        current_speaker = None

        for line in lines:
            # Check if line is character name (all caps, or ends with colon)
            if re.match(r'^[A-Z][A-Z\s]+:?$', line.strip()):
                current_speaker = line.strip().rstrip(':')
            elif current_speaker:
                dialogue.append({
                    'character': current_speaker,
                    'text': line.strip()
                })

        return dialogue

class UniversalScriptScraper(BaseScraper):
    """Universal scraper that tries multiple methods"""

    def __init__(self):
        super().__init__(name="universal", use_browser=True)
        self.scrapers = [
            SpringfieldScraper(),
            EightFlixScraper(),
            SubslikescriptScraper()
        ]

    async def scrape_all_sources(self, show_name: str) -> List[Dict[str, Any]]:
        """Try to scrape from all available sources"""
        all_results = []

        for scraper in self.scrapers:
            try:
                logger.info(f"Trying {scraper.name} for {show_name}")

                if hasattr(scraper, 'get_show_episodes'):
                    episodes = await scraper.get_show_episodes(show_name)
                    results = await scraper.batch_scrape(episodes[:5])  # Limit for testing
                    all_results.extend(results)

                elif hasattr(scraper, 'search_show'):
                    episodes = await scraper.search_show(show_name)
                    if isinstance(episodes, str):
                        episodes = [episodes]
                    results = await scraper.batch_scrape(episodes[:5])
                    all_results.extend(results)

            except Exception as e:
                logger.error(f"Error with {scraper.name}: {e}")
                continue

        return all_results

    async def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Try to scrape URL with appropriate scraper"""
        for scraper in self.scrapers:
            if scraper.name in url or any(domain in url for domain in ['springfield', '8flix', 'subslike']):
                return await scraper.scrape(url)

        # Try all scrapers
        for scraper in self.scrapers:
            result = await scraper.scrape(url)
            if result:
                return result

        return None

class CharacterSceneExtractor:
    """Extract scenes for specific characters"""

    def __init__(self):
        self.characters = TARGET_CHARACTERS

    def extract_character_scenes(self, script_data: Dict[str, Any], character_key: str) -> List[Dict[str, Any]]:
        """Extract all scenes containing target character"""
        character_info = self.characters.get(character_key)
        if not character_info:
            return []

        character_names = character_info['names']
        context_clues = character_info.get('context_clues', [])
        scenes = []

        # Handle different data formats
        if 'scenes' in script_data:
            # Structured scenes
            for scene in script_data['scenes']:
                if self._scene_contains_character(scene, character_names, context_clues):
                    scenes.append({
                        'character': character_key,
                        'location': scene.get('location'),
                        'dialogue': scene.get('dialogue'),
                        'actions': scene.get('actions'),
                        'source': script_data.get('source'),
                        'url': script_data.get('url'),
                        'title': script_data.get('title')
                    })

        elif 'dialogue' in script_data:
            # Dialogue list
            relevant_dialogue = []
            for entry in script_data['dialogue']:
                if any(name.lower() in entry.get('character', '').lower() for name in character_names):
                    relevant_dialogue.append(entry)

            if relevant_dialogue:
                scenes.append({
                    'character': character_key,
                    'dialogue': relevant_dialogue,
                    'source': script_data.get('source'),
                    'url': script_data.get('url'),
                    'title': script_data.get('title')
                })

        elif 'script' in script_data:
            # Raw script text
            script_text = script_data['script']
            if any(name.lower() in script_text.lower() for name in character_names):
                # Extract relevant portions
                extracted = self._extract_from_raw_script(script_text, character_names)
                if extracted:
                    scenes.append({
                        'character': character_key,
                        'extracted_text': extracted,
                        'source': script_data.get('source'),
                        'url': script_data.get('url'),
                        'title': script_data.get('title')
                    })

        return scenes

    def _scene_contains_character(self, scene: Dict, names: List[str], context: List[str]) -> bool:
        """Check if scene contains character"""
        # Check dialogue
        for dialogue in scene.get('dialogue', []):
            if any(name.lower() in dialogue.get('character', '').lower() for name in names):
                return True

        # Check actions
        for action in scene.get('actions', []):
            if any(name.lower() in action.lower() for name in names):
                return True

        # Check location (might contain character name)
        location = scene.get('location', '')
        if any(name.lower() in location.lower() for name in names):
            return True

        return False

    def _extract_from_raw_script(self, text: str, names: List[str]) -> List[str]:
        """Extract relevant portions from raw script"""
        lines = text.split('\n')
        extracted = []
        context_window = 10  # Lines before/after character mention

        for i, line in enumerate(lines):
            if any(name.lower() in line.lower() for name in names):
                # Get surrounding context
                start = max(0, i - context_window)
                end = min(len(lines), i + context_window + 1)
                context = lines[start:end]
                extracted.extend(context)

        return extracted