"""Iter142 retest of iteration_141 items: CB/register/portal reflow at 320 & 390@200%, nav/crisis/sonner, focus return, axe contrast.
Usage: python a11y_retest142.py <parent_email> <parent_password> [mobile|desktop]"""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, FOCUS_JS
from a11y_retest141 import ok, ax, RECT

CUL = """(root) => { const R = root ? document.querySelector(root) : document.body; const vw = document.documentElement.clientWidth; if (!R) return ['NO ROOT'];
 return [...R.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > vw + 1 || r.left < -1); })
 .filter(e => ![...e.children].some(c => { const r = c.getBoundingClientRect(); return r.width > 0 && (r.right > vw + 1 || r.left < -1); })).slice(0, 6)
 .map(e => `${e.tagName.toLowerCase()}[${e.getAttribute('data-testid') || e.className.toString().slice(0,50)}] '${(e.textContent||'').trim().slice(0,22)}' l=${Math.round(e.getBoundingClientRect().left)} r=${Math.round(e.getBoundingClientRect().right)} vw=${vw}`); }"""
SW = "(s) => { const d = document.documentElement; const e = s ? document.querySelector(s) : null; return {doc: [d.scrollWidth, d.clientWidth, innerWidth], el: e ? [e.scrollWidth, e.clientWidth] : null}; }"
CLIP = """() => [...document.querySelectorAll('[data-testid=bottom-nav] button, [data-testid=bottom-nav] span')].filter(e => e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().right > document.documentElement.clientWidth + 1).map(e => (e.getAttribute('data-testid')||e.textContent.trim()) + ' sw=' + e.scrollWidth + ' cw=' + e.clientWidth + ' r=' + Math.round(e.getBoundingClientRect().right))"""
BRAND = """(root) => { const R = document.querySelector(root); const el = [...R.querySelectorAll('*')].find(e => e.children.length === 0 && /SA\\s*Co\\s*Parents/i.test(e.textContent) ) || [...R.querySelectorAll('*')].find(e => /^SA\\s*CoParents$/i.test(e.textContent.trim())); if (!el) return null; const r = el.getBoundingClientRect(); const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.3; return {txt: el.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height), lines: Math.round(r.height / lh), fs: getComputedStyle(el).fontSize}; }"""

SIZES = (("390@200%", 390, "200%"), ("320@100%", 320, ""), ("320@200%", 320, "200%"), ("195@100% (info)", 195, ""))


async def setsize(page, w, fs):
    await page.set_viewport_size({"width": w, "height": 844})
    await page.evaluate(f"document.documentElement.style.fontSize='{fs}'")
    await page.wait_for_timeout(800)


async def main():
    email, pw = sys.argv[1], sys.argv[2]
    mobile = (sys.argv[3] if len(sys.argv) > 3 else "mobile") == "mobile"
    print("MODE mobile=", mobile)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ---------- guest: register + login ----------
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=mobile, has_touch=mobile)
        page = await ctx.new_page()
        await page.goto(BASE + "/register"); await page.wait_for_timeout(2500)
        for label, w, fs in SIZES:
            await setsize(page, w, fs)
            s = await page.evaluate(SW, None); c = await page.evaluate(CUL, None)
            info = "INFO " if "info" in label else ""
            print(f"{info}/register {label}: doc={s['doc']} culprits={c}") if info else ok(s["doc"][0] <= s["doc"][1] + 1 and not c, f"/register {label}: doc={s['doc']} culprits={c}")
        await setsize(page, 390, "")
        await ax(page, "/register")
        await page.goto(BASE + "/login"); await page.wait_for_timeout(2500)
        await page.click('[data-testid="login-show-email-toggle"]'); await page.wait_for_timeout(600)
        for t in ("login-hide-email-toggle", "login-forgot-password-link"):
            r = await page.evaluate(RECT, f'[data-testid="{t}"]')
            ok(r and r["h"] >= 24 and r["w"] >= 24, f"{t} target size {r}")
        await ax(page, "/login (email form open)")
        for label, w, fs in SIZES[:3]:
            await setsize(page, w, fs)
            s = await page.evaluate(SW, None); ok(s["doc"][0] <= s["doc"][1] + 1, f"/login {label} doc={s['doc']} culprits={await page.evaluate(CUL, None)}")
        await ctx.close()

        # ---------- parent ----------
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=mobile, has_touch=mobile)
        await ctx.request.post(BASE + "/api/auth/login", data={"email": email, "password": pw})
        page = await ctx.new_page()
        await page.add_init_script("localStorage.setItem('sac_ai_notice_ack','1')")
        await page.goto(BASE + "/"); await page.wait_for_timeout(4000)
        for label, w, fs in SIZES:
            await setsize(page, w, fs)
            s = await page.evaluate(SW, None); c = await page.evaluate(CUL, None); cl = await page.evaluate(CLIP)
            toasts = await page.evaluate("() => [...document.querySelectorAll('[data-sonner-toast]')].map(t => { const r = t.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })")
            msg = f"portal home {label}: doc={s['doc']} culprits={c} navclip={cl} toasts={toasts}"
            if "info" in label: print("INFO", msg)
            else: ok(s["doc"][0] <= s["doc"][1] + 1 and not c and not cl, msg)
            if label == "390@200%":
                await page.screenshot(path="/app/tests/i142_home_390_200.jpeg", quality=40, type="jpeg")
        await setsize(page, 390, "")
        chip = await page.evaluate("() => [...document.querySelectorAll('*')].filter(e => e.children.length===0 && /Tool for either path/i.test(e.textContent)).map(e => e.className.toString().match(/text-\\[[^\\]]+\\]/) + ' fs=' + getComputedStyle(e).fontSize)")
        print("'Tool for either path' chip:", chip)
        # ---------- BIFF drawer: suggestion + axe + legacy tag ----------
        await page.locator('[data-testid="nav-biff"]').focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(1500)
        D = '[data-testid="biff-coach-drawer"]'
        tags = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('*')].filter(e => e.children.length===0 && /^(ADVOCATE|NOTE)$/i.test(e.textContent.trim())).map(e => e.textContent.trim())", D)
        print("legacy milestone tags in drawer:", tags)
        ok(not any(t.upper() == "ADVOCATE" for t in tags), "no ADVOCATE tag in drawer")
        await ax(page, "BIFF drawer (initial)")
        ta = page.locator(f'{D} textarea').first
        await ta.fill("You are always late picking up the kids and you never tell me anything. This is ridiculous and I am sick of it.")
        btns = await page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('button[data-testid]')].filter(e => e.getBoundingClientRect().height>0).map(e => e.getAttribute('data-testid'))", D)
        print("drawer buttons:", btns)
        cand = [t for t in btns if t == "biff-suggest-btn"]
        if cand:
            await page.click(f'[data-testid="{cand[0]}"]'); print("clicked", cand[0])
            await page.wait_for_timeout(15000)
        await ax(page, "BIFF drawer (after suggestion)")
        txt = await page.locator(D).inner_text(); print("drawer has 'no friction cues':", "no friction cues" in txt.lower())
        await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
        f = await page.evaluate(FOCUS_JS); ok("nav-biff" in f["el"] and await page.locator(D).count() == 0, f"BIFF Esc focus return: {f}")
        # ---------- CB overlay ----------
        CB = '[data-testid="comm-builder-page"]'
        await page.locator('[data-testid="door-comm"]').focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
        ok(await page.locator(CB).count() == 1, "CB opened via keyboard")
        await ax(page, "CB overlay")
        for label, w, fs in SIZES:
            await setsize(page, w, fs)
            await page.evaluate("(s) => document.querySelector(s).scrollTo(0,0)", CB)
            qe = await page.evaluate(RECT, '[data-testid="cb-quick-exit"]'); s = await page.evaluate(SW, CB)
            c = await page.evaluate(CUL, CB); br = await page.evaluate(BRAND, CB)
            pill = await page.evaluate("() => { const d = document.querySelector('[data-testid=cb-draft-card]'); if (!d) return 'no draft card'; const vw = document.documentElement.clientWidth; const dr = d.getBoundingClientRect(); return [...d.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width>0 && (r.right > Math.min(dr.right, vw) + 1); }).map(e => e.textContent.trim().slice(0,20) + ' r=' + Math.round(e.getBoundingClientRect().right) + ' card_r=' + Math.round(dr.right)).slice(0,4); }")
            vw = s["doc"][1]
            cond = qe and qe["l"] >= 0 and qe["r"] <= vw and s["el"][0] <= s["el"][1] + 1 and not c and (br is None or br["w"] > 60) and (isinstance(pill, str) or not pill)
            msg = f"CB {label}: quick-exit={qe} cbScroll={s['el']} doc={s['doc']} culprits={c} brand={br} draftOverflow={pill}"
            if "info" in label: print("INFO", msg)
            else: ok(cond, msg)
            await page.screenshot(path=f"/app/tests/i142_cb_{w}_{fs or '100'}.jpeg".replace('%', ''), quality=40, type="jpeg")
        await setsize(page, 390, "")
        await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
        f = await page.evaluate(FOCUS_JS); ok("door-comm" in f["el"] and await page.locator(CB).count() == 0, f"CB Esc focus return: {f}")
        # ---------- guided modal ----------
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        await page.click('[data-testid="door-court"]'); await page.wait_for_timeout(2000)
        await page.click('[data-testid="court-more-tools-toggle"]'); await page.wait_for_timeout(1200)
        el = page.locator('[data-testid="court-module-foundation"]')
        await el.scroll_into_view_if_needed(); await el.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2500)
        G = '[data-testid="modal-guided-foundation"]'
        ok(await page.locator(G).count() == 1, "modal-guided-foundation opened via Enter")
        disc = await page.evaluate(RECT, '[data-testid="guided-resume-discard"]'); print("guided-resume-discard:", disc)
        await ax(page, "guided modal")
        await page.keyboard.press("Escape"); await page.wait_for_timeout(1000)
        f = await page.evaluate(FOCUS_JS); ok("court-module-foundation" in f["el"] and await page.locator(G).count() == 0, f"guided Esc focus return: {f}")
        await b.close()

asyncio.run(main())
