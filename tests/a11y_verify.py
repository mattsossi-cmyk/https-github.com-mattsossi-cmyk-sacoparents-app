"""Independent mobile a11y verification (390x844): axe on key screens incl. open dialogs, keyboard, 200% text, semantics.
Usage: python a11y_verify.py <parent_email> <parent_password> <out.json>"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL")][0].rstrip("/")
AXE = open("/app/frontend/node_modules/axe-core/axe.min.js").read()
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
AXE_JS = """(a) => axe.run(a.ctx || document, {runOnly: {type: 'tag', values: a.tags}}).then(r => r.violations.map(v => ({
  id: v.id, impact: v.impact, n: v.nodes.length,
  nodes: v.nodes.slice(0, 8).map(x => ({t: x.target.join(' ').slice(-110), html: x.html.slice(0, 140)}))})))"""
SEM_JS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const small = [...document.querySelectorAll('button, a[href], input:not([type=hidden]), select, [role=button], [role=checkbox], [role=switch]')]
    .filter(vis).filter(e => { const r = e.getBoundingClientRect(); if (e.tagName === 'A' && getComputedStyle(e).display === 'inline') return false; return r.height < 24 || r.width < 24; })
    .map(e => { const r = e.getBoundingClientRect(); return `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || (e.textContent||'').trim().slice(0,25)}] ${Math.round(r.width)}x${Math.round(r.height)}`; });
  return {lang: document.documentElement.lang, h1: [...document.querySelectorAll('h1')].filter(vis).length,
    main: document.querySelectorAll('main, [role=main]').length, title: document.title,
    dialogs: [...document.querySelectorAll('[role=dialog],[role=alertdialog]')].length, small: small.slice(0, 15), small_n: small.length};
}"""
OVER_JS = """() => { const d = document.documentElement; const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > innerWidth + 2 && r.width > 0 && getComputedStyle(e).position !== 'fixed'; })
  .filter(e => !e.closest('[class*=overflow-x-auto],[class*=overflow-auto]'))
  .filter(e => ![...e.children].some(c => c.getBoundingClientRect().right > innerWidth + 2))
  .slice(0, 6).map(e => `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,40)}] r=${Math.round(e.getBoundingClientRect().right)}`);
  return {sw: d.scrollWidth, cw: d.clientWidth, overflow: d.scrollWidth > d.clientWidth + 1, wide}; }"""
FOCUS_JS = """() => { const e = document.activeElement; if (!e || e === document.body) return {el: 'BODY'}; const s = getComputedStyle(e);
  const vis = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || (s.boxShadow && s.boxShadow !== 'none');
  const name = e.getAttribute('aria-label') || (e.textContent || '').trim().slice(0, 30) || e.getAttribute('placeholder') || '';
  return {el: `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || name}]`, visible_focus: vis, inDialog: !!e.closest('[role=dialog],[data-testid*=drawer],[data-testid^=modal-]')}; }"""
results = []


async def axe(page, label, ctx=None):
    await page.add_script_tag(content=AXE)
    v = await page.evaluate(AXE_JS, {"ctx": ctx, "tags": TAGS})
    sem = await page.evaluate(SEM_JS)
    ov = await page.evaluate(OVER_JS)
    r = {"label": label, "url": page.url.replace(BASE, ""), "violations": v, "sem": sem, "overflow": ov}
    results.append(r)
    print(f"\n== {label} {r['url']} axe={[(x['id'], x['n']) for x in v]} h1={sem['h1']} main={sem['main']} lang={sem['lang']} dialogs={sem['dialogs']} overflow={ov['overflow']} small={sem['small_n']}", flush=True)
    for x in v:
        for n in x["nodes"][:4]:
            print(f"   {x['id']}: {n['t']} :: {n['html'][:100]}")
    if sem["small"]:
        print("   small targets:", sem["small"][:8])
    return r


async def text200(page, label):
    await page.evaluate("document.documentElement.style.fontSize='200%'")
    await page.wait_for_timeout(500)
    ov = await page.evaluate(OVER_JS)
    await page.evaluate("document.documentElement.style.fontSize=''")
    # browser-zoom equivalent: 390 device at 200% zoom = 195 CSS px; use WCAG reflow width 320 too
    vs = page.viewport_size
    out = {"root200": ov}
    for w in (320, 195):
        await page.set_viewport_size({"width": w, "height": 844})
        await page.wait_for_timeout(500)
        out[f"w{w}"] = await page.evaluate(OVER_JS)
    await page.set_viewport_size(vs)
    print(f"   [200%] {label}: root200 overflow={out['root200']['overflow']} {out['root200']['wide'][:3]} | 320px={out['w320']['overflow']} {out['w320']['wide'][:3]} | 195px(zoom200)={out['w195']['overflow']} {out['w195']['wide'][:3]}")
    results.append({"label": label + " text200", **out})


async def tabwalk(page, label, n=25):
    seq = []
    for _ in range(n):
        await page.keyboard.press("Tab")
        seq.append(await page.evaluate(FOCUS_JS))
    no_vis = [s["el"] for s in seq if s.get("el") != "BODY" and not s.get("visible_focus")]
    print(f"   [kbd] {label}: order={[s['el'] for s in seq][:14]}")
    if no_vis:
        print(f"   [kbd] no visible focus: {sorted(set(no_vis))[:10]}")
    results.append({"label": label + " kbd", "seq": seq})
    return seq


async def goto(page, path, wait=2500):
    await page.goto(BASE + path, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(wait)


async def main():
    email, pw, out = sys.argv[1], sys.argv[2], sys.argv[3]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ---------- guest ----------
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        await goto(page, "/login")
        await axe(page, "login default"); await tabwalk(page, "login", 12); await text200(page, "login")
        await goto(page, "/login")
        if await page.locator('[data-testid="login-show-email-toggle"]').count():
            await page.click('[data-testid="login-show-email-toggle"]'); await page.wait_for_timeout(500)
        await page.fill('[data-testid="login-email-input"]', "nobody@example.com")
        await page.fill('[data-testid="login-password-input"]', "wrongpass1")
        await page.click('[data-testid="login-submit-button"]'); await page.wait_for_timeout(2500)
        alerts = await page.evaluate("() => [...document.querySelectorAll('[role=alert],[aria-live]')].map(e => e.getAttribute('role')+':'+(e.textContent||'').trim().slice(0,60))")
        inv = await page.evaluate("() => [...document.querySelectorAll('input')].map(e => `${e.getAttribute('data-testid')} invalid=${e.getAttribute('aria-invalid')} describedby=${e.getAttribute('aria-describedby')}`)")
        print("   login error live regions:", alerts, inv)
        await axe(page, "login with error")
        await goto(page, "/register")
        await axe(page, "register default"); await tabwalk(page, "register", 15); await text200(page, "register")
        subm = page.locator('form button[type=submit]').first
        print("   register submit disabled before input:", await subm.is_disabled())
        await page.fill('[data-testid="register-email-input"]', "bad-email"); await page.fill('[data-testid="register-password-input"]', "x")
        await page.locator('[data-testid="register-name-input"]').focus(); await page.wait_for_timeout(800)
        alerts = await page.evaluate("() => [...document.querySelectorAll('[role=alert],[aria-live]')].map(e => e.getAttribute('role')+':'+(e.textContent||'').trim().slice(0,60))")
        inv = await page.evaluate("() => [...document.querySelectorAll('input')].map(e => `${e.getAttribute('data-testid')||e.name} req=${e.required} invalid=${e.getAttribute('aria-invalid')} describedby=${e.getAttribute('aria-describedby')} valmsg=${e.validationMessage.slice(0,30)}`)")
        print("   register empty-submit live regions:", alerts, inv)
        await axe(page, "register with validation")
        await goto(page, "/help")
        await axe(page, "help guest"); await tabwalk(page, "help", 12); await text200(page, "help")
        await goto(page, "/calendar")
        await axe(page, "calendar"); await tabwalk(page, "calendar", 10); await text200(page, "calendar")
        # guest portal: BIFF -> consent/AI modal
        await goto(page, "/", 3500)
        await axe(page, "portal guest home")
        try:
            await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1200)
            ta = page.locator('[data-testid="biff-coach-drawer"] textarea').first
            await ta.fill("Pick up is at 5 today please confirm."); await page.wait_for_timeout(300)
            await page.click('[data-testid="biff-suggest-btn"]'); await page.wait_for_timeout(3500)
            sem = await page.evaluate(SEM_JS)
            print("   guest BIFF suggest -> dialogs:", sem["dialogs"], await page.evaluate("() => [...document.querySelectorAll('[role=dialog]')].map(d => d.getAttribute('data-testid'))"))
            await axe(page, "guest consent/AI modal open")
            await tabwalk(page, "guest consent modal", 8)
        except Exception as e:
            print("   guest modal ERR", str(e)[:150])
        await ctx.close()
        # ---------- parent ----------
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        r = await ctx.request.post(BASE + "/api/auth/login", data={"email": email, "password": pw})
        print("\nparent login", r.status)
        page = await ctx.new_page()
        await goto(page, "/", 3500)
        await axe(page, "portal parent home"); await tabwalk(page, "portal home", 15); await text200(page, "portal home")
        for path in ("/case-settings", "/plan-options", "/help"):
            await goto(page, path)
            await axe(page, "parent " + path); await tabwalk(page, path, 12); await text200(page, path)
        # BIFF drawer open
        await goto(page, "/", 3500)
        try:
            await page.click('[data-testid="nav-biff"]'); await page.wait_for_timeout(1200)
            await axe(page, "BIFF drawer open")
            seq = await tabwalk(page, "BIFF drawer", 10)
            print("   focus left drawer during tab:", [s["el"] for s in seq if not s.get("inDialog")][:6])
            await page.locator('[data-testid="biff-coach-drawer"] textarea').first.fill("Can we swap Saturday for Sunday this week?")
            await page.click('[data-testid="biff-suggest-btn"]'); await page.wait_for_timeout(2500)
            d = await page.evaluate("() => [...document.querySelectorAll('[role=dialog],[role=alertdialog]')].map(d => d.getAttribute('data-testid'))")
            print("   AI notice dialogs:", d)
            if d:
                await axe(page, "AI notice modal open")
                await tabwalk(page, "AI notice modal", 6)
                await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
                print("   after Esc dialogs:", await page.evaluate("() => document.querySelectorAll('[role=dialog]').length"), "focus:", await page.evaluate(FOCUS_JS))
            await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
            print("   BIFF drawer after Esc:", await page.locator('[data-testid="biff-coach-drawer"]').count(), "focus:", await page.evaluate(FOCUS_JS))
        except Exception as e:
            print("   BIFF ERR", str(e)[:200])
        # Communication builder
        try:
            await goto(page, "/", 3500)
            await page.get_by_text("Communication Builder", exact=True).first.click(); await page.wait_for_timeout(2000)
            await axe(page, "communication builder open"); await text200(page, "communication builder")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
            print("   CB after Esc:", await page.locator('[data-testid="comm-builder-page"]').count())
        except Exception as e:
            print("   CB ERR", str(e)[:200])
        # Guided journey modal
        try:
            await goto(page, "/", 3500)
            await page.get_by_text("Self Journey", exact=True).first.click(); await page.wait_for_timeout(2000)
            g = page.locator('[data-testid^="toolkit-guided-"]').first
            print("   guided launchers:", await page.locator('[data-testid^="toolkit-guided-"]').count())
            if await g.count():
                await g.scroll_into_view_if_needed(); await g.click(); await page.wait_for_timeout(2000)
                await axe(page, "guided journey modal open")
                seq = await tabwalk(page, "guided modal", 10)
                print("   focus left guided modal:", [s["el"] for s in seq if not s.get("inDialog")][:6])
                await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
                print("   guided after Esc:", await page.locator('[data-testid^="modal-guided-"]').count())
        except Exception as e:
            print("   GUIDED ERR", str(e)[:200])
        await ctx.close()
        await b.close()
    json.dump(results, open(out, "w"), indent=1)
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
