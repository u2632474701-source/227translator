from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranslationResult:
    source_language: str
    target_language: str
    translated_text: str
    provider: str = "vertex"


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text


def _read_project_id_from_service_account(path: str | None) -> str | None:
    if not path:
        return None

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

    project_id = payload.get("project_id")
    return project_id if isinstance(project_id, str) and project_id.strip() else None


def _ensure_google_application_credentials() -> None:
    """Let Vertex AI use the same service-account.json as Google Sheets."""

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if service_account_file:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file


class VertexAITranslator:
    provider = "vertex"

    def __init__(
        self,
        *,
        project: str,
        location: str,
        model: str,
    ) -> None:
        self.project = project
        self.location = location
        self.model = model
        self._client = None

    @classmethod
    def from_env(cls) -> "VertexAITranslator":
        _ensure_google_application_credentials()

        credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        project = (
            os.getenv("GOOGLE_CLOUD_PROJECT")
            or _read_project_id_from_service_account(credentials_file)
            or ""
        ).strip()

        location = (
            os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("VERTEX_LOCATION")
            or "global"
        ).strip()

        model = (os.getenv("VERTEX_MODEL") or "gemini-2.5-flash").strip()

        if not project:
            raise RuntimeError(
                "Vertex AI needs GOOGLE_CLOUD_PROJECT or project_id in service-account.json"
            )

        if not location:
            raise RuntimeError("Vertex AI needs GOOGLE_CLOUD_LOCATION or VERTEX_LOCATION")

        if not model:
            raise RuntimeError("Vertex AI needs VERTEX_MODEL")

        return cls(project=project, location=location, model=model)

    def _ensure_client(self):
        if self._client is not None:
            return self._client

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "Vertex AI requires google-genai. Install with: py -m pip install google-genai"
            ) from exc

        self._client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
        )
        return self._client

    async def translate(
        self,
        text: str,
        *,
        target_language: str,
        source_language: str | None = None,
    ) -> TranslationResult:
        client = self._ensure_client()

        payload = {
            "target_language": target_language,
            "source_language_hint": source_language or "auto",
            "text": text,
        }

        prompt = (
            "You are a strict translation engine for Telegram group chat messages.\n"
            "Translate the input text to the target language.\n"
            "Preserve usernames, game/server names, item names, commands, URLs, emojis, numbers, and formatting when possible.\n"
            "Preserve tone, slang, short casual style, and profanity intensity without adding explanations.\n"
            "Do not censor, summarize, comment, or add notes.\n"
            "Return only valid JSON with keys: source_language, target_language, translated_text.\n\n"
            f"Input JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            )
        except Exception:
            # google-genai also accepts dict config in many versions.
            config = {
                "temperature": 0,
                "response_mime_type": "application/json",
            }

        response = await client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise RuntimeError("Vertex AI returned empty translation response")

        try:
            parsed = json.loads(_strip_json_fence(raw_text))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Vertex AI returned invalid JSON: {raw_text[:300]}") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("Vertex AI returned JSON, but not an object")

        translated_text = parsed.get("translated_text")
        if not isinstance(translated_text, str) or not translated_text.strip():
            raise RuntimeError("Vertex AI JSON response is missing translated_text")

        detected_source = parsed.get("source_language")
        resolved_target = parsed.get("target_language")

        return TranslationResult(
            source_language=detected_source if isinstance(detected_source, str) and detected_source.strip() else source_language or "auto",
            target_language=resolved_target if isinstance(resolved_target, str) and resolved_target.strip() else target_language,
            translated_text=translated_text.strip(),
            provider=self.provider,
        )


def build_translator_from_env() -> VertexAITranslator:
    return VertexAITranslator.from_env()


def format_translation(result: TranslationResult) -> str:
    # User-facing Telegram response: only the real Vertex AI translation text.
    return result.translated_text
