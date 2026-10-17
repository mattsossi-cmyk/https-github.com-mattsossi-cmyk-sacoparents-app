"""Iter141 quick Safety Gate UI regression: linked parents banner, /case-settings, plan-options after webhook, /help quick exit, admin audit export."""
import asyncio, json, subprocess, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE
from a11y_retest141 import ok

SETUP = "/app/backend/tests/fe_gate_setup.py"


async def login(b, email, pw):
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, accept_downloads=True)
    r = await ctx.request.post(BASE + "/api/auth/login", data={"email": email, "password": pw})
    print("login", email.split("@")[0], r.status)
    return ctx, await ctx.new_page()


async def main():
    admin_email, admin_pw = sys.argv[1], sys.argv[2]
    info = json.loads(subprocess.check_output(["python", SETUP, "setup"], cwd="/app/backend").decode().strip().splitlines()[-1])
    cid = info["case"]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        texts = []
        for who in ("a", "b"):
            ctx, page = await login(b, info[who], "Str0ng!Pass99")
            await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
            if await page.locator('[data-testid="consent-screen"]').count():
                print("consent screen shown for", who)
            bn = page.locator('[data-testid="case-settings-banner-text"]').first
            texts.append(await bn.inner_text() if await bn.count() else None)
            await ctx.close()
        ok(texts[0] and texts[0] == texts[1], f"both parents same banner: {texts}")
        code = subprocess.check_output(["python", SETUP, "send", cid, "1", "structured", "professional", "parallel_parenting"], cwd="/app/backend").decode().strip()
        print("webhook status:", code)
        for who in ("a", "b"):
            ctx, page = await login(b, info[who], "Str0ng!Pass99")
            await page.goto(BASE + "/"); await page.wait_for_timeout(4000)
            body = await page.locator("body").inner_text()
            card = await page.locator('[data-testid="plan-options-card"]').count()
            ok("Some features are set by your professional for this case." in body and card == 1, f"{who}: professional text + plan-options-card ({card})")
            if who == "a" and card:
                await page.click('[data-testid="plan-options-card-button"]'); await page.wait_for_timeout(2500)
                opts = await page.evaluate("() => [...document.querySelectorAll('[data-testid^=plan-option-]')].map(e => e.getAttribute('data-testid'))")
                ok(page.url.endswith("/plan-options") and opts, f"plan-options page opts={opts}")
            await ctx.close()
        # help quick exit (guest)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = await ctx.new_page()
        await page.goto(BASE + "/login"); await page.wait_for_timeout(1500)
        await page.goto(BASE + "/help"); await page.wait_for_timeout(2500)
        await page.click('[data-testid="help-quick-exit"]'); await page.wait_for_timeout(2500)
        ok(page.url.endswith("/calendar"), f"quick exit -> {page.url}")
        await page.go_back(); await page.wait_for_timeout(2000)
        ok("/help" not in page.url, f"Back after quick exit -> {page.url}")
        await ctx.close()
        # admin
        ctx, page = await login(b, admin_email, admin_pw)
        await page.goto(BASE + "/admin/audit-log"); await page.wait_for_timeout(3500)
        before = await page.locator('[data-testid="admin-audit-page"] table').inner_text() if await page.locator('[data-testid="admin-audit-page"] table').count() else ""
        try:
            async with page.expect_download(timeout=20000) as dl:
                await page.click('[data-testid="admin-audit-export"]')
            d = await dl.value
            ok(d.suggested_filename.endswith(".csv"), f"export download {d.suggested_filename}")
        except Exception as e:
            ok(False, f"export download ERR {str(e)[:120]}")
        await page.wait_for_timeout(2500)
        after = await page.locator('[data-testid="admin-audit-page"] table').inner_text() if await page.locator('[data-testid="admin-audit-page"] table').count() else ""
        print("daily counts before:", before[:200].replace("\n", " | "))
        print("daily counts after :", after[:200].replace("\n", " | "))
        ok(after and after != before, "daily counts updated after export")
        sw = await page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        ok(sw, "no horizontal overflow on audit page at 390")
        await ctx.close(); await b.close()

if __name__ == "__main__":
    asyncio.run(main())
