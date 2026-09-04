import asyncio
import random


def _bezier_point(t: float, p0: tuple, p1: tuple, p2: tuple) -> tuple[float, float]:
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
    return x, y


def bezier_path(start: tuple[float, float], end: tuple[float, float], steps: int = 20) -> list[tuple[float, float]]:
    """A curved path from start to end via one randomized control point —
    real mouse movement isn't a straight line (§5.2)."""
    control = (
        (start[0] + end[0]) / 2 + random.uniform(-100, 100),
        (start[1] + end[1]) / 2 + random.uniform(-100, 100),
    )
    return [_bezier_point(i / steps, start, control, end) for i in range(1, steps + 1)]


async def human_mouse_move(page, x: float, y: float, *, start: tuple[float, float] = (0, 0)) -> None:
    """Moves the mouse to (x, y) along a bezier curve in small steps with
    randomized micro-delays, instead of teleporting in one call."""
    for px, py in bezier_path(start, (x, y)):
        await page.mouse.move(px, py)
        await asyncio.sleep(random.uniform(0.005, 0.02))
