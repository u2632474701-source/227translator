from __future__ import annotations

from typing import Any


TABLE = "translator_users"


def profile_key(chat_id: str | int, user_id: str | int) -> str:
    return f"{chat_id}:{user_id}"


async def get_user_language(ctx, *, chat_id: str | int, user_id: str | int) -> str | None:
    record = await ctx.data.find_one(
        TABLE,
        {
            "profile_key": profile_key(chat_id, user_id),
        },
    )

    if record is None:
        return None

    data = getattr(record, "data", {}) or {}
    language = data.get("language")

    if isinstance(language, str) and language.strip():
        return language.strip().lower()

    return None


async def set_user_language(
    ctx,
    *,
    chat_id: str | int,
    user_id: str | int,
    language: str,
    username: str = "",
    first_name: str = "",
) -> Any:
    data = {
        "profile_key": profile_key(chat_id, user_id),
        "chat_id": str(chat_id),
        "user_id": str(user_id),
        "username": username or "",
        "first_name": first_name or "",
        "language": language,
        "source": "telegram_setup",
    }

    return await ctx.data.upsert(
        TABLE,
        "profile_key",
        data,
    )
