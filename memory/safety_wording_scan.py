"""Scan parent-visible screens for leftover safety-assessment wording. Usage: python safety_wording_scan.py"""
import asyncio
import json
import re

from playwright.async_api import async_playwright

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0]
ROUTES = """/ /accessibility /account /activities/alignment /activities/reflection /calendar /case-settings /coach /communication
/communication/alignment /communication/reflection /companion-assessment /complete-alignment-report /confidentiality /dashboard
/data-retention /delete-account /for-professionals /foundation/demo /help /interventions /join /join/sample-preview /joint-agreement
/joint-professional-report /joint-reports /learning /legacy /legal/app-store-privacy /legal/hb300 /legal/hipaa /legal/privacy-practices
/login /mediator-badge /methodology /my-plan /nd-risk-assessment /onboarding/what-do-you-need /orientation /pathway-report /plan-options
/prep/child-goals /prep/communication /prep/issues /prep/priority /prep/readiness /privacy /privacy-notice /privacy-policy /problem-solving
/professionals /progress /reflection /register /safety /safety-assessment /samples /samples/co-parenting /samples/joint-alignment-preview
/schedule/alignment /schedule/reflection /shared-with-professionals /signup /situation /special-needs-v2 /special-needs-v2/compare
/special-needs-v2/educational-deep-dive /special-needs-v2/educational-deep-dive/compare /special-needs-v2/medical-deep-dive
/special-needs-v2/medical-deep-dive/compare /special-needs-v2/psychological-deep-dive /special-needs-v2/psychological-deep-dive/compare
/special-needs-v2/report /summary /terms /watch /what-professionals-see""".split()
PAT = re.compile(r"[^.\n]{0,60}(safety screen|safety assessment|safety check|safety plan|safety reflection|safety and functioning|"
                 r"family violence|domestic violence|violence|screening)[^.\n]{0,60}", re.I)


async def scan(page, who):
    hits = {}
    for r in ROUTES:
        try:
            await page.goto(BASE + r, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(900)
            text = await page.evaluate("document.body.innerText")
            found = sorted({m.group(0).strip() for m in PAT.finditer(text)})
            if found:
                hits[r] = {"landed": page.url.replace(BASE, ""), "snippets": found[:6]}
                print(who, r, "->", hits[r]["landed"], "|", " || ".join(found[:6]), flush=True)
        except Exception as e:  # noqa: BLE001
            hits[r] = {"error": str(e)[:80]}
    return who, hits


async def main():
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/pw-browsers/chromium_headless_shell-1208/chrome-linux/headless_shell")
        anon = await (await b.new_context(viewport={"width": 1280, "height": 900})).new_page()
        pg = await (await b.new_context(viewport={"width": 1280, "height": 900})).new_page()
        await pg.goto(BASE + "/login", wait_until="networkidle")
        try:
            await pg.get_by_role("button", name="Sign in with email").click(timeout=4000)
        except Exception:  # noqa: BLE001
            pass
        await pg.fill("input[type=email]", "parent1@test.com")
        await pg.fill("input[type=password]", "TestPass123!")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(4000)
        (_, out["signed_out"]), (_, out["parent"]) = await asyncio.gather(scan(anon, "signed_out"), scan(pg, "parent"))
        await b.close()
    json.dump(out, open("/app/memory/safety_wording_scan.json", "w"), indent=1)
    for who, hits in out.items():
        print(f"== {who}: {len(hits)} screens with matches")
        for r, v in hits.items():
            print(" ", r, "->", v.get("landed", ""), "|", " || ".join(v.get("snippets", [])) or v.get("error"))


asyncio.run(main())
