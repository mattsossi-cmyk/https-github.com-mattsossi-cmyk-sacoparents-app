"""Record a ~45-second scripted in-app tour that matches the narration beats.

Output: /app/memory/intro_video_work/raw.webm  (540x1170 @ 25fps)

Beat plan (matches build_intro_narration.py SCRIPT):
  0–4s   "Welcome to SA Coparents — the calm space..."     → Landing
  4–10s  "Going through separation is hard..."             → Dashboard
  10–15s "Start by setting your child-centered goals..."   → Child Goals
  15–21s "Work through your real concerns..."              → Issues
  21–27s "Practice softer communication..."                → Communication
  27–33s "Capture honest reflections..."                   → Reflection
  33–40s "Our intelligent assistant prepares..."           → Summary
  40–45s "No conflict. No surprises..."                    → Resources / Safety
"""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

PREVIEW = "https://prepared-parents.preview.emergentagent.com"
WORK = Path("/app/memory/intro_video_work")
WORK.mkdir(parents=True, exist_ok=True)

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
            record_video_dir=str(WORK),
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
        await page.wait_for_timeout(1200)

        async def hide_overlay():
            await page.evaluate(
                """() => {
                    const sels = ['a[href*="emergent"]','iframe[src*="emergent"]','[class*="emergent-badge"]'];
                    sels.forEach(s => document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; }));
                }"""
            )

        async def visit(route, dwell_ms, scroll=True):
            await page.goto(f"{PREVIEW}{route}", wait_until="networkidle")
            await hide_overlay()
            await page.wait_for_timeout(500)
            if scroll:
                await page.evaluate("""async () => {
                    await new Promise(r => {
                        let y = 0;
                        const id = setInterval(() => {
                            y += 6;
                            window.scrollTo(0, y);
                            if (y > 600) { clearInterval(id); r(); }
                        }, 20);
                    });
                }""")
            await page.wait_for_timeout(dwell_ms)

        # 1. Landing (~4s)
        await visit("/", dwell_ms=3500, scroll=False)
        # 2. Dashboard (~6s)
        await visit("/dashboard", dwell_ms=5500, scroll=True)
        # 3. Child Goals (~5s)
        await visit("/prep/child-goals", dwell_ms=5000, scroll=True)
        # 4. Issues & Concerns (~6s)
        await visit("/prep/issues", dwell_ms=6000, scroll=True)
        # 5. Communication (~6s)
        await visit("/prep/communication", dwell_ms=6000, scroll=True)
        # 6. Reflection (~6s)
        await visit("/reflection", dwell_ms=6000, scroll=True)
        # 7. Summary (~7s)
        await visit("/summary", dwell_ms=7000, scroll=True)
        # 8. Safety (~5s)
        await visit("/safety", dwell_ms=5000, scroll=True)

        await context.close()
        await browser.close()

        for f in WORK.glob("*.webm"):
            target = WORK / "raw.webm"
            if f != target:
                f.rename(target)
        print("Recorded:", WORK / "raw.webm")


if __name__ == "__main__":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
    asyncio.run(main())
