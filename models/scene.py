from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json

@dataclass
class DialogueLine:
    """Single dialogue line"""
    speaker: str
    text: str
    timestamp: Optional[str] = None
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'speaker': self.speaker,
            'text': self.text,
            'timestamp': self.timestamp,
            'context': self.context
        }

@dataclass
class Scene:
    """Scene data model"""
    scene_id: str
    character: str
    show: str
    season: Optional[int]
    episode: Optional[int]
    scene_number: Optional[int]
    location: Optional[str]
    participants: List[str]
    dialogue: List[DialogueLine]
    actions: List[str]
    duration: Optional[int]  # in seconds
    source_url: str
    extraction_date: datetime
    raw_text: Optional[str] = None
    confidence_score: float = 1.0

    def __post_init__(self):
        if not self.scene_id:
            self.scene_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique scene ID"""
        unique_str = f"{self.show}_{self.season}_{self.episode}_{self.scene_number}_{self.character}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'scene_id': self.scene_id,
            'character': self.character,
            'show': self.show,
            'season': self.season,
            'episode': self.episode,
            'scene_number': self.scene_number,
            'location': self.location,
            'participants': self.participants,
            'dialogue': [d.to_dict() for d in self.dialogue],
            'actions': self.actions,
            'duration': self.duration,
            'source_url': self.source_url,
            'extraction_date': self.extraction_date.isoformat(),
            'raw_text': self.raw_text,
            'confidence_score': self.confidence_score
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """Create Scene from dictionary"""
        dialogue = [DialogueLine(**d) for d in data.get('dialogue', [])]
        data['dialogue'] = dialogue
        data['extraction_date'] = datetime.fromisoformat(data['extraction_date'])
        return cls(**data)

    def get_character_dialogue(self) -> List[str]:
        """Get all dialogue for the main character"""
        return [
            d.text for d in self.dialogue
            if self.character.lower() in d.speaker.lower()
        ]

    def get_dialogue_count(self) -> int:
        """Get total dialogue lines"""
        return len(self.dialogue)

    def get_word_count(self) -> int:
        """Get total word count in scene"""
        total_words = 0
        for d in self.dialogue:
            total_words += len(d.text.split())
        for a in self.actions:
            total_words += len(a.split())
        return total_words

@dataclass
class SceneCollection:
    """Collection of scenes for a character"""
    character: str
    scenes: List[Scene] = field(default_factory=list)

    def add_scene(self, scene: Scene):
        """Add scene to collection"""
        self.scenes.append(scene)

    def get_by_show(self, show: str) -> List[Scene]:
        """Get all scenes from a specific show"""
        return [s for s in self.scenes if s.show == show]

    def get_by_episode(self, show: str, season: int, episode: int) -> List[Scene]:
        """Get scenes from specific episode"""
        return [
            s for s in self.scenes
            if s.show == show and s.season == season and s.episode == episode
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        total_dialogue = sum(s.get_dialogue_count() for s in self.scenes)
        total_words = sum(s.get_word_count() for s in self.scenes)
        total_duration = sum(s.duration for s in self.scenes if s.duration)

        shows = {}
        for scene in self.scenes:
            if scene.show not in shows:
                shows[scene.show] = 0
            shows[scene.show] += 1

        return {
            'total_scenes': len(self.scenes),
            'total_dialogue_lines': total_dialogue,
            'total_words': total_words,
            'total_duration_seconds': total_duration,
            'shows': shows,
            'average_scene_length': total_words / len(self.scenes) if self.scenes else 0
        }

    def to_json(self, filepath: str):
        """Save collection to JSON file"""
        data = {
            'character': self.character,
            'scenes': [s.to_dict() for s in self.scenes],
            'stats': self.get_stats()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> 'SceneCollection':
        """Load collection from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        collection = cls(character=data['character'])
        for scene_data in data['scenes']:
            collection.add_scene(Scene.from_dict(scene_data))

        return collection