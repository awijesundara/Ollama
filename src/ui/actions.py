import json

import chainlit as cl


async def confirm_destructive_action(label: str) -> bool:
    response = await cl.AskActionMessage(
        content=f"Confirm: {label}",
        actions=[
            cl.Action(
                name="confirm",
                label="Confirm",
                payload={"value": "confirm"},
            ),
            cl.Action(
                name="cancel",
                label="Cancel",
                payload={"value": "cancel"},
            ),
        ],
        timeout=90,
    ).send()
    return bool(response and response.get("payload", {}).get("value") == "confirm")


async def send_json_export(data: dict[str, object]) -> None:
    encoded = json.dumps(data, indent=2, default=str).encode()
    element = cl.File(
        name="my-memories.json",
        content=encoded,
        display="inline",
        mime="application/json",
    )
    await cl.Message(content="Your memory export is ready.", elements=[element]).send()

