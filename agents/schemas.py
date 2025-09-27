from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class LlmMessage:
    """Standard message format for LLM conversations"""
    role: str  # 'user', 'assistant', 'system'
    content: str

@dataclass
class DecisionTrace:
    """Structured format for character decision-making traces"""
    scene_id: str
    character: str
    situation: str
    internal_monologue: str
    decision: str
    justification: str
    context_window: List[str]  # Previous scenes for context
    participants: List[str]
    metadata: Dict[str, Any]

@dataclass
class FireworksTool:
    """Tool definition for Fireworks function calling"""
    type: str = "function"
    function: Dict[str, Any] = None

@dataclass
class FireworksToolCallResponse:
    """Response from Fireworks tool call"""
    content: str
    tool_calls: List[Dict[str, Any]]