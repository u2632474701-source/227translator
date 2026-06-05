from __future__ import annotations

import os
from typing import Any, Optional

from xenevis.signals.signal import Signal
from xenevis.telegram.polling import TelegramPollingRunner
from xenevis.telegram.transport import TelegramTransport


_PATCH_INSTALLED = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _default_show_alert() -> bool:
    return _env_bool("TELEGRAM_CALLBACK_SHOW_ALERT", True)


def _default_callback_text() -> str:
    return os.getenv("TELEGRAM_CALLBACK_ALERT_TEXT", "Done").strip() or "Done"


def set_callback_alert(ctx, text: str, *, show_alert: Optional[bool] = None) -> None:
    """Store callback-answer preferences on the current trace.

    Telegram popups/toasts are answerCallbackQuery responses, so this only
    applies to callback_query events, not normal /tr command messages.
    """

    trace = getattr(ctx, "trace", None)
    metadata = getattr(trace, "metadata", None)

    if not isinstance(metadata, dict):
        return

    metadata["telegram_callback_answer"] = {
        "text": text,
        "show_alert": _default_show_alert() if show_alert is None else bool(show_alert),
    }


def install_popup_alert_patch() -> None:
    """Patch current Xenevis Telegram polling to support callback popup alerts.

    This is intentionally a bot-local experiment until Xenevis SDK gets a clean
    public primitive such as:

        xenevis.telegram.answer_callback("...", alert=True)

    The patch keeps Runtime authority unchanged; it only changes how Telegram
    surface answers callback_query after Runtime has produced a trace.
    """

    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    _PATCH_INSTALLED = True

    def answer_callback_query(
        self: TelegramTransport,
        callback_query_id: str,
        *,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "callback_query_id": callback_query_id,
        }

        resolved_text = text if text is not None else _default_callback_text()
        if resolved_text:
            params["text"] = resolved_text[:200]

        if show_alert:
            params["show_alert"] = "true"

        return self.call("answerCallbackQuery", params=params)

    TelegramTransport.answer_callback_query = answer_callback_query  # type: ignore[method-assign]

    async def handle_update(self: TelegramPollingRunner, update: dict) -> None:
        update_id = update.get("update_id")

        if isinstance(update_id, int):
            self._offset = update_id + 1

        self._emit(
            "adapter.event.received",
            status="received",
            data={"adapter": "telegram", "update_id": update_id},
        )

        event = self.normalizer.normalize(update)

        if event is None:
            self._emit(
                "adapter.event.ignored",
                status="ignored",
                data={"adapter": "telegram", "update_id": update_id},
            )
            return

        self._emit(
            "adapter.event.normalized",
            status="normalized",
            data={
                "adapter": "telegram",
                "update_id": update_id,
                "event_type": getattr(event, "type", None),
                "action": getattr(event, "action", None),
            },
        )

        trace = await self.app.execute_event(event)
        output = trace.metadata.get("output")
        rendered = self.renderer.render(output)

        callback_query_id = event.metadata.get("callback_query_id")
        callback_answer = trace.metadata.get("telegram_callback_answer")

        if rendered is None:
            self._emit(
                "telegram.output.skipped",
                status="skipped",
                data={"reason": "no_renderable_output", "trace_id": trace.id},
            )

            if callback_query_id:
                self.transport.answer_callback_query(
                    str(callback_query_id),
                    text=_callback_text(callback_answer),
                    show_alert=_callback_show_alert(callback_answer),
                )
                self._emit(
                    "telegram.callback.answered",
                    status="delivered",
                    trace_id=trace.id,
                    data={
                        "alert": _callback_show_alert(callback_answer),
                        "text": _callback_text(callback_answer),
                    },
                )

            return

        chat_id = self._chat_id_from_event(event)

        if chat_id is None:
            self._emit(
                "telegram.output.skipped",
                status="skipped",
                data={"reason": "missing_chat_id", "trace_id": trace.id},
            )

            if callback_query_id:
                self.transport.answer_callback_query(
                    str(callback_query_id),
                    text=_callback_text(callback_answer),
                    show_alert=_callback_show_alert(callback_answer),
                )
                self._emit(
                    "telegram.callback.answered",
                    status="delivered",
                    trace_id=trace.id,
                    data={
                        "alert": _callback_show_alert(callback_answer),
                        "text": _callback_text(callback_answer),
                    },
                )

            return

        self._emit(
            "telegram.output.created",
            status="created",
            trace_id=trace.id,
            data={"target": chat_id, "method": rendered.get("method")},
        )

        message_id = event.payload.get("message_id") if isinstance(event.payload, dict) else None
        self.transport.deliver(rendered, chat_id=chat_id, message_id=message_id)

        self._emit(
            "telegram.output.delivered",
            status="delivered",
            trace_id=trace.id,
            data={"target": chat_id, "method": rendered.get("method")},
        )

        if callback_query_id:
            self.transport.answer_callback_query(
                str(callback_query_id),
                text=_callback_text(callback_answer),
                show_alert=_callback_show_alert(callback_answer),
            )
            self._emit(
                "telegram.callback.answered",
                status="delivered",
                trace_id=trace.id,
                data={
                    "alert": _callback_show_alert(callback_answer),
                    "text": _callback_text(callback_answer),
                },
            )

    TelegramPollingRunner.handle_update = handle_update  # type: ignore[method-assign]


def _callback_text(callback_answer: Any) -> str:
    if isinstance(callback_answer, dict):
        text = callback_answer.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

    return _default_callback_text()


def _callback_show_alert(callback_answer: Any) -> bool:
    if isinstance(callback_answer, dict) and "show_alert" in callback_answer:
        return bool(callback_answer.get("show_alert"))

    return _default_show_alert()
