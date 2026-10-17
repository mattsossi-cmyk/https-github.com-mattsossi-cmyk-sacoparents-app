import asyncio, sys
from playwright.async_api import async_playwright

BASE = sys.argv[1]
SW = "() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, off: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > innerWidth + 1 && !e.closest('[class*=overflow-x-auto],[class*=overflow-auto],pre'); }).filter(e => { return true; }).slice(0, 10).map(e => (e.dataset.testid || e.tagName + '.' + String(e.className).slice(0, 50)) + ':' + Math.round(e.getBoundingClientRect().right))})"


async def ctx_for(b, width, cred=None):
    ctx = await b.new_context(viewport={"width": width, "height": 844}, is_mobile=True, has_touch=True)
    await ctx.add_init_script("try{localStorage.setItem('sac_ai_notice_ack','1')}catch(e){}")
    if cred:
        await ctx.request.post(BASE + "/api/auth/login", data={"email": cred[0], "password": cred[1]})
    return ctx


async def probe(b, width, big, path, action=None, cred=("parent1@test.com", "TestPass123!")):
    ctx = await ctx_for(b, width, cred)
    pg = await ctx.new_page()
    await pg.goto(BASE + path, wait_until="domcontentloaded")
    await pg.wait_for_timeout(3000)
    if big:
        await pg.evaluate("document.documentElement.style.fontSize = '200%'")
    if action:
        await action(pg)
    await pg.wait_for_timeout(600)
    res = await pg.evaluate(SW)
    if action:
        qe = await pg.query_selector("[data-testid=cb-quick-exit]")
        if qe:
            r = await qe.bounding_box()
            res["quick_exit_right"] = round(r["x"] + r["width"]) if r else None
    print(path, width, "200%" if big else "100%", res, flush=True)
    await ctx.close()


async def open_cb(pg):
    await pg.click("[data-testid=door-comm]")
    await pg.wait_for_selector("[data-testid=comm-builder-page]")


async def guided_focus(b):
    ctx = await ctx_for(b, 390, ("parent1@test.com", "TestPass123!"))
    pg = await ctx.new_page()
    await pg.goto(BASE + "/", wait_until="domcontentloaded")
    await pg.wait_for_timeout(3000)
    try:
        await pg.click("[data-testid=door-court]")
        await pg.wait_for_timeout(800)
        t = await pg.query_selector("[data-testid=court-more-tools-toggle]")
        if t:
            await t.click()
            await pg.wait_for_timeout(500)
        await pg.focus("[data-testid=court-module-foundation]")
        await pg.keyboard.press("Enter")
        await pg.wait_for_selector("[data-testid^=modal-guided-]", timeout=5000)
        await pg.wait_for_timeout(500)
        print("in modal:", await pg.evaluate("() => document.activeElement.dataset.testid || document.activeElement.tagName + '.' + document.activeElement.getAttribute('role')"))
        await pg.keyboard.press("Escape")
        for t in (30, 200, 800):
            await pg.wait_for_timeout(t)
            print(t, "guided focus after Esc:", await pg.evaluate("() => [document.activeElement.dataset.testid || document.activeElement.tagName, !!document.querySelector('[data-testid^=modal-guided-]'), document.querySelector('[data-testid=court-page]')?.className.includes(' hidden ')]"), flush=True)
    except Exception as e:
        print("guided probe error", str(e)[:200])
    await ctx.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, big in ((390, True), (320, False)):
            await probe(b, w, big, "/", open_cb)
            await probe(b, w, big, "/")
            await probe(b, w, big, "/register", cred=None)
        await guided_focus(b)
        await b.close()

asyncio.run(main())
