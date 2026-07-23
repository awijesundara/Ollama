import argparse
import asyncio
import statistics
import time
from uuid import uuid4

from src.auth.identity import AuthenticatedIdentity
from src.ollama.models import ChatMessage
from src.runtime import services


async def one_request(identity: AuthenticatedIdentity, number: int) -> float:
    started = time.monotonic()
    await services.require_retriever().retrieve(
        identity,
        f"load-thread-{number % 10}",
        "Return the word healthy.",
    )
    async for _ in services.ollama.stream_chat(
        [ChatMessage(role="user", content="Return the word healthy.")]
    ):
        pass
    return time.monotonic() - started


async def main(concurrency: int, requests: int) -> None:
    await services.start()
    prefix = f"load-test-{uuid4()}"
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(number: int) -> float:
        async with semaphore:
            return await one_request(
                AuthenticatedIdentity(f"{prefix}-{number % concurrency}"),
                number,
            )

    try:
        latencies = await asyncio.gather(
            *(bounded(number) for number in range(requests))
        )
        ordered = sorted(latencies)
        p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
        print(
            {
                "requests": requests,
                "concurrency": concurrency,
                "mean_seconds": statistics.mean(latencies),
                "p95_seconds": p95,
                "max_seconds": max(latencies),
            }
        )
    finally:
        await services.database.close()
        await services.ollama.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.concurrency, arguments.requests))
