"""Text-node overflow scan (catches unbreakable words spilling out of boxes). Usage: python a11y_textnode_scan142.py <email> <pw>"""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE

JS = """(root) => { const R = root ? document.querySelector(root) : document.body; const vw = document.documentElement.clientWidth; const out = [];
 const w = document.createTreeWalker(R, NodeFilter.SHOW_TEXT); let n;
 while ((n = w.nextNode())) { if (!n.textContent.trim()) continue; const p = n.parentElement; if (!p || p.closest('script,style,[aria-hidden=true]')) continue;
   const rg = document.createRange(); rg.selectNodeContents(n); const b = rg.getBoundingClientRect(); if (!b.width) continue;
   let box = p; while (box && getComputedStyle(box).display === 'inline') box = box.parentElement; const pb = box.getBoundingClientRect();
   if (b.right > vw + 1 || b.right > pb.right + 2) out.push(`'${n.textContent.trim().slice(0,28)}' r=${Math.round(b.right)} box_r=${Math.round(pb.right)} vw=${vw} in=${box.getAttribute('data-testid') || box.className.toString().slice(0,40)}`); }
 return out.slice(0, 12); }"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        await ctx.request.post(BASE + "/api/auth/login", data={"email": sys.argv[1], "password": sys.argv[2]})
        page = await ctx.new_page()
        await page.add_init_script("localStorage.setItem('sac_ai_notice_ack','1')")
        await page.goto(BASE + "/"); await page.wait_for_timeout(4000)
        await page.evaluate("document.querySelectorAll('[data-sonner-toast]').forEach(t => t.remove())")
        for w, fs in ((390, "200%"), (320, "")):
            await page.set_viewport_size({"width": w, "height": 844}); await page.evaluate(f"document.documentElement.style.fontSize='{fs}'"); await page.wait_for_timeout(700)
            print(f"HOME {w}@{fs or '100%'} sw={await page.evaluate('document.documentElement.scrollWidth')}:")
            for o in await page.evaluate(JS, None): print("   ", o)
        await page.set_viewport_size({"width": 390, "height": 844}); await page.evaluate("document.documentElement.style.fontSize=''")
        await page.click('[data-testid="door-comm"]'); await page.wait_for_timeout(2500)
        for w, fs in ((390, "200%"), (320, "")):
            await page.set_viewport_size({"width": w, "height": 844}); await page.evaluate(f"document.documentElement.style.fontSize='{fs}'"); await page.wait_for_timeout(700)
            print(f"CB {w}@{fs or '100%'}:")
            for o in await page.evaluate(JS, '[data-testid=comm-builder-page]'): print("   ", o)
        await page.set_viewport_size({"width": 390, "height": 844}); await page.evaluate("document.documentElement.style.fontSize='200%'"); await page.wait_for_timeout(500)
        await page.evaluate("document.querySelector('[data-testid=comm-builder-page]').scrollTo(0,0)")
        await page.screenshot(path="/app/tests/i142_cb_390_200_top.jpeg", quality=40, type="jpeg")
        await b.close()

asyncio.run(main())
