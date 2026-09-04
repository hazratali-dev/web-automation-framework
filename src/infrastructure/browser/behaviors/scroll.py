import asyncio
import random


async def human_scroll(page, *, steps: int = 5, step_px: int = 300) -> None:
    """Scrolls down in steps with randomized pauses in between — simulates
    someone reading the page rather than jumping straight to the bottom
    (§5.2)."""
    for _ in range(steps):
        await page.mouse.wheel(0, step_px + random.randint(-50, 50))
        await asyncio.sleep(random.uniform(0.3, 1.2))


async def think_time(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """A randomized pause between actions (§5.2)."""
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))
