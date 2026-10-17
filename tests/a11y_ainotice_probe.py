import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, FOCUS_JS
from a11y_retest141 import DLG, ok, ax


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        await page.locator('[data-testid="nav-biff"]').click(); await page.wait_for_timeout(1500)
        print("after nav-biff:", await page.evaluate(DLG), "focus", await page.evaluate(FOCUS_JS))
        D = '[data-testid="biff-coach-drawer"]'
        print("textareas:", await page.evaluate("(s) => [...document.querySelectorAll(s + ' textarea')].map(t => t.getAttribute('data-testid') + ' ro=' + t.readOnly + ' h=' + t.getBoundingClientRect().height)", D))
        ta = page.locator(f'{D} textarea').first
        await ta.focus(); print("focus ta:", await page.evaluate(FOCUS_JS))
        await page.keyboard.press("Enter"); await page.wait_for_timeout(1500)
        print("after Enter:", await page.evaluate(DLG), await page.evaluate(FOCUS_JS))
        if await page.locator('[data-testid="consent-screen"]').count():
            for cb in await page.locator('[data-testid="consent-screen"] input[type=checkbox]').all():
                await cb.check(force=True)
            await page.click('[data-testid="consent-screen-continue"]'); await page.wait_for_timeout(3000)
            print("after consent:", await page.evaluate(DLG), await page.evaluate(FOCUS_JS), "drawer:", await page.locator(D).count())
            await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
            print("after Esc on AI notice:", await page.evaluate(DLG))
            await page.locator('[data-testid="nav-biff"]').click(); await page.wait_for_timeout(1500)
            print("drawer reopened:", await page.locator(D).count())
        if await page.locator(D).count() and len(await page.evaluate(DLG)) < 2:
            await page.locator(f'{D} textarea').first.click(); await page.wait_for_timeout(1500)
            print("after click:", await page.evaluate(DLG), await page.evaluate(FOCUS_JS))
        dl = await page.evaluate(DLG)
        if len(dl) >= 2:
            await ax(page, "guest AI notice")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
            dl2 = await page.evaluate(DLG)
            ok(len(dl2) == 1, f"1st Esc closes only AI notice: {dl2} focus={await page.evaluate(FOCUS_JS)}")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
            f = await page.evaluate(FOCUS_JS)
            ok(await page.locator(D).count() == 0 and "nav-biff" in f["el"], f"2nd Esc closes drawer; focus {f}")
        await b.close()

asyncio.run(main())
