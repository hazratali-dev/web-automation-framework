"""Navigation Timing / Paint Timing / PerformanceObserver capture (§5.2, §3
metrics.metric_name: lcp/fcp/ttfb/cls/load_time_ms)."""

# Must run via add_init_script BEFORE navigation — LCP/CLS are only ever
# reported through a PerformanceObserver, there's no "read it after the fact"
# API, so we start collecting into window.__metrics as soon as the document
# starts loading.
_OBSERVER_INIT_SCRIPT = """
(() => {
    window.__metrics = { lcp: 0, cls: 0 };
    try {
        new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const last = entries[entries.length - 1];
            if (last) window.__metrics.lcp = last.renderTime || last.loadTime || 0;
        }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {}
    try {
        new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    window.__metrics.cls = (window.__metrics.cls || 0) + entry.value;
                }
            }
        }).observe({ type: 'layout-shift', buffered: true });
    } catch (e) {}
})();
"""

_READ_METRICS_SCRIPT = """
() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paintEntries = performance.getEntriesByType('paint');
    const fcp = paintEntries.find((p) => p.name === 'first-contentful-paint');
    return {
        ttfb: nav ? nav.responseStart : null,
        load_time_ms: nav ? nav.loadEventEnd : null,
        fcp: fcp ? fcp.startTime : null,
        lcp: window.__metrics ? window.__metrics.lcp : null,
        cls: window.__metrics ? window.__metrics.cls : null,
    };
}
"""


async def install_metrics_observer(context) -> None:
    """Context-level init script — must be registered before the page
    navigates, since LCP/CLS can only be observed live, not read after."""
    await context.add_init_script(_OBSERVER_INIT_SCRIPT)


async def read_performance_metrics(page) -> dict[str, float | None]:
    return await page.evaluate(_READ_METRICS_SCRIPT)
