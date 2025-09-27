import os
import json
import requests
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dotenv import load_dotenv

from agents.schemas import FireworksTool, FireworksToolCallResponse, LlmMessage

load_dotenv()

class LLM:
    """
    Raw LLM API calls for Fireworks AI.
    Supports DeepSeek, Qwen, and other models.
    """

    def __init__(self):
        # Fireworks AI configuration
        self.fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
        if not self.fireworks_api_key:
            raise ValueError("FIREWORKS_API_KEY not found in environment variables")

        self.fireworks_endpoint = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.fireworks_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.fireworks_api_key}"
        }

        # Fireworks model mapping
        self.fireworks_models = {
            "deepseek-v3": "accounts/fireworks/models/deepseek-v3",
            "deepseek-v3p1": "accounts/fireworks/models/deepseek-v3p1",
            "deepseek-r1": "accounts/fireworks/models/deepseek-r1-0528",
            "qwen3-30b-a3b": "accounts/fireworks/models/qwen3-30b-a3b",
            "qwen2.5-72b-instruct": "accounts/fireworks/models/qwen2p5-72b-instruct"
        }

    def fw_basic_call(self, prompt_or_messages, model: str = "deepseek-v3p1", system_prompt: Optional[str] = None,
                      stream: bool = False, on_token: Optional[Callable[[str], None]] = None,
                      timeout_seconds: int = 120, reasoning_effort: Optional[str] = "medium",
                      on_reasoning: Optional[Callable[[str], None]] = None, **kwargs) -> str:
        """Basic Fireworks AI API call for text generation. Accepts either a string prompt or a list of messages."""
        if not self.fireworks_api_key:
            raise ValueError("Fireworks API key not found. Check FIREWORKS_API_KEY environment variable.")

        # Get the full model name from mapping
        full_model_name = self.fireworks_models.get(model, model)

        # Handle different input types
        messages = []
        if isinstance(prompt_or_messages, str):
            # Single prompt - create user message
            messages = [{"role": "user", "content": prompt_or_messages}]
        elif isinstance(prompt_or_messages, list):
            # List of messages - convert to Fireworks format
            for msg in prompt_or_messages:
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    # LlmMessage object - role is already a string
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                elif isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    # Already in dict format
                    messages.append(msg)
                else:
                    raise ValueError("Invalid message format. Expected LlmMessage objects or dicts with 'role' and 'content' keys.")
        else:
            raise ValueError("Input must be either a string prompt or a list of messages.")

        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Build payload for chat completions API
        payload = {
            "model": full_model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 20480),
            "temperature": kwargs.get("temperature", 0.6),
            "top_p": kwargs.get("top_p", 1),
            "top_k": kwargs.get("top_k", 40),
            "presence_penalty": kwargs.get("presence_penalty", 0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0),
            "stream": stream
        }

        # Include reasoning_effort ONLY for reasoning-capable models
        supports_reasoning = model in {"deepseek-r1", "deepseek-v3p1"}
        if supports_reasoning and reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if not stream:
            # Non-streaming request
            try:
                response = requests.post(
                    self.fireworks_endpoint,
                    headers=self.fireworks_headers,
                    data=json.dumps(payload),
                    timeout=timeout_seconds
                )
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        message_obj = result["choices"][0].get("message", {})
                        content = message_obj.get("content", "")
                        reasoning_content = message_obj.get("reasoning_content", "")

                        # Fallback: parse <think> ... </think> if present in content
                        if not reasoning_content and isinstance(content, str) and "<think>" in content and "</think>" in content:
                            try:
                                start_idx = content.find("<think>") + len("<think>")
                                end_idx = content.find("</think>")
                                extracted_reasoning = content[start_idx:end_idx]
                                # Remove the <think>...</think> block from visible content
                                visible_content = content[end_idx + len("</think>"):].lstrip("\n")
                                reasoning_content = extracted_reasoning
                                content = visible_content
                            except Exception:
                                pass

                        # Return raw content without formatting
                        return content
                    else:
                        print("FW Response structure:", result.keys() if result else "Empty result")
                        raise Exception("No response content received from Fireworks API")
                else:
                    raise Exception(f"Fireworks API request failed with status {response.status_code}: {response.text}")
            except requests.RequestException as e:
                raise Exception(f"[fw_basic_call] Fireworks API request failed: {str(e)}")
            except json.JSONDecodeError as e:
                raise Exception(f"[fw_basic_call] Failed to parse Fireworks API response: {str(e)}")

        # Streaming request using chat completions API
        headers = dict(self.fireworks_headers)
        headers["Accept"] = "text/event-stream"

        final_text_chunks: List[str] = []
        final_reasoning_chunks: List[str] = []
        try:
            with requests.post(
                self.fireworks_endpoint,
                headers=headers,
                data=json.dumps(payload),
                stream=True,
                timeout=timeout_seconds
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        try:
                            json_data = json.loads(line[6:])  # Remove "data: " prefix
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})

                                # Handle reasoning_content (comes first in the stream)
                                if "reasoning_content" in delta and delta["reasoning_content"]:
                                    reason_chunk = delta["reasoning_content"]
                                    final_reasoning_chunks.append(reason_chunk)
                                    if on_reasoning:
                                        try:
                                            on_reasoning(reason_chunk)
                                        except Exception:
                                            pass

                                # Handle content (comes after reasoning is complete)
                                if "content" in delta and delta["content"]:
                                    text_chunk = delta["content"]
                                    final_text_chunks.append(text_chunk)
                                    if on_token:
                                        try:
                                            on_token(text_chunk)
                                        except Exception:
                                            pass
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            raise Exception(f"[fw_basic_call(stream)] Fireworks streaming failed: {str(e)}")

        combined_visible = "".join(final_text_chunks)
        if not final_reasoning_chunks and ("<think>" in combined_visible and "</think>" in combined_visible):
            try:
                start_idx = combined_visible.find("<think>") + len("<think>")
                end_idx = combined_visible.find("</think>")
                extracted_reasoning = combined_visible[start_idx:end_idx]
                combined_visible = combined_visible[end_idx + len("</think>"):].lstrip("\n")
                final_reasoning_chunks.append(extracted_reasoning)
            except Exception:
                pass

        # Return raw content without formatting
        return combined_visible

    def fw_tool_call(self, prompt: str = None, messages: List[LlmMessage] = None, tools: List[FireworksTool] = None,
                     model_key: str = "deepseek-v3p1", max_tokens: int = 4096,
                     temperature: float = 0.3, system_prompt: Optional[str] = None,
                     stream: bool = False, on_token: Optional[Callable[[str], None]] = None,
                     on_reasoning: Optional[Callable[[str], None]] = None,
                     reasoning_effort: Optional[str] = None,
                     timeout_seconds: int = 120) -> FireworksToolCallResponse:
        """
        Call Fireworks AI with tool/function calling support.

        Args:
            prompt: Optional single user prompt (legacy, use messages instead)
            messages: Optional full conversation history as list of LlmMessage objects
            tools: List of tool definitions in Fireworks format
            model_key: Model key from available Fireworks models
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            stream: Enable streaming response
            on_token: Callback for each content token during streaming
            on_reasoning: Callback for each reasoning token during streaming
            reasoning_effort: Reasoning effort level for supported models

        Returns:
            Dict with 'content' and 'tool_calls' keys.
        """

        if not self.fireworks_api_key:
            raise ValueError("Fireworks API key not found. Check FIREWORKS_API_KEY environment variable.")

        if model_key not in self.fireworks_models:
            raise ValueError(f"Unknown model key: {model_key}. Available: {list(self.fireworks_models.keys())}")

        model = self.fireworks_models[model_key]

        # Validate tools format
        if not isinstance(tools, list):
            raise ValueError("Tools must be a list of tool definitions")

        for tool in tools:
            if not isinstance(tool, dict) or tool.get("type") != "function":
                raise ValueError("Each tool must be a dict with 'type': 'function'")
            if "function" not in tool or "name" not in tool["function"]:
                raise ValueError("Each tool must have a 'function' with a 'name'")

        # Build messages array
        api_messages: List[Dict[str, Any]] = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        if messages:
            # Use provided conversation history
            for msg in messages:
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    api_messages.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg, dict):
                    api_messages.append(msg)
                else:
                    raise ValueError("Invalid message format in fw_tool_call")
        elif prompt:
            # Fallback to single prompt
            api_messages.append({"role": "user", "content": prompt})
        else:
            raise ValueError("Either 'messages' or 'prompt' must be provided")

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": api_messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": stream
        }

        # Add reasoning_effort for supported models
        supports_reasoning = model_key in {"deepseek-r1", "deepseek-v3p1"}
        if supports_reasoning and reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if not stream:
            # Non-streaming request
            try:
                response = requests.post(
                    self.fireworks_endpoint,
                    headers=self.fireworks_headers,
                    json=payload,
                    timeout=timeout_seconds
                )
                response.raise_for_status()
                response_json = response.json()
                message = response_json["choices"][0]["message"]

                content = message.get("content", "")

                return {
                    "content": content,
                    "tool_calls": message.get("tool_calls", [])
                }
            except requests.exceptions.RequestException as e:
                raise Exception(f"[fw_tool_call] Fireworks function calling failed: {str(e)}")
            except json.JSONDecodeError as e:
                raise Exception(f"[fw_tool_call] Failed to parse Fireworks API response: {str(e)}")
            except (KeyError, IndexError) as e:
                raise Exception(f"[fw_tool_call] Failed to extract data from Fireworks response: {str(e)}")

        # Streaming request
        headers = dict(self.fireworks_headers)
        headers["Accept"] = "text/event-stream"

        content_chunks: List[str] = []
        reasoning_chunks: List[str] = []
        tool_calls_accumulated = []

        try:
            with requests.post(
                self.fireworks_endpoint,
                headers=headers,
                json=payload,
                stream=True,
                timeout=timeout_seconds
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        try:
                            json_data = json.loads(line[6:])  # Remove "data: " prefix
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})

                                # Handle reasoning_content
                                if "reasoning_content" in delta and delta["reasoning_content"]:
                                    reason_chunk = delta["reasoning_content"]
                                    reasoning_chunks.append(reason_chunk)
                                    if on_reasoning:
                                        try:
                                            on_reasoning(reason_chunk)
                                        except Exception:
                                            pass

                                # Handle content streaming
                                if "content" in delta and delta["content"]:
                                    text_chunk = delta["content"]
                                    content_chunks.append(text_chunk)
                                    if on_token:
                                        try:
                                            on_token(text_chunk)
                                        except Exception:
                                            pass

                                # Handle tool calls
                                if "tool_calls" in delta:
                                    for tc in delta["tool_calls"]:
                                        if "index" in tc:
                                            idx = tc["index"]
                                            while len(tool_calls_accumulated) <= idx:
                                                tool_calls_accumulated.append({})

                                            if "id" in tc:
                                                tool_calls_accumulated[idx]["id"] = tc["id"]
                                            if "type" in tc:
                                                tool_calls_accumulated[idx]["type"] = tc["type"]
                                            if "function" in tc:
                                                if "function" not in tool_calls_accumulated[idx]:
                                                    tool_calls_accumulated[idx]["function"] = {}
                                                if "name" in tc["function"]:
                                                    tool_calls_accumulated[idx]["function"]["name"] = tc["function"]["name"]
                                                if "arguments" in tc["function"]:
                                                    if "arguments" not in tool_calls_accumulated[idx]["function"]:
                                                        tool_calls_accumulated[idx]["function"]["arguments"] = ""
                                                    tool_calls_accumulated[idx]["function"]["arguments"] += tc["function"]["arguments"]
                        except json.JSONDecodeError:
                            continue

            return {
                "content": "".join(content_chunks),
                "tool_calls": tool_calls_accumulated
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"[fw_tool_call(stream)] Fireworks streaming failed: {str(e)}")