from __future__ import annotations

import asyncio

import xenevis

from translator_bot.translator import build_translator_from_env, format_translation


async def main() -> None:
    xenevis.env.load(".env", required=True)

    translator = build_translator_from_env()
    print("Provider: vertex")

    result = await translator.translate(
        "Hello, this is a real Vertex AI translation test.",
        target_language="pl",
    )

    print(format_translation(result))


if __name__ == "__main__":
    asyncio.run(main())
