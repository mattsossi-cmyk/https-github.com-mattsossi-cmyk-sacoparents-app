"""Follow-up a11y probes: overflow culprits, AI notice/consent modals, guided modal, drawer focus."""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, AXE, AXE_JS, TAGS, FOCUS_JS

CULPRIT = """() => [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 2; })
 .filter(e => ![...e.children].some(c => c.getBoundingClientRect().right > innerWidth + 2)).slice(0, 6)
 .map(e => `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,50)}] w=${Math.round(e.getBoundingClientRect().width)} r=${Math.round(e.getBoundingClientRect().right)}`)"""
DLG = "() => [...document.querySelectorAll('[role=dialog],[role=alertdialog]')].map(d => d.getAttribute('data-testid') + ' modal=' + d.getAttribute('aria-modal') + ' label=' + (d.getAttribute('aria-labelledby') || d.getAttribute('aria-label')))"


async def ax(page, label):
    await page.add_script_tag(content=AXE)
    v = await page.evaluate(AXE_JS, {"ctx": None, "tags": TAGS})
    print(f"== {label}: {[(x['id'], x['n']) for x in v]}")
    for x in v:
        for n in x["nodes"][:3]:
            print("   ", x["id"], n["t"], "::", n["html"][:90])


async def tabs(page, n):
    out = []
    for _ in range(n):
        await page.keyboard.press("Tab"); out.append((await page.evaluate(FOCUS_JS)))
    return out


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for who in ("guest", "parent"):
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            if who == "parent":
                await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
            page = await ctx.new_page()
            for path in (["/register"] if who == "guest" else ["/"]):
                await page.goto(BASE + path); await page.wait_for_timeout(3000)
                await page.evaluate("document.documentElement.style.fontSize='200%'"); await page.wait_for_timeout(400)
                print(who, path, "root200 culprits:", await page.evaluate(CULPRIT))
                await page.evaluate("document.documentElement.style.fontSize=''")
                await page.set_viewport_size({"width": 195, "height": 844}); await page.wait_for_timeout(500)
                print(who, path, "195px culprits:", await page.evaluate(CULPRIT))
                await page.set_viewport_size({"width": 390, "height": 844})
            await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
            try:
                await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1200)
                print(who, "initial focus in drawer:", await page.evaluate(FOCUS_JS))
                await page.locator('[data-testid="biff-coach-drawer"] textarea').first.click(force=True); await page.wait_for_timeout(2500)
                print(who, "dialogs after textarea click:", await page.evaluate(DLG), "focus:", await page.evaluate(FOCUS_JS))
                if await page.evaluate("() => document.querySelectorAll('[role=dialog],[role=alertdialog]').length"):
                    await ax(page, who + " AI/consent modal")
                    seq = await tabs(page, 8)
                    print("   tab seq:", [s["el"] for s in seq], "outside:", [s["el"] for s in seq if not s.get("inDialog")])
                    await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
                    print("   after Esc dialogs:", await page.evaluate(DLG), "focus:", await page.evaluate(FOCUS_JS))
            except Exception as e:
                print(who, "modal ERR", str(e)[:160])
            if who == "parent":
                await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
                for sel in ('[data-testid="door-self"]', '[data-testid="door-court"]'):
                    try:
                        await page.click(sel); await page.wait_for_timeout(2500)
                        n = await page.locator('[data-testid^="toolkit-guided-"]').count()
                        print("guided launchers after", sel, n)
                        if n:
                            g = page.locator('[data-testid^="toolkit-guided-"]').first
                            await g.scroll_into_view_if_needed(); await g.click(); await page.wait_for_timeout(2500)
                            print("guided dialogs:", await page.evaluate(DLG), "focus:", await page.evaluate(FOCUS_JS))
                            await ax(page, "guided modal")
                            seq = await tabs(page, 8)
                            print("   guided tab outside modal:", [s["el"] for s in seq if not s.get("inDialog")])
                            await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
                            print("   guided after Esc:", await page.locator('[data-testid^="modal-guided-"]').count(), await page.evaluate(FOCUS_JS))
                            break
                        await page.goto(BASE + "/"); await page.wait_for_timeout(3000)
                    except Exception as e:
                        print("guided ERR", str(e)[:160])
            await ctx.close()
        await b.close()

asyncio.run(main())
