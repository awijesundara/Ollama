import asyncio
import json

from src.runtime import services


async def main() -> int:
    try:
        await services.start()
        database = await services.database.health_check()
        ollama = await services.ollama.health_check()
        models = await services.ollama.models_available(
            {
                services.settings.OLLAMA_CHAT_MODEL,
                services.settings.OLLAMA_EMBEDDING_MODEL,
            }
        )
        result = {"database": database, "ollama": ollama, "models": models}
        print(json.dumps(result))
        return 0 if all(result.values()) else 1
    finally:
        await services.database.close()
        await services.ollama.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
