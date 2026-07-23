# Load testing

Run `scripts/load_test.py` only against an isolated, migrated performance
environment with non-production Ollama capacity.

Test separate profiles for:

- increasing concurrent authenticated identities;
- long-running streamed generations and cancellation;
- PostgreSQL pool size plus one, twice pool size, and sustained saturation;
- users with 0, 100, and 500 memories;
- resumed threads with 100, 1,000, and 10,000 persisted steps;
- Ollama response delays beyond the configured timeout.

Record p50, p95, p99, failures, database pool usage, Ollama queue depth, memory
retrieval latency, and resume latency. Do not use real user identifiers,
messages, or memories in load data.

