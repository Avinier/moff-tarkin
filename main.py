import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import sys

from scrapers.script_scrapers import UniversalScriptScraper, CharacterSceneExtractor
from storage.database import StorageManager
from models.scene import Scene, SceneCollection, DialogueLine
from config.settings import TARGET_CHARACTERS, SCRAPING_CONFIG

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/extraction_{time}.log", rotation="100 MB", level="DEBUG")

class ExtractionPipeline:
    """Main extraction pipeline orchestrator"""

    def __init__(self):
        self.scraper = UniversalScriptScraper()
        self.extractor = CharacterSceneExtractor()
        self.storage = StorageManager()
        self.stats = {
            'urls_processed': 0,
            'scenes_extracted': 0,
            'errors': 0
        }

    async def extract_character_scenes(self, character_key: str, show_name: str = None):
        """Extract all scenes for a specific character"""
        logger.info(f"Starting extraction for {character_key}")

        character_info = TARGET_CHARACTERS.get(character_key)
        if not character_info:
            logger.error(f"Unknown character: {character_key}")
            return

        show_name = show_name or character_info['show']

        # Scrape from all sources
        logger.info(f"Scraping {show_name} from all sources...")
        script_data = await self.scraper.scrape_all_sources(show_name)

        if not script_data:
            logger.warning(f"No data found for {show_name}")
            return

        logger.info(f"Found {len(script_data)} scripts/episodes")

        # Extract character scenes
        all_scenes = []
        for data in script_data:
            if self.storage.is_duplicate(data.get('url', '')):
                logger.debug(f"Skipping duplicate: {data.get('url')}")
                continue

            scenes = self.extractor.extract_character_scenes(data, character_key)
            all_scenes.extend(scenes)
            self.stats['urls_processed'] += 1

        # Convert to Scene objects and save
        for scene_data in all_scenes:
            scene = self._create_scene_object(scene_data, character_key)
            if self.storage.save_scene(scene):
                self.stats['scenes_extracted'] += 1

        logger.info(f"Extracted {len(all_scenes)} scenes for {character_key}")

    def _create_scene_object(self, scene_data: Dict[str, Any], character_key: str) -> Scene:
        """Convert extracted data to Scene object"""
        character_info = TARGET_CHARACTERS[character_key]

        # Parse dialogue
        dialogue = []
        if 'dialogue' in scene_data:
            for d in scene_data['dialogue']:
                if isinstance(d, dict):
                    dialogue.append(DialogueLine(
                        speaker=d.get('character', 'Unknown'),
                        text=' '.join(d.get('lines', [])) if 'lines' in d else d.get('text', '')
                    ))

        # Extract episode info from title
        title = scene_data.get('title', '')
        season, episode = self._parse_episode_info(title)

        return Scene(
            scene_id='',  # Will be auto-generated
            character=character_key,
            show=character_info['show'],
            season=season,
            episode=episode,
            scene_number=None,
            location=scene_data.get('location'),
            participants=self._extract_participants(scene_data),
            dialogue=dialogue,
            actions=scene_data.get('actions', []),
            duration=None,
            source_url=scene_data.get('url', ''),
            extraction_date=datetime.now(),
            raw_text=scene_data.get('extracted_text', '')
        )

    def _parse_episode_info(self, title: str) -> tuple:
        """Extract season and episode from title"""
        import re
        # Try common patterns
        patterns = [
            r'S(\d+)E(\d+)',
            r'Season\s+(\d+)\s+Episode\s+(\d+)',
            r'(\d+)x(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.I)
            if match:
                return int(match.group(1)), int(match.group(2))

        return None, None

    def _extract_participants(self, scene_data: Dict[str, Any]) -> List[str]:
        """Extract all participants from scene"""
        participants = set()

        if 'dialogue' in scene_data:
            for d in scene_data['dialogue']:
                if isinstance(d, dict) and 'character' in d:
                    participants.add(d['character'])

        return list(participants)

    async def extract_all_characters(self):
        """Extract scenes for all target characters"""
        for character_key in TARGET_CHARACTERS.keys():
            try:
                await self.extract_character_scenes(character_key)
            except Exception as e:
                logger.error(f"Error extracting {character_key}: {e}")
                self.stats['errors'] += 1

        self.print_stats()

    def print_stats(self):
        """Print extraction statistics"""
        logger.info("=" * 50)
        logger.info("EXTRACTION COMPLETE")
        logger.info(f"URLs Processed: {self.stats['urls_processed']}")
        logger.info(f"Scenes Extracted: {self.stats['scenes_extracted']}")
        logger.info(f"Errors: {self.stats['errors']}")

        # Get database stats
        db_stats = self.storage.get_stats()
        logger.info(f"Database Stats: {db_stats}")

async def test_extraction():
    """Test extraction with a single character"""
    pipeline = ExtractionPipeline()

    # Test with Tywin Lannister
    await pipeline.extract_character_scenes(
        character_key='tywin_lannister',
        show_name='game of thrones'
    )

async def run_full_extraction():
    """Run full extraction for all characters"""
    pipeline = ExtractionPipeline()
    await pipeline.extract_all_characters()

def main():
    parser = argparse.ArgumentParser(description='Character Scene Extraction Pipeline')
    parser.add_argument(
        '--character',
        choices=list(TARGET_CHARACTERS.keys()),
        help='Extract scenes for specific character'
    )
    parser.add_argument(
        '--show',
        type=str,
        help='Override show name for search'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test extraction'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Extract all characters'
    )

    args = parser.parse_args()

    if args.test:
        asyncio.run(test_extraction())
    elif args.all:
        asyncio.run(run_full_extraction())
    elif args.character:
        pipeline = ExtractionPipeline()
        asyncio.run(pipeline.extract_character_scenes(
            character_key=args.character,
            show_name=args.show
        ))
    else:
        logger.info("Starting extraction pipeline...")
        logger.info("Target characters:")
        for char_key, char_info in TARGET_CHARACTERS.items():
            logger.info(f"  - {char_key}: {char_info['show']}")
        logger.info("\nUse --help to see available options")

if __name__ == "__main__":
    main()
