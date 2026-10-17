"""Iter141 part 2: AI notice layering (guest), guided modal, register/login semantics, footer."""
import asyncio, sys
from playwright.async_api import async_playwright
sys.path.insert(0, "/app/tests")
from a11y_verify import BASE, FOCUS_JS
from a11y_retest141 import ok, ax, DLG, RECT


async def main():
    email, pw = sys.argv[1], sys.argv[2]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        # guest AI notice layering covered by a11y_ainotice_probe.py
        # ---- login ----
        await page.goto(BASE + "/login"); await page.wait_for_timeout(2500)
        for t in ("login-show-email-toggle", "login-magic-link-button"):
            r = await page.evaluate(RECT, f'[data-testid="{t}"]'); ok(r and r["h"] >= 24, f"{t} size {r}")
        await page.click('[data-testid="login-show-email-toggle"]'); await page.wait_for_timeout(500)
        for t in ("login-hide-email-toggle", "login-forgot-password-link", "login-submit-button"):
            r = await page.evaluate(RECT, f'[data-testid="{t}"]'); ok(r and r["h"] >= 24, f"{t} size {r}")
        lab = await page.evaluate("() => ['login-email-input','login-password-input'].map(t => { const e = document.querySelector(`[data-testid=${t}]`); return t + ':' + (e && (e.labels && e.labels.length ? e.labels[0].textContent.trim() : e.getAttribute('aria-label'))) + ' inMain=' + !!(e && e.closest('main')); })")
        print("login labels:", lab)
        await page.fill('[data-testid="login-email-input"]', email); await page.fill('[data-testid="login-password-input"]', "WrongPass999!")
        await page.click('[data-testid="login-submit-button"]'); await page.wait_for_timeout(2500)
        err = page.locator('[data-testid="login-error"]')
        ok(await err.count() and await err.get_attribute("role") == "alert", f"login-error role=alert: {await err.inner_text() if await err.count() else None}")
        print("  inputs:", await page.evaluate("() => [...document.querySelectorAll('main input')].map(e => `${e.getAttribute('data-testid')} inv=${e.getAttribute('aria-invalid')} db=${e.getAttribute('aria-describedby')}`)"))
        await ax(page, "login with error")
        # ---- register ----
        await page.goto(BASE + "/register"); await page.wait_for_timeout(2500)
        names = await page.evaluate("""() => [...document.querySelectorAll('input,select,textarea')].filter(e => e.type !== 'hidden').map(e => {
            const n = (e.labels && e.labels.length ? [...e.labels].map(l => l.textContent.trim()).join(' ') : '') || e.getAttribute('aria-label') || (e.getAttribute('aria-labelledby') ? document.getElementById(e.getAttribute('aria-labelledby'))?.textContent : '');
            return `${e.getAttribute('data-testid') || e.name}: '${(n||'').slice(0,40)}' inMain=${!!e.closest('main')}`; })""")
        for n in names: print("  ", n)
        ok(all(": ''" not in n for n in names), "all register inputs have accessible names")
        sb = page.locator('[data-testid="register-submit-button"]')
        db = await sb.get_attribute("aria-describedby"); hint = page.locator('[data-testid="register-submit-hint"]')
        ht = await hint.inner_text() if await hint.count() else None
        hid = await hint.get_attribute("id") if await hint.count() else None
        ok(await sb.is_disabled() and ht and db and hid and hid in db.split(), f"submit disabled + hint linked: db={db} hint id={hid} text={ht!r}")
        r = await page.evaluate(RECT, '[data-testid="register-add-child"]'); ok(r and r["h"] >= 24, f"register-add-child {r}")
        await page.locator('[data-testid="register-mediation-date-input"]').focus(); await page.wait_for_timeout(300)
        f = await page.evaluate("() => { const s = getComputedStyle(document.activeElement); return {o: s.outlineStyle + ' ' + s.outlineWidth + ' ' + s.outlineColor, bs: s.boxShadow.slice(0,60)}; }")
        ok("none" not in f["o"] or f["bs"] != "none", f"date focus style {f}")
        await page.fill('[data-testid="register-name-input"]', "TEST A11y")
        await page.fill('[data-testid="register-email-input"]', "test_a11y141@example.com")
        await page.fill('[data-testid="register-password-input"]', "password")
        await page.wait_for_timeout(500)
        print("  strength label:", await page.evaluate("() => [...document.querySelectorAll('[data-testid*=strength]')].map(e => e.getAttribute('data-testid') + ':' + e.textContent.trim().slice(0,40) + ' color=' + getComputedStyle(e).color)"))
        for cb in await page.locator('main input[type=checkbox]').all():
            if not await cb.is_checked(): await cb.check(force=True)
        await page.wait_for_timeout(300)
        print("  submit disabled after fill:", await sb.is_disabled(), "hint:", await hint.inner_text() if await hint.count() else None)
        if not await sb.is_disabled():
            await sb.click(); await page.wait_for_timeout(2000)
        fe = page.locator('[data-testid="register-form-error"]')
        ok(await fe.count() and await fe.get_attribute("role") == "alert", f"register-form-error alert: {await fe.inner_text() if await fe.count() else None}")
        pi = page.locator('[data-testid="register-password-input"]')
        ok(await pi.get_attribute("aria-invalid") == "true", f"password aria-invalid={await pi.get_attribute('aria-invalid')} db={await pi.get_attribute('aria-describedby')}")
        await ax(page, "register weak password error")
        # strength meter levels
        for pwd in ("abc", "abcdefgh1", "Abcdefgh1", "Abcdefgh1!xyz"):
            await pi.fill(pwd); await page.wait_for_timeout(300)
            await ax(page, f"register strength '{pwd}'")
        await ctx.close()
        # ---- parent: guided modal ----
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.request.post(BASE + "/api/auth/login", data={"email": email, "password": pw})
        page = await ctx.new_page()
        await page.goto(BASE + "/"); await page.wait_for_timeout(3500)
        found = False
        for door in ("door-self", "door-court", "door-comm"):
            await page.goto(BASE + "/"); await page.wait_for_timeout(3000)
            d = page.locator(f'[data-testid="{door}"]')
            if not await d.count(): continue
            await d.click(); await page.wait_for_timeout(2500)
            tids = await page.evaluate("() => [...document.querySelectorAll('[data-testid]')].filter(e => e.getBoundingClientRect().height>0).map(e => e.getAttribute('data-testid')).filter(t => /guided|readiness|conflict|journey-card|start/i.test(t)).slice(0,20)")
            print(door, "->", tids)
            for t in tids:
                if t.startswith("modal-"): continue
                el = page.locator(f'[data-testid="{t}"]').first
                try:
                    await el.scroll_into_view_if_needed(); await el.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(2000)
                except Exception:
                    continue
                if await page.locator('[data-testid^="modal-guided-"]').count():
                    found = True
                    print("guided opened via", t, await page.evaluate(DLG), "focus:", await page.evaluate(FOCUS_JS))
                    seq = []
                    for _ in range(25):
                        await page.keyboard.press("Tab"); seq.append(await page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
                    ok(all(seq), f"guided Tab trapped out={seq.count(False)}")
                    await ax(page, "guided modal")
                    await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
                    f = await page.evaluate(FOCUS_JS)
                    ok(await page.locator('[data-testid^="modal-guided-"]').count() == 0, f"guided Esc closes; focus -> {f} (launcher {t})")
                    break
                if await page.locator('[role=dialog]').count():
                    print("  non-guided dialog via", t, await page.evaluate(DLG)); await page.keyboard.press("Escape"); await page.wait_for_timeout(500)
            if found: break
        if not found: print("WARN guided modal launcher not found")
        await ctx.close(); await b.close()

asyncio.run(main())
