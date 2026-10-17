"""Iter141 targeted retest: grey-rock wording, dialog focus/Esc, CB reflow, login/register semantics, footer, rem scaling.
Usage: python a11y_retest141.py <parent_email> <parent_password>"""
import asyncio, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, AXE, AXE_JS, TAGS, FOCUS_JS

BAD = re.compile(r"safety|coerc|advocate|flagged", re.I)
DLG = "() => [...document.querySelectorAll('[role=dialog],[role=alertdialog]')].map(d => (d.getAttribute('data-testid')||d.id||d.className.toString().slice(0,20)) + ' modal=' + d.getAttribute('aria-modal') + ' lby=' + d.getAttribute('aria-labelledby') + '->' + ((document.getElementById(d.getAttribute('aria-labelledby')||'_')||{}).textContent||'').trim().slice(0,40) + ' label=' + d.getAttribute('aria-label'))"
RECT = "(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), h: Math.round(r.height), vw: innerWidth, fs: getComputedStyle(e).fontSize}; }"
OVER = "() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, cb: (document.querySelector('[data-testid=comm-builder-page]')||{}).scrollWidth, cbw: (document.querySelector('[data-testid=comm-builder-page]')||{}).clientWidth})"
CULPRIT = """(root) => { const R = document.querySelector(root) || document.body; return [...R.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1; })
 .filter(e => ![...e.children].some(c => c.getBoundingClientRect().right > innerWidth + 1)).slice(0, 6)
 .map(e => `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,50)}] '${(e.textContent||'').trim().slice(0,25)}' r=${Math.round(e.getBoundingClientRect().right)}`); }"""


def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)


async def ax(page, label):
    await page.add_script_tag(content=AXE)
    v = await page.evaluate(AXE_JS, {"ctx": None, "tags": TAGS})
    print(f"== axe {label}: {[(x['id'], x['n']) for x in v]}")
    for x in v:
        for n in x["nodes"][:3]:
            print("    ", x["id"], n["t"], "::", n["html"][:110])


async def bad_words(page, sel):
    txt = await page.evaluate("(s) => { const e = document.querySelector(s); if (!e) return ''; const c = e.cloneNode(true); c.querySelectorAll('[data-testid*=crisis]').forEach(x => x.remove()); return c.innerText + ' ' + [...c.querySelectorAll('[title],[aria-label]')].map(x => (x.getAttribute('title')||'') + ' ' + (x.getAttribute('aria-label')||'')).join(' '); }", sel)
    hits = [txt[max(0, m.start() - 40): m.end() + 30].replace("\n", " ") for m in BAD.finditer(txt)]
    return hits


async def main():
    email, pw = sys.argv[1], sys.argv[2]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.request.post(BASE + "/api/auth/login", data={"email": email, "password": pw})
        page = await ctx.new_page()
        prompts = []
        page.on("dialog", lambda d: (prompts.append(d.message), asyncio.ensure_future(d.dismiss())))
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        await page.evaluate("localStorage.removeItem('sac_ai_notice_ack')")
        await page.reload(); await page.wait_for_timeout(3500)
        h1 = await page.evaluate("() => [...document.querySelectorAll('h1')].filter(e => e.getBoundingClientRect().height > 0).map(e => e.textContent.trim())")
        ok(h1 == ["Pick your path"], f"portal home single visible h1: {h1}")
        # ---- BIFF drawer ----
        await page.locator('[data-testid="nav-biff"]').focus()
        await page.keyboard.press("Enter"); await page.wait_for_timeout(1500)
        print("dialogs:", await page.evaluate(DLG))
        f = await page.evaluate(FOCUS_JS); ok(f.get("inDialog"), f"focus moved into drawer on open: {f}")
        seq = []
        for _ in range(35):
            await page.keyboard.press("Tab"); seq.append(await page.evaluate(FOCUS_JS))
        out = [s["el"] for s in seq if not s.get("inDialog")]
        ok(not out, f"Tab trapped in drawer (35 tabs) outside={out[:5]}")
        seq = []
        for _ in range(12):
            await page.keyboard.press("Shift+Tab"); seq.append(await page.evaluate(FOCUS_JS))
        out = [s["el"] for s in seq if not s.get("inDialog")]
        ok(not out, f"Shift+Tab trapped in drawer outside={out[:5]}")
        D = '[data-testid="biff-coach-drawer"]'
        fs0 = await page.evaluate(RECT, '[data-testid="grey-rock-toggle-chip"]')
        on = page.locator(f'{D} [data-testid="grey-rock-toggle-on-btn"]')
        if await on.count():
            await on.click(); await page.wait_for_timeout(1000)
        chip = page.locator('[data-testid="biff-greyrock-chip"]').first
        ok(await chip.count() > 0, "biff-greyrock-chip shown after grey-rock on")
        if await chip.count():
            ct = (await chip.inner_text()).strip(); tt = await chip.get_attribute("title")
            ok(ct == "Grey-rock tone on" and not tt, f"chip text='{ct}' title={tt!r}")
        dtxt = await page.locator(D).inner_text()
        ok("Grey-rock BIFF: short, factual and neutral." in dtxt, "grey-rock subtitle present")
        ok("History of Successes & Failures" in dtxt and "+ Log Milestone" in dtxt, "history card neutral heading + Log Milestone")
        ok(await page.locator('[data-testid="advocate-review-tile"]').count() == 0, "no advocate-review-tile")
        ok(await page.locator(f'{D} [data-testid="success-count"]').count() and await page.locator(f'{D} [data-testid="friction-count"]').count(), "success/friction counts present")
        hits = await bad_words(page, D)
        ok(not hits, f"forbidden words in BIFF drawer (grey-rock on): {hits[:6]}")
        print("page-level forbidden (outside crisis):", (await bad_words(page, 'body'))[:8])
        await page.locator(f'{D} [data-testid="add-milestone-btn"]').click(); await page.wait_for_timeout(800)
        ok(prompts and prompts[-1].startswith("Enter Milestone Title"), f"milestone prompt: {prompts[-1:] }")
        await ax(page, "BIFF drawer grey-rock on")
        # AI notice on top
        ta = page.locator(f'{D} textarea').first
        print("textarea readonly:", await ta.get_attribute("readonly"))
        await ta.click(force=True); await page.wait_for_timeout(1500)
        dl = await page.evaluate(DLG); print("dialogs after textarea click:", dl)
        if len(dl) >= 2:
            await ax(page, "AI notice modal over drawer")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
            dl2 = await page.evaluate(DLG)
            ok(len(dl2) == 1 and await page.locator(D).count() == 1, f"1st Esc closes only AI notice: {dl2}")
            f = await page.evaluate(FOCUS_JS); print("   focus after 1st Esc:", f)
            await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
        else:
            print("WARN AI notice did not open (maybe server-side ack)")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
        f = await page.evaluate(FOCUS_JS)
        ok(await page.locator(D).count() == 0 and "nav-biff" in f["el"], f"2nd Esc closes drawer, focus back: {f}")
        # 200% chip growth
        await page.locator('[data-testid="nav-biff"]').click(); await page.wait_for_timeout(1200)
        a = await page.evaluate(RECT, '[data-testid="biff-greyrock-chip"]')
        await page.evaluate("document.documentElement.style.fontSize='200%'"); await page.wait_for_timeout(500)
        bb = await page.evaluate(RECT, '[data-testid="biff-greyrock-chip"]')
        ok(a and bb and float(bb["fs"][:-2]) >= 1.9 * float(a["fs"][:-2]), f"biff chip font scales at 200%: {a and a['fs']} -> {bb and bb['fs']}")
        print("   drawer 200% culprits:", await page.evaluate(CULPRIT, D))
        await page.evaluate("document.documentElement.style.fontSize=''")
        # turn grey rock off again
        off = page.locator(f'{D} [data-testid="grey-rock-toggle-off-btn"]')
        if await off.count():
            await off.click(); await page.wait_for_timeout(600)
        await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
        # ---- Communication Builder ----
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        cands = await page.evaluate("() => [...document.querySelectorAll('button,a,[role=button]')].filter(e => /Communication Builder/i.test(e.textContent) && e.getBoundingClientRect().height>0).map(e => e.getAttribute('data-testid')+'|'+e.textContent.trim().slice(0,40))")
        print("CB launcher candidates:", cands[:6])
        door = page.locator('[data-testid="door-comm"]')
        await door.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
        if not await page.locator('[data-testid="comm-builder-page"]').count():
            l = page.get_by_text("Communication Builder", exact=True).first
            await l.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
        opener = await page.evaluate("() => (window.__op = null, '')")
        CB = '[data-testid="comm-builder-page"]'
        if await page.locator(CB).count():
            print("CB dialogs:", await page.evaluate(DLG))
            h = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('h1')].map(e => e.textContent.trim().slice(0,50) + ' vis=' + (e.getBoundingClientRect().height>0))", CB)
            print("CB h1s:", h, "focus:", await page.evaluate(FOCUS_JS))
            seq = []
            for _ in range(60):
                await page.keyboard.press("Tab"); seq.append(await page.evaluate("() => !!document.activeElement.closest('[data-testid=comm-builder-page]')"))
            ok(all(seq), f"Tab trapped in CB (60 tabs) out={seq.count(False)}")
            on = page.locator(f'{CB} [data-testid="grey-rock-toggle-on-btn"]')
            print("CB grey-rock toggle present:", await on.count())
            if await on.count():
                await on.first.click(); await page.wait_for_timeout(1000)
                hits = await bad_words(page, CB); ok(not hits, f"forbidden words in CB (grey-rock on): {hits[:6]}")
                ms = page.locator(f'{CB} [data-testid="add-milestone-btn"]')
                if await ms.count():
                    await ms.first.click(); await page.wait_for_timeout(600); print("CB milestone prompt:", prompts[-1:])
                off = page.locator(f'{CB} [data-testid="grey-rock-toggle-off-btn"]')
                if await off.count(): await off.first.click(); await page.wait_for_timeout(500)
            else:
                hits = await bad_words(page, CB); print("CB forbidden (grey-rock state as-is):", hits[:6])
            await ax(page, "CB overlay")
            for label, w, fs in (("390 root200", 390, "200%"), ("195px", 195, ""), ("320 root200", 320, "200%")):
                await page.set_viewport_size({"width": w, "height": 844}); await page.evaluate(f"document.documentElement.style.fontSize='{fs}'"); await page.wait_for_timeout(700)
                await page.evaluate("(s) => document.querySelector(s).scrollTo(0,0)", CB)
                qe = await page.evaluate(RECT, '[data-testid="cb-quick-exit"]')
                ov = await page.evaluate(OVER)
                cul = await page.evaluate(CULPRIT, CB)
                ok(qe and qe["l"] >= 0 and qe["r"] <= qe["vw"] and ov["sw"] <= ov["cw"] + 1 and not cul, f"CB reflow {label}: quick-exit={qe} over={ov} culprits={cul}")
                await page.screenshot(path=f"/app/tests/cb_{label.replace(' ', '_')}.jpeg", quality=40, type="jpeg")
            await page.set_viewport_size({"width": 390, "height": 844}); await page.evaluate("document.documentElement.style.fontSize=''")
            await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
            f = await page.evaluate(FOCUS_JS)
            ok(await page.locator(CB).count() == 0, f"Esc closes CB; focus -> {f}")
        else:
            print("FAIL could not open CB")
        # ---- guided modal ----
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        gl = await page.evaluate("() => [...document.querySelectorAll('[data-testid]')].map(e => e.getAttribute('data-testid')).filter(t => /guided|readiness/i.test(t)).slice(0,15)")
        print("guided-ish testids on home:", gl)
        for door in ("door-court", "door-self"):
            await page.goto(BASE + "/"); await page.wait_for_timeout(3000)
            await page.click(f'[data-testid="{door}"]'); await page.wait_for_timeout(2500)
            gl = await page.evaluate("() => [...document.querySelectorAll('[data-testid]')].filter(e => e.getBoundingClientRect().height>0).map(e => e.getAttribute('data-testid')).filter(t => /guided|readiness|conflict/i.test(t)).slice(0,15)")
            print(door, "guided-ish:", gl)
            lc = [t for t in gl if not t.startswith("modal-")]
            if lc:
                el = page.locator(f'[data-testid="{lc[0]}"]').first
                await el.scroll_into_view_if_needed(); await el.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
                print("  after launching", lc[0], "dialogs:", await page.evaluate(DLG), "modal-guided:", await page.locator('[data-testid^="modal-guided-"]').count())
                if await page.locator('[data-testid^="modal-guided-"]').count():
                    print("  focus:", await page.evaluate(FOCUS_JS))
                    seq = []
                    for _ in range(25):
                        await page.keyboard.press("Tab"); seq.append(await page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
                    ok(all(seq), f"guided Tab trapped out={seq.count(False)}")
                    await ax(page, "guided modal")
                    await page.keyboard.press("Escape"); await page.wait_for_timeout(700)
                    f = await page.evaluate(FOCUS_JS)
                    ok(await page.locator('[data-testid^="modal-guided-"]').count() == 0, f"guided Esc closes; focus -> {f} (launcher {lc[0]})")
                    break
        await ctx.close()
        # ---- guest forms / footer ----
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        for path, want in (("/login", True), ("/register", True), ("/privacy-notice", True), ("/calendar", False)):
            await page.goto(BASE + path); await page.wait_for_timeout(2500)
            n = await page.locator('[data-testid="global-footer-get-help"]').count()
            ok((n > 0) == want, f"footer Get help on {path}: {n}")
        await page.goto(BASE + "/login"); await page.wait_for_timeout(2500)
        for t in ("login-show-email-toggle", "login-magic-link-button"):
            print(t, await page.evaluate(RECT, f'[data-testid="{t}"]'))
        await page.click('[data-testid="login-show-email-toggle"]'); await page.wait_for_timeout(500)
        for t in ("login-hide-email-toggle", "login-magic-link-button", "login-forgot-password-link"):
            print(t, await page.evaluate(RECT, f'[data-testid="{t}"]'))
        lab = await page.evaluate("() => ['login-email-input','login-password-input'].map(t => { const e = document.querySelector(`[data-testid=${t}]`); return t + ':' + (e && (e.labels && e.labels.length ? e.labels[0].textContent.trim() : e.getAttribute('aria-label'))) + ' inMain=' + !!(e && e.closest('main')); })")
        print("login labels:", lab)
        await ctx.close(); await b.close()

if __name__ == "__main__":
    asyncio.run(main())
