import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, FOCUS_JS
from a11y_retest141 import DLG, ok, ax


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
        page = await ctx.new_page()
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        await page.click('[data-testid="door-court"]'); await page.wait_for_timeout(2500)
        mods = await page.evaluate("() => [...document.querySelectorAll('[data-testid^=court-module-]')].map(e => e.getAttribute('data-testid') + ' vis=' + (e.getBoundingClientRect().height>0))")
        print("court modules:", mods)
        if not any("vis=true" in m for m in mods):
            tids = await page.evaluate("() => [...document.querySelectorAll('button[data-testid]')].filter(e => e.getBoundingClientRect().height>0).map(e => e.getAttribute('data-testid')).filter(t => /more-tools-toggle/i.test(t))")
            print("expanders:", tids)
            for t in tids[:3]:
                await page.click(f'[data-testid="{t}"]'); await page.wait_for_timeout(1500)
                mods = await page.evaluate("() => [...document.querySelectorAll('[data-testid^=court-module-]')].map(e => e.getAttribute('data-testid') + ' vis=' + (e.getBoundingClientRect().height>0))")
                print(" after", t, mods)
                if any("vis=true" in m for m in mods): break
        target = [m.split(" ")[0] for m in mods if "vis=true" in m and "safety" not in m]
        if target:
            el = page.locator(f'[data-testid="{target[0]}"]')
            await el.scroll_into_view_if_needed(); await el.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
            print("dialogs:", await page.evaluate(DLG), "guided:", await page.locator('[data-testid^="modal-guided-"]').count(), "focus:", await page.evaluate(FOCUS_JS))
            if await page.locator('[data-testid^="modal-guided-"]').count():
                seq = []
                for _ in range(25):
                    await page.keyboard.press("Tab"); seq.append(await page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
                ok(all(seq), f"guided Tab trapped out={seq.count(False)}")
                seq = []
                for _ in range(10):
                    await page.keyboard.press("Shift+Tab"); seq.append(await page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
                ok(all(seq), f"guided Shift+Tab trapped out={seq.count(False)}")
                await ax(page, "guided modal")
                await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
                f = await page.evaluate(FOCUS_JS)
                rem = await page.locator('[data-testid^="modal-guided-"]').count(); print("remaining guided:", rem, "dialogs:", await page.evaluate(DLG))
                ok(rem == 0 and target[0] in f["el"], f"guided Esc closes; focus -> {f} (launcher {target[0]})")
        await b.close()

asyncio.run(main())
