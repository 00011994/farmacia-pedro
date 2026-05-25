import asyncio
import json
import os
from datetime import datetime

import websockets

clients: set = set()


async def notify_all(event: dict) -> None:
    if not clients:
        return
    msg = json.dumps(event, ensure_ascii=False)
    await asyncio.gather(*[client.send(msg) for client in set(clients)], return_exceptions=True)


async def event_producer() -> None:
    last_mtime = None
    path = os.path.join("out", "report.json")
    while True:
        try:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if last_mtime is None:
                    last_mtime = mtime
                elif mtime != last_mtime:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    await notify_all({
                        "type": "report_update",
                        "timestamp": datetime.now().isoformat(),
                        "data": data,
                    })
                    last_mtime = mtime
        except Exception as exc:
            print(f"[ws_server] Erro no event_producer: {exc}")
        await asyncio.sleep(2)


async def handler(websocket) -> None:
    clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    finally:
        clients.discard(websocket)


async def main() -> None:
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server ativo em ws://0.0.0.0:8765")
        await event_producer()


if __name__ == "__main__":
    asyncio.run(main())
