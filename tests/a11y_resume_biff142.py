"""Guided resume-discard button + BIFF suggestion contrast. Usage: python a11y_resume_biff142.py <email> <pw>"""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE
from a11y_retest141 import ax, RECT, ok

COLOR = "(s) => { const e = document.querySelector(s); if (!e) return null; const cs = getComputedStyle(e); return [cs.color, cs.backgroundColor, cs.fontSize, Math.round(e.getBoundingClientRect().height), e.textContent.trim().slice(0,40)]; }"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
        page = await ctx.new_page()
        await page.add_init_script("localStorage.setItem('sac_ai_notice_ack','1')")
        await page.goto(BASE + "/"); await page.wait_for_timeout(4000)
        # BIFF suggestion
        await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1500)
        D = '[data-testid="biff-coach-drawer"]'
        await page.locator(f'{D} textarea').first.fill("Hi, can we swap the Saturday pickup to 10am this week? Thanks.")
        await page.click('[data-testid="biff-suggest-btn"]')
        for _ in range(20):
            await page.wait_for_timeout(1500)
            t = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('[data-testid]')].map(e => e.getAttribute('data-testid')).filter(t => /suggest|result|rewrite|friction|cue/i.test(t))", D)
            if any(x not in ("biff-suggest-btn",) for x in t): break
        print("suggestion-related testids:", t)
        nf = await page.evaluate("(s) => { const e = [...document.querySelector(s).querySelectorAll('*')].find(e => e.children.length===0 && /no friction cues/i.test(e.textContent)); return e && [e.textContent.trim().slice(0,60), getComputedStyle(e).color]; }", D)
        print("'no friction cues' node:", nf)
        await ax(page, "BIFF drawer with suggestion")
        await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
        # guided resume
        async def open_guided():
            await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
            vis = await page.evaluate("() => [...document.querySelectorAll('[data-testid]')].filter(e=>e.getBoundingClientRect().height>0).map(e=>e.getAttribute('data-testid'))")
            print("after goto visible:", [v for v in vis if 'court' in v or 'guided' in v or 'door' in v][:15])
            if await page.locator('[data-testid^="guided-resume-discard"]').count(): return
            if not await page.locator('[data-testid="door-court"]').is_visible():
                mt = page.locator('[data-testid="court-module-foundation"]')
                if await mt.count() and await mt.is_visible():
                    await mt.click(); await page.wait_for_timeout(2500); return
                if not await page.locator('[data-testid="court-more-tools-toggle"]').is_visible():
                    await page.click('[data-testid="nav-doors"]', force=True); await page.wait_for_timeout(1500)
                else:
                    await page.click('[data-testid="court-more-tools-toggle"]'); await page.wait_for_timeout(1200)
                    await page.click('[data-testid="court-module-foundation"]'); await page.wait_for_timeout(2500); return
            if not await page.locator('[data-testid="door-court"]').count():
                print("view:", await page.evaluate("() => [...document.querySelectorAll('[data-testid]')].filter(e=>e.getBoundingClientRect().height>0).map(e=>e.getAttribute('data-testid')).slice(0,25)"))
            await page.click('[data-testid="door-court"]'); await page.wait_for_timeout(2000)
            await page.click('[data-testid="court-more-tools-toggle"]'); await page.wait_for_timeout(1200)
            await page.click('[data-testid="court-module-foundation"]'); await page.wait_for_timeout(2500)
        await open_guided()
        G = '[data-testid="modal-guided-foundation"]'
        if await page.locator('[data-testid^="guided-resume-discard"]').count() == 0:
            btns = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('button[data-testid], textarea, input')].map(e => e.getAttribute('data-testid') || e.tagName)", G)
            print("guided controls:", btns[:20])
            start = [x for x in btns if x and any(k in x for k in ("start", "begin"))]
            if start:
                await page.click(f'{G} [data-testid="{start[0]}"]'); await page.wait_for_timeout(1200)
            ta = page.locator(f'{G} [data-testid="guided-input-foundation"]')
            if await ta.count():
                await ta.fill("TEST_resume draft text"); await page.wait_for_timeout(800)
            ch = page.locator(f'{G} [role=radio], {G} input[type=radio], {G} [data-testid*=option]').first
            if await ch.count():
                await ch.click(force=True); await page.wait_for_timeout(800)
            nx = ["guided-send-foundation"]
            if nx:
                await page.click(f'{G} [data-testid="{nx[0]}"]', force=True); await page.wait_for_timeout(9000)
            await page.keyboard.press("Escape"); await page.wait_for_timeout(1000)
            await open_guided()
        r = await page.evaluate(COLOR, '[data-testid^="guided-resume-discard"]')
        print("guided-resume-discard [color,bg,fs,h,text]:", r)
        if r:
            ok(r[3] >= 24, f"discard height >=24: {r[3]}")
            await ax(page, "guided modal with resume prompt")
        await b.close()

asyncio.run(main())
