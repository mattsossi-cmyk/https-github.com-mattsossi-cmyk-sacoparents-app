import asyncio, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.add_init_script("try{localStorage.setItem('sac_ai_notice_ack','1')}catch(e){}")
        await ctx.request.post(BASE + "/api/auth/login", data={"email": "parent1@test.com", "password": "TestPass123!"})
        pg = await ctx.new_page()
        await pg.goto(BASE + "/", wait_until="domcontentloaded")
        await pg.wait_for_timeout(3000)
        await pg.evaluate("document.documentElement.style.fontSize = '200%'")
        await pg.wait_for_timeout(4000)
        print(await pg.evaluate("""() => {
  window.scrollTo(2000, window.scrollY); const sx = window.scrollX; const sw0 = [document.documentElement.scrollWidth, sx, getComputedStyle(document.documentElement).overflowX, getComputedStyle(document.body).overflowX];
  const over = () => document.documentElement.scrollWidth > innerWidth + 1;
  let node = document.body; const path = [];
  while (true) {
    let culprit = null;
    for (const c of node.children) { const prev = c.style.display; c.style.display = 'none'; const fixed = !over(); c.style.display = prev; if (fixed) { culprit = c; break; } }
    if (!culprit) break;
    path.push((culprit.dataset.testid || culprit.tagName + '.' + String(culprit.className).slice(0, 70)));
    node = culprit;
  }
  return [sw0, document.documentElement.scrollWidth, path.slice(-4), node.outerHTML.slice(0, 300)];
}"""))
        await b.close()
asyncio.run(main())
