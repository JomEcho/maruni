from __future__ import annotations
import os, json, logging
from dataclasses import dataclass
from typing import Any, Optional
from core.profile import PROFILE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STYLE_DIRECTIVE = "\n".join(PROFILE.get("llm_style_directives", []))

@dataclass
class LLMClient:
    provider: str
    model: str
    openai_key: str | None = None
    anthropic_key: str | None = None

    def extract_learning_objectives(self, text: str) -> list[dict[str, Any]]:
        """Extract learning objectives from text using LLM."""
        prompt = (
            "Extract learning objectives from the following text. "
            "Return ONLY JSON array with objects containing: concept (string), bloom (string), summary (string). "
            "Use Bloom's taxonomy levels: remember, understand, apply, analyze, evaluate, create. "
            "Be concise and focus on key concepts. "
            f"\n{STYLE_DIRECTIVE}\n\nText:\n{text[:4000]}"
        )
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "concept": {"type": "string"},
                    "bloom": {"type": "string"},
                    "summary": {"type": "string"}
                },
                "required": ["concept", "bloom", "summary"]
            }
        }
        return self._complete_json(prompt, schema)

    def generate_items(self, lo: dict, n: int = 5, mode: str = "mc") -> list[dict[str, Any]]:
        """Generate assessment items for a learning objective."""
        pref_mc = PROFILE.get("prefer_multiple_choice_for_calibration", True)
        if mode == "mc" and not pref_mc:
            mode = "open"
        
        prompt = (
            f"Create {n} {mode.upper()} questions for this learning objective. "
            "Return ONLY JSON array with objects containing: "
            "prompt (string), options (array of strings, for MC only), "
            "answer_key (string), explanation (string with 'waarom'). "
            "Make questions challenging but fair. "
            f"\n{STYLE_DIRECTIVE}\n\nLearning Objective: {json.dumps(lo, ensure_ascii=False)}"
        )
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer_key": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["prompt", "answer_key", "explanation"]
            }
        }
        return self._complete_json(prompt, schema)

    def grade_open(self, question: str, answer: str, rubric: dict) -> dict[str, Any]:
        """Grade an open-ended answer using a rubric."""
        depth = PROFILE.get("open_question_depth", "kort")
        prompt = (
            "Grade this answer using the provided rubric. "
            "Return ONLY JSON object with: score (number 0-5), feedback (string). "
            f"Feedback should be {depth} and include 'waarom' and one pitfall if relevant. "
            f"\n{STYLE_DIRECTIVE}\n\nQuestion: {question}\nAnswer: {answer}\nRubric: {json.dumps(rubric)}"
        )
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 5},
                "feedback": {"type": "string"}
            },
            "required": ["score", "feedback"]
        }
        return self._complete_json(prompt, schema)

    def _complete_json(self, prompt: str, schema: dict, max_retries: int = 3) -> Any:
        """Complete JSON generation with retries and error handling."""
        provider = (self.provider or "").lower()
        
        for attempt in range(max_retries):
            try:
                if provider == "openai":
                    return self._call_openai(prompt, schema)
                elif provider == "anthropic":
                    return self._call_anthropic(prompt, schema)
                else:
                    logger.warning(f"Unknown provider: {provider}, using stub")
                    return self._stub_response(schema)
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"error": f"{provider}_error: {str(e)}"}
                continue
        
        return {"error": "max_retries_exceeded"}

    def _call_openai(self, prompt: str, schema: dict) -> Any:
        """Call OpenAI API with structured output."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_key or os.environ.get("OPENAI_API_KEY"))
            
            system_prompt = (
                "You are a helpful assistant that returns ONLY valid JSON. "
                f"Follow this schema exactly: {json.dumps(schema)}"
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI tokens used: {response.usage.total_tokens if response.usage else 'unknown'}")
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _call_anthropic(self, prompt: str, schema: dict) -> Any:
        """Call Anthropic API with structured output."""
        try:
            import anthropic
            client = anthropic.Client(api_key=self.anthropic_key or os.environ.get("ANTHROPIC_API_KEY"))
            
            system_prompt = (
                "You are a helpful assistant that returns ONLY valid JSON. "
                f"Follow this schema exactly: {json.dumps(schema)}"
            )
            
            message = client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = "".join([c.text for c in message.content if hasattr(c, "text")])
            logger.info(f"Anthropic tokens used: {message.usage.input_tokens + message.usage.output_tokens if message.usage else 'unknown'}")
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def _stub_response(self, schema: dict) -> Any:
        """Return stub response for local development."""
        if schema.get("type") == "array":
            return [{"note": "local stub, no API call", "concept": "example", "bloom": "understand", "summary": "This is a stub response"}]
        elif schema.get("type") == "object":
            return {"score": 3, "feedback": "Stub response - no actual grading performed"}
        else:
            return {"error": "unknown_schema_type"}

def get_llm() -> LLMClient:
    """Get configured LLM client."""
    from core.settings import settings
    return LLMClient(
        provider=settings.LLM_PROVIDER,
        model=settings.MODEL_NAME,
        openai_key=settings.OPENAI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
    )
