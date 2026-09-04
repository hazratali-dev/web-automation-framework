"""Fingerprint resistance (§5.2) — masks the most common headless/automation
tells. Not a guarantee against determined fingerprinting, just the standard
baseline: hide `navigator.webdriver`, fill in the properties a real Chrome
window has that a bare headless one doesn't, and add tiny noise to
canvas/WebGL reads so two sessions don't produce byte-identical fingerprints.
"""

STEALTH_INIT_SCRIPT = """
(() => {
    // 1. The single biggest automation tell.
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. Headless Chrome has an empty plugins/mimeTypes list; real Chrome doesn't.
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

    // 3. `window.chrome` is absent in headless without this stub.
    window.chrome = window.chrome || { runtime: {} };

    // 4. Permissions API leak: headless reports 'denied' for notifications
    // without a prompt ever being shown; real Chrome asks first.
    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (originalQuery) {
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
    }

    // 5. Canvas/WebGL noise — nudge pixel data slightly so repeated sessions
    // don't produce byte-identical canvas fingerprints.
    const noisify = (canvas, context) => {
        if (!context) return;
        const shift = Math.floor(Math.random() * 3) - 1;
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + shift));
        }
        context.putImageData(imageData, 0, 0);
    };
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function (...args) {
        try {
            noisify(this, this.getContext('2d'));
        } catch (e) {
            /* canvas may be WebGL-backed; ignore */
        }
        return originalToDataURL.apply(this, args);
    };

    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (parameter) {
        // UNMASKED_VENDOR_WEBGL / UNMASKED_RENDERER_WEBGL
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.apply(this, [parameter]);
    };
})();
"""


async def apply_stealth(context) -> None:
    """Injects the stealth script at context level, so it runs before any
    page (or navigation within a page) in this context ever observes the
    un-patched values (§5.2)."""
    await context.add_init_script(STEALTH_INIT_SCRIPT)
