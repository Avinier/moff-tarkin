import sqlite3
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger
import sys
sys.path.append('..')

from models.scene import Scene, SceneCollection

class SQLiteStorage:
    """SQLite storage for all data - simple, no setup required"""

    def __init__(self, db_path: str = "data/moff_tarkin.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup_tables()
        self._setup_cache_table()

    def _setup_tables(self):
        """Create tables for scenes"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                scene_id TEXT PRIMARY KEY,
                character TEXT NOT NULL,
                show TEXT NOT NULL,
                season INTEGER,
                episode INTEGER,
                scene_number INTEGER,
                location TEXT,
                participants TEXT,  -- JSON array
                dialogue TEXT,      -- JSON array
                actions TEXT,       -- JSON array
                duration INTEGER,
                source_url TEXT,
                extraction_date TEXT,
                raw_text TEXT,
                confidence_score REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for fast queries
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_character ON scenes(character)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_show ON scenes(show)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_source_url ON scenes(source_url)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_extraction_date ON scenes(extraction_date)")

        self.conn.commit()

    def _setup_cache_table(self):
        """Create cache table for deduplication and response caching"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                url TEXT PRIMARY KEY,
                content TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_urls (
                url TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def save_scene(self, scene: Scene) -> bool:
        """Save single scene"""
        try:
            scene_dict = scene.to_dict()

            self.conn.execute("""
                INSERT OR REPLACE INTO scenes (
                    scene_id, character, show, season, episode, scene_number,
                    location, participants, dialogue, actions, duration,
                    source_url, extraction_date, raw_text, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scene_dict['scene_id'],
                scene_dict['character'],
                scene_dict['show'],
                scene_dict.get('season'),
                scene_dict.get('episode'),
                scene_dict.get('scene_number'),
                scene_dict.get('location'),
                json.dumps(scene_dict.get('participants', [])),
                json.dumps(scene_dict.get('dialogue', [])),
                json.dumps(scene_dict.get('actions', [])),
                scene_dict.get('duration'),
                scene_dict['source_url'],
                scene_dict['extraction_date'],
                scene_dict.get('raw_text'),
                scene_dict.get('confidence_score', 1.0)
            ))

            self.conn.commit()
            logger.debug(f"Saved scene {scene.scene_id} to SQLite")
            return True

        except Exception as e:
            logger.error(f"Error saving scene: {e}")
            return False

    def save_batch(self, scenes: List[Scene]) -> int:
        """Save multiple scenes efficiently"""
        if not scenes:
            return 0

        saved_count = 0
        for scene in scenes:
            if self.save_scene(scene):
                saved_count += 1

        logger.info(f"Saved {saved_count}/{len(scenes)} scenes")
        return saved_count

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get scene by ID"""
        cursor = self.conn.execute(
            "SELECT * FROM scenes WHERE scene_id = ?", (scene_id,)
        )
        row = cursor.fetchone()

        if row:
            return self._row_to_scene(row)
        return None

    def get_character_scenes(self, character: str, limit: int = None) -> List[Scene]:
        """Get all scenes for a character"""
        query = "SELECT * FROM scenes WHERE character = ?"
        params = [character]

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)
        return [self._row_to_scene(row) for row in cursor]

    def get_show_scenes(self, show: str, character: str = None) -> List[Scene]:
        """Get scenes from a specific show"""
        if character:
            query = "SELECT * FROM scenes WHERE show = ? AND character = ?"
            params = [show, character]
        else:
            query = "SELECT * FROM scenes WHERE show = ?"
            params = [show]

        cursor = self.conn.execute(query, params)
        return [self._row_to_scene(row) for row in cursor]

    def search_dialogue(self, text: str, character: str = None) -> List[Scene]:
        """Search for text in dialogue"""
        query = "SELECT * FROM scenes WHERE dialogue LIKE ?"
        params = [f'%{text}%']

        if character:
            query += " AND character = ?"
            params.append(character)

        cursor = self.conn.execute(query, params)
        return [self._row_to_scene(row) for row in cursor]

    def _row_to_scene(self, row: sqlite3.Row) -> Scene:
        """Convert database row to Scene object"""
        from models.scene import DialogueLine

        # Parse JSON fields
        dialogue_data = json.loads(row['dialogue']) if row['dialogue'] else []
        dialogue = [DialogueLine(**d) if isinstance(d, dict) else DialogueLine(speaker="Unknown", text=str(d))
                   for d in dialogue_data]

        return Scene(
            scene_id=row['scene_id'],
            character=row['character'],
            show=row['show'],
            season=row['season'],
            episode=row['episode'],
            scene_number=row['scene_number'],
            location=row['location'],
            participants=json.loads(row['participants']) if row['participants'] else [],
            dialogue=dialogue,
            actions=json.loads(row['actions']) if row['actions'] else [],
            duration=row['duration'],
            source_url=row['source_url'],
            extraction_date=datetime.fromisoformat(row['extraction_date']),
            raw_text=row['raw_text'],
            confidence_score=row['confidence_score']
        )

    # Cache methods (replacing Redis)
    def is_processed(self, url: str) -> bool:
        """Check if URL was already processed"""
        cursor = self.conn.execute(
            "SELECT 1 FROM processed_urls WHERE url = ?", (url,)
        )
        return cursor.fetchone() is not None

    def mark_processed(self, url: str):
        """Mark URL as processed"""
        self.conn.execute(
            "INSERT OR IGNORE INTO processed_urls (url) VALUES (?)", (url,)
        )
        self.conn.commit()

    def cache_response(self, url: str, content: str, expiry_hours: int = 24):
        """Cache HTTP response"""
        expiry = f"datetime('now', '+{expiry_hours} hours')"
        self.conn.execute(
            f"INSERT OR REPLACE INTO cache (url, content, expiry) VALUES (?, ?, {expiry})",
            (url, content)
        )
        self.conn.commit()

    def get_cached_response(self, url: str) -> Optional[str]:
        """Get cached response if not expired"""
        cursor = self.conn.execute(
            """SELECT content FROM cache
               WHERE url = ? AND expiry > datetime('now')""",
            (url,)
        )
        row = cursor.fetchone()
        return row['content'] if row else None

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # Total scenes
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM scenes")
        stats['total_scenes'] = cursor.fetchone()['count']

        # Scenes by character
        cursor = self.conn.execute("""
            SELECT character, COUNT(*) as count, COUNT(DISTINCT show) as shows
            FROM scenes GROUP BY character
        """)
        stats['characters'] = {}
        for row in cursor:
            stats['characters'][row['character']] = {
                'scene_count': row['count'],
                'show_count': row['shows']
            }

        # Cached URLs
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM cache WHERE expiry > datetime('now')")
        stats['cached_urls'] = cursor.fetchone()['count']

        # Processed URLs
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM processed_urls")
        stats['processed_urls'] = cursor.fetchone()['count']

        return stats

    def export_to_json(self, filepath: str, character: str = None):
        """Export scenes to JSON file"""
        if character:
            scenes = self.get_character_scenes(character)
        else:
            cursor = self.conn.execute("SELECT * FROM scenes")
            scenes = [self._row_to_scene(row) for row in cursor]

        data = [scene.to_dict() for scene in scenes]

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(data)} scenes to {filepath}")

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        self.conn.execute("DELETE FROM cache WHERE expiry <= datetime('now')")
        self.conn.commit()

class FileStorage:
    """Simple file storage for raw HTML backup"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def save_raw(self, url: str, content: str, source: str):
        """Save raw HTML content"""
        # Create filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filepath = self.raw_dir / source / f"{url_hash}.html"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save HTML
        filepath.write_text(content, encoding='utf-8')

        # Save metadata
        meta_path = filepath.with_suffix('.json')
        metadata = {
            'url': url,
            'source': source,
            'saved_at': datetime.now().isoformat(),
            'size': len(content)
        }
        meta_path.write_text(json.dumps(metadata, indent=2))

        logger.debug(f"Saved raw content to {filepath}")

    def get_raw_files(self, source: str = None) -> List[Path]:
        """Get list of raw HTML files"""
        if source:
            pattern = f"{source}/*.html"
        else:
            pattern = "**/*.html"

        return list(self.raw_dir.glob(pattern))

class StorageManager:
    """Unified storage management with SQLite"""

    def __init__(self, db_path: str = "data/moff_tarkin.db"):
        self.db = SQLiteStorage(db_path)
        self.files = FileStorage()

    def save_scene(self, scene: Scene, save_raw: bool = False) -> bool:
        """Save scene to database"""
        success = self.db.save_scene(scene)

        if success:
            # Mark URL as processed
            self.db.mark_processed(scene.source_url)

        return success

    def is_duplicate(self, url: str) -> bool:
        """Check if URL was already processed"""
        return self.db.is_processed(url)

    def cache_response(self, url: str, content: str):
        """Cache HTTP response"""
        self.db.cache_response(url, content)

    def get_cached_response(self, url: str) -> Optional[str]:
        """Get cached response"""
        return self.db.get_cached_response(url)

    def save_raw_html(self, url: str, content: str, source: str):
        """Save raw HTML to file system"""
        self.files.save_raw(url, content, source)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        stats = self.db.get_stats()
        stats['raw_files'] = len(self.files.get_raw_files())
        return stats