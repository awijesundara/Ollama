GHOST_ACTIVITY_LINGER_SECONDS = 4.0


def format_activity_text(status: str) -> str:
    """Format a truthful task status for the transient ghost activity row."""
    clean = " ".join(status.split()).strip().rstrip(".…")
    return f"**{clean}…**"
