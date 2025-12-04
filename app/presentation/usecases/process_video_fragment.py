from __future__ import annotations

import asyncio

from app.application.video.processor import process_video

url = "http://localhost:8000/media/5be64b77856745c4a332192147ed0eea/index.m3u8"

ranges = [
    {
        "start_at": "2025-01-01T10:00:00",
        "end_at":   "2025-01-01T10:00:08",
    },
    {
        "start_at": "2025-01-01T10:00:12",
        "end_at":   "2025-01-01T10:00:19",
    },
    {
        "start_at": "2025-01-01T10:00:25",
        "end_at":   "2025-01-01T10:00:30",
    },
]

source_id = "test-source-id-1"


async def main() -> None:
    await process_video(
        video_source=url,
        source_id=source_id,
        ranges=ranges,
    )


if __name__ == "__main__":
    asyncio.run(main())