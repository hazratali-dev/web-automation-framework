import asyncio
import random


async def human_type(page, selector: str, text: str) -> None:
    """Types character-by-character with a randomized 50-200ms delay per
    key-stroke (§5.2), instead of Playwright's instant fill()."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.2))
