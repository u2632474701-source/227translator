# Xenevis Telegram Translator Bot — Vertex AI + callback popup alerts

To jest eksperymentalna wersja bota z popup/toast alertami dla kliknięć inline buttonów.

Ważne: Telegramowe popupy są częścią `answerCallbackQuery`, więc działają tylko dla callbacków, czyli kliknięć w inline keyboard. Zwykła komenda `/tr` nie ma popupu, bo jest zwykłą wiadomością.

## Co jest nowe

- `VERTEX_TIMEOUT_SECONDS=30`
- `TELEGRAM_CALLBACK_SHOW_ALERT=true`
- bot-local experimental patch dla callback popup alerts
- callback może pokazać:
  - sukces: `Translation ready.`
  - timeout: popup z timeoutem
  - quota/rate limit: popup z limitem Vertex AI
  - błędny/expired token: popup z błędem

## `.env`

```env
TELEGRAM_BOT_TOKEN=...

GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json

GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=global
VERTEX_MODEL=gemini-2.5-flash
VERTEX_TIMEOUT_SECONDS=30

TELEGRAM_CALLBACK_SHOW_ALERT=true
TELEGRAM_CALLBACK_ALERT_TEXT=Done
```

`TELEGRAM_CALLBACK_SHOW_ALERT=true` oznacza modalny popup.

`TELEGRAM_CALLBACK_SHOW_ALERT=false` oznacza mały toast na górze Telegrama.

## Instalacja

```bat
py -m pip install -r requirements.txt
```

## Uruchomienie

```bat
py main.py
```

## Ważne ograniczenie

To jest bot-local eksperyment. Docelowo Xenevis SDK powinien dostać publiczne API typu:

```python
xenevis.telegram.answer_callback("Translation ready.", alert=True)
```

albo metadata na `xenevis.telegram.edit(...)`, zamiast monkeypatcha polling/transportu.
