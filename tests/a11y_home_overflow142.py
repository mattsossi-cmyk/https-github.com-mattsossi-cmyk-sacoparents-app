"""Find what forces document scrollWidth on portal home at 200% root font. Usage: python a11y_home_overflow142.py <email> <pw>"""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE

JS = """() => { const vw = document.documentElement.clientWidth; const out = [];
 for (const e of document.querySelectorAll('body *')) { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
   if (r.right > vw + 1 || e.scrollWidth > e.clientWidth + 1 && cs.overflowX === 'visible' && e.clientWidth > 0) {
     out.push(`${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.id || e.className.toString().slice(0,45)}] pos=${cs.position} disp=${cs.display} vis=${cs.visibility} op=${cs.opacity} w=${Math.round(r.width)} h=${Math.round(r.height)} l=${Math.round(r.left)} r=${Math.round(r.right)} sw=${e.scrollWidth} cw=${e.clientWidth} '${(e.textContent||'').trim().slice(0,25)}'`); } }
 return [vw, document.documentElement.scrollWidth, out.slice(0, 25)]; }"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 320, "height": 844})
        await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
        page = await ctx.new_page()
        await page.add_init_script("localStorage.setItem('sac_ai_notice_ack','1')")
        await page.goto(BASE + "/"); await page.wait_for_timeout(4000)
        await page.evaluate("document.documentElement.style.fontSize='200%'"); await page.wait_for_timeout(800)
        vw, sw, out = await page.evaluate(JS)
        print("vw", vw, "docSW", sw)
        for o in out: print("  ", o)
        await page.screenshot(path="/app/tests/i142_home_320_200.jpeg", quality=40, type="jpeg")
        deep = await page.evaluate("""() => { const vw = document.documentElement.clientWidth; return [...document.querySelectorAll('[data-testid=door-landing] *, header *')].filter(e => e.scrollWidth > e.clientWidth + 1 && e.clientWidth > 0 && ![...e.children].some(c => c.scrollWidth > c.clientWidth + 1 && c.clientWidth > 0)).slice(0, 15).map(e => { const cs = getComputedStyle(e); return `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,60)}] ox=${cs.overflowX} ws=${cs.whiteSpace} sw=${e.scrollWidth} cw=${e.clientWidth} '${(e.textContent||'').trim().slice(0,30)}'`; }); }""")
        print("leaf overflow in door-landing/header:")
        for d in deep: print("  ", d)
        hdr = await page.evaluate("() => [...document.querySelectorAll('*')].filter(e => e.children.length===0 && /^SA ?CoParents$|sacoparentsapp/i.test(e.textContent.trim())).map(e => { const r = e.getBoundingClientRect(); return e.textContent.trim() + ' w=' + Math.round(r.width) + ' h=' + Math.round(r.height) + ' l=' + Math.round(r.left) + ' vis=' + getComputedStyle(e).visibility; })")
        print("brand nodes:", hdr)
        await page.set_viewport_size({"width": 390, "height": 844}); await page.wait_for_timeout(600)
        await page.evaluate("document.querySelectorAll('[data-sonner-toast]').forEach(t => t.remove())")
        await page.screenshot(path="/app/tests/i142_home_390_200_nav.jpeg", quality=40, type="jpeg")
        await page.set_viewport_size({"width": 320, "height": 844}); await page.wait_for_timeout(600)
        await page.locator('[data-testid="door-comm"]').scroll_into_view_if_needed(); await page.wait_for_timeout(400)
        kids = await page.evaluate("() => { const d = document.querySelector('[data-testid=door-comm]'); const out=[]; const w = document.createTreeWalker(d, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect(); if (b.right > d.getBoundingClientRect().right + 1) out.push(n.textContent.trim().slice(0,30) + ' r=' + Math.round(b.right) + ' parent=' + n.parentElement.className.toString().slice(0,60)); } return out.slice(0,8); }")
        print("door-comm overflowing text nodes:", kids)
        await page.screenshot(path="/app/tests/i142_doorcomm_320_200.jpeg", quality=40, type="jpeg")
        await b.close()

asyncio.run(main())
