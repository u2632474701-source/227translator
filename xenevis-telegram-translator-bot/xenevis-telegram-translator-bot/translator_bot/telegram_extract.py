from __future__ import annotations

from typing import Any


def payload(ctx) -> dict[str, Any]:
    value = getattr(ctx, "payload", {}) or {}
    return value if isinstance(value, dict) else {}


def current_message(ctx) -> dict[str, Any]:
    msg = payload(ctx).get("message")
    return msg if isinstance(msg, dict) else {}


def current_chat_id(ctx) -> str | int | None:
    p = payload(ctx)
    if p.get("chat_id") is not None:
        return p["chat_id"]

    chat = current_message(ctx).get("chat")
    if isinstance(chat, dict):
        return chat.get("id")

    return None


def current_message_id(ctx) -> str | int | None:
    p = payload(ctx)
    if p.get("message_id") is not None:
        return p["message_id"]

    return current_message(ctx).get("message_id")


def reply_to_message(ctx) -> dict[str, Any] | None:
    reply = current_message(ctx).get("reply_to_message")
    return reply if isinstance(reply, dict) else None


def text_from_message(message: dict[str, Any] | None) -> str | None:
    if not isinstance(message, dict):
        return None

    for key in ("text", "caption"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def callback_data(ctx) -> str | None:
    value = payload(ctx).get("data")
    return str(value) if value is not None else None


def user_snapshot(ctx) -> dict[str, str]:
    identity = getattr(ctx, "identity", None)
    return {
        "user_id": str(getattr(identity, "id", "") or ""),
        "username": str(getattr(identity, "username", "") or ""),
        "first_name": str(getattr(identity, "display_name", "") or ""),
    }
