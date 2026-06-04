"""Capture raw mobile-layout screen content (no device frame) for marketing.

Captured at iPhone-14-Pro-Max logical viewport (430x932) with deviceScaleFactor=3
so output is 1290x2796 — exactly Apple's required 6.7" portrait pixel size.
"""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

PREVIEW = "https://prepared-parents.preview.emergentagent.com"
OUT_DIR = Path("/app/memory/app_store_assets/refreshed_feb2026/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# iPhone 14 Pro Max logical pts (430x932) with 3x scale = 1290x2796 px output
VW, VH, DSF = 430, 932, 3

LEGAL_LS = '{"version":"v1","at":"2026-02-12T00:00:00.000Z"}'
ORI_LS = "true"
VERIFY_DISMISS_LS = "9999999999999"  # far future so banner is hidden

ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PW = "AdminPass123!"


SCREENS = [
    ("01_dashboard", "/dashboard"),
    ("02_child_goals", "/prep/child-goals"),
    ("03_communication", "/prep/communication"),
    ("04_summary", "/summary"),
    ("05_reflection", "/reflection"),
    ("06_safety", "/safety"),
]


async def login_and_set_ls(page):
    await page.goto(f"{PREVIEW}/login", wait_until="domcontentloaded")
    await page.evaluate(
        """([legalK, legalV, oriK, oriV, vbK, vbV]) => {
            try {
                localStorage.setItem(legalK, legalV);
                localStorage.setItem(oriK, oriV);
                localStorage.setItem(vbK, vbV);
            } catch (_) {}
        }""",
        [
            "sac_legal_ack_v1", LEGAL_LS,
            "sacoparents.orientation_seen.v1", ORI_LS,
            "sac_verify_banner_dismissed_at", VERIFY_DISMISS_LS,
        ],
    )
    await page.goto(f"{PREVIEW}/login", wait_until="networkidle")
    await page.fill('[data-testid="login-email-input"]', ADMIN_EMAIL)
    await page.fill('[data-testid="login-password-input"]', ADMIN_PW)
    await page.click('[data-testid="login-submit-button"]')
    try:
        await page.wait_for_url("**/dashboard", timeout=10000)
    except Exception:
        pass


async def capture(page, route, out_file):
    await page.goto(f"{PREVIEW}{route}", wait_until="networkidle")
    await page.wait_for_timeout(1500)
    # Hide Emergent watermark/badge if present
    await page.evaluate(
        """() => {
            const sels = [
                'a[href*="emergent"]',
                'iframe[src*="emergent"]',
                '[class*="emergent-badge"]',
            ];
            sels.forEach(s => document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; }));
        }"""
    )
    # Take the visible viewport (not full page) — matches what users actually see
    await page.screenshot(path=str(out_file), full_page=False, type="png")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": VW, "height": VH},
            device_scale_factor=DSF,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        page = await context.new_page()
        await login_and_set_ls(page)

        for slug, route in SCREENS:
            out = OUT_DIR / f"{slug}.png"
            print(f"Capturing {route} -> {out}")
            try:
                await capture(page, route, out)
            except Exception as e:
                print(f"  FAIL: {e}")
        await browser.close()


if __name__ == "__main__":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
    asyncio.run(main())
