from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    label: str


SUPPORTED_LANGUAGES: tuple[Language, ...] = (
    Language("pl", "Polski"),
    Language("en", "English"),
    Language("de", "Deutsch"),
    Language("uk", "Ukrainian"),
    Language("ru", "Russian"),
    Language("es", "Spanish"),
    Language("fr", "French"),
    Language("it", "Italian"),
)


def normalize_language(code: str | None, fallback: str = "en") -> str:
    if not code:
        return fallback

    normalized = code.strip().lower().replace("_", "-")
    base = normalized.split("-", 1)[0]
    supported = {language.code for language in SUPPORTED_LANGUAGES}

    if normalized in supported:
        return normalized
    if base in supported:
        return base
    return fallback


def language_label(code: str) -> str:
    normalized = normalize_language(code)
    for language in SUPPORTED_LANGUAGES:
        if language.code == normalized:
            return language.label
    return normalized.upper()


def language_buttons(xenevis, token: str):
    # Current SDK TelegramUI validates `inline` as a flat list of TelegramButton
    # objects. The renderer can handle rows, but UI validation runs first.
    return [
        xenevis.telegram.button.callback(
            language.label,
            f"tr_setup:{token}:{language.code}",
        )
        for language in SUPPORTED_LANGUAGES
    ]
