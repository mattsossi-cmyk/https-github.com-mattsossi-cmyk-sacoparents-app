import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE
from a11y_retest141 import ok, bad_words, RECT

CUL = """() => { const vw = document.documentElement.clientWidth; return [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > vw + 1; })
 .filter(e => ![...e.children].some(c => c.getBoundingClientRect().right > vw + 1)).slice(0, 6)
 .map(e => `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,60)}] pos=${getComputedStyle(e).position} '${(e.textContent||'').trim().slice(0,20)}' r=${Math.round(e.getBoundingClientRect().right)} vw=${vw}`); }"""


async def chk(page, label):
    for w, fs in ((390, "200%"), (195, "")):
        await page.set_viewport_size({"width": w, "height": 844}); await page.evaluate(f"document.documentElement.style.fontSize='{fs}'"); await page.wait_for_timeout(700)
        sw = await page.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        print(f"{label} w={w} fs={fs or '100%'} scroll={sw} culprits={await page.evaluate(CUL)}")
    await page.set_viewport_size({"width": 390, "height": 844}); await page.evaluate("document.documentElement.style.fontSize=''")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        await page.goto(BASE + "/register"); await page.wait_for_timeout(2500)
        await chk(page, "/register")
        await ctx.close()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
        page = await ctx.new_page()
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        await chk(page, "portal home")
        chips = await page.evaluate("() => [...document.querySelectorAll('[class*=\"text-[0.\"]')].filter(e => e.getBoundingClientRect().height>0).slice(0,3).map(e => e.className.toString().match(/text-\\[[^\\]]+\\]/)[0] + '=' + getComputedStyle(e).fontSize)")
        await page.evaluate("document.documentElement.style.fontSize='200%'"); await page.wait_for_timeout(400)
        chips2 = await page.evaluate("() => [...document.querySelectorAll('[class*=\"text-[0.\"]')].filter(e => e.getBoundingClientRect().height>0).slice(0,3).map(e => getComputedStyle(e).fontSize)")
        print("portal rem chips 100% -> 200%:", chips, chips2)
        px = await page.evaluate("() => [...document.querySelectorAll('[class*=\"text-[\"][class*=\"px]\"]')].filter(e => e.getBoundingClientRect().height>0).slice(0,5).map(e => (e.getAttribute('data-testid')||'') + ' ' + e.className.toString().match(/text-\\[\\d+px\\]/))")
        print("remaining px font classes visible on portal:", px)
        await page.evaluate("document.documentElement.style.fontSize=''")
        # grey-rock on then CB wording
        await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1200)
        D = '[data-testid="biff-coach-drawer"]'
        on = page.locator(f'{D} [data-testid="grey-rock-toggle-on-btn"]')
        if await on.count(): await on.click(); await page.wait_for_timeout(800)
        hist = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('h3')].map(h => h.textContent.trim())", D)
        ok(any(h == "History of Successes & Failures" for h in hist), f"drawer h3s (textContent): {hist}")
        chip = await page.evaluate("() => { const c = document.querySelector('[data-testid=biff-greyrock-chip]'); return c && [c.textContent.trim(), c.getAttribute('title'), c.getAttribute('aria-label')]; }")
        ok(chip and chip[0] == "Grey-rock tone on" and not chip[1], f"chip textContent/title/aria-label: {chip}")
        await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
        await page.click('[data-testid="door-comm"]'); await page.wait_for_timeout(2500)
        CB = '[data-testid="comm-builder-page"]'
        print("CB grey-rock state chips:", await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('[data-testid*=grey], [data-testid*=greyrock]')].map(e => e.getAttribute('data-testid') + ':' + e.textContent.trim().slice(0,50))", CB))
        hits = await bad_words(page, CB)
        ok(not hits, f"CB forbidden words with grey-rock on: {hits[:6]}")
        await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
        # restore
        await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1200)
        off = page.locator(f'{D} [data-testid="grey-rock-toggle-off-btn"]')
        if await off.count(): await off.click(); await page.wait_for_timeout(600)
        await b.close()

asyncio.run(main())
