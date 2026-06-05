"""Record an App Store preview tour of SACOParents.

Output: /app/memory/app_store_assets/refreshed_feb2026/preview_video/raw.webm

Pipeline:
1. Playwright records a scripted tour of the app at iPhone-sized viewport.
2. refresh_video_compose.py post-processes: adds brand intro + outro cards,
   converts to MP4 (H.264), pads/scales to 1080x1920 (Apple-acceptable size).
"""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

PREVIEW = "https://prepared-parents.preview.emergentagent.com"
OUT_DIR = Path("/app/memory/app_store_assets/refreshed_feb2026/preview_video")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Record at exact 540x1170 (matches iPhone 6.7" aspect 9:19.5). dsf=1.
# ffmpeg post will upscale to 1080x1920 with Lanczos.
VW, VH = 540, 1170

LEGAL_LS = '{"version":"v1","at":"2026-02-12T00:00:00.000Z"}'
ORI_LS = "true"
VERIFY_LS = "9999999999999"

ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PW = "AdminPass123!"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": VW, "height": VH},
            device_scale_factor=1,
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": VW, "height": VH},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
            ),
        )
        page = await context.new_page()

        # ----- Login & prep -----
        await page.goto(f"{PREVIEW}/login", wait_until="domcontentloaded")
        await page.evaluate(
            """([a,b,c,d,e,f]) => { try {
                localStorage.setItem(a,b); localStorage.setItem(c,d); localStorage.setItem(e,f);
            } catch(_){} }""",
            ["sac_legal_ack_v1", LEGAL_LS,
             "sacoparents.orientation_seen.v1", ORI_LS,
             "sac_verify_banner_dismissed_at", VERIFY_LS],
        )
        await page.goto(f"{PREVIEW}/login", wait_until="networkidle")
        await page.fill('[data-testid="login-email-input"]', ADMIN_EMAIL)
        await page.fill('[data-testid="login-password-input"]', ADMIN_PW)
        await page.click('[data-testid="login-submit-button"]')
        try:
            await page.wait_for_url("**/dashboard", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        # Helper: hide Emergent watermark
        async def hide_overlay():
            await page.evaluate(
                """() => {
                    const sels = ['a[href*="emergent"]','iframe[src*="emergent"]','[class*="emergent-badge"]'];
                    sels.forEach(s => document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; }));
                }"""
            )

        # ----- Tour -----
        async def visit(route, dwell_ms=2800, scroll=False):
            await page.goto(f"{PREVIEW}{route}", wait_until="networkidle")
            await hide_overlay()
            await page.wait_for_timeout(600)
            if scroll:
                # Gentle scroll for visual interest
                await page.evaluate("""async () => {
                    await new Promise(r => {
                        let y = 0;
                        const id = setInterval(() => {
                            y += 8;
                            window.scrollTo(0, y);
                            if (y > 400) { clearInterval(id); r(); }
                        }, 16);
                    });
                }""")
            await page.wait_for_timeout(dwell_ms)

        # 1. Dashboard ~3.5s
        await visit("/dashboard", dwell_ms=3000, scroll=True)
        # 2. Child Goals ~3s
        await visit("/prep/child-goals", dwell_ms=2800, scroll=True)
        # 3. Communication ~3s
        await visit("/prep/communication", dwell_ms=2800, scroll=True)
        # 4. Readiness ~3s
        await visit("/prep/readiness", dwell_ms=2800, scroll=True)
        # 5. Summary ~3.5s
        await visit("/summary", dwell_ms=3200, scroll=True)
        # 6. Reflection ~3s
        await visit("/reflection", dwell_ms=2800, scroll=True)
        # 7. Safety ~3s
        await visit("/safety", dwell_ms=2800, scroll=True)

        await context.close()
        await browser.close()

        # Playwright dumped the video to OUT_DIR with a random name; rename it
        for f in OUT_DIR.glob("*.webm"):
            target = OUT_DIR / "raw.webm"
            if f != target:
                f.rename(target)
        print("Recorded:", OUT_DIR / "raw.webm")


if __name__ == "__main__":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
    asyncio.run(main())
