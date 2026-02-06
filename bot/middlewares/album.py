import asyncio
from typing import Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.6):
        self.latency = latency
        self.album_data = {}

    async def __call__(self, handler, event: Message, data: Dict[str, Any]) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        key = event.media_group_id
        if key not in self.album_data:
            self.album_data[key] = []
            asyncio.create_task(self.dispatch_album(handler, event, key, data))

        self.album_data[key].append(event)
        return

    async def dispatch_album(self, handler, event, key, data):
        await asyncio.sleep(self.latency)
        if key in self.album_data:
            data["album"] = self.album_data[key]
            del self.album_data[key]
            await handler(event, data)