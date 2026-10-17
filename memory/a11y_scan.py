import asyncio, json, sys
from playwright.async_api import async_playwright

BASE = sys.argv[1]
OUT = sys.argv[2]
AXE = open("/app/frontend/node_modules/axe-core/axe.min.js").read()
PUBLIC = ["/", "/legacy", "/login", "/register", "/signup", "/forgot-password", "/privacy", "/privacy-notice", "/terms",
          "/accessibility", "/methodology", "/what-professionals-see", "/legal/hipaa", "/legal/hb300",
          "/legal/privacy-practices", "/legal/app-store-privacy", "/data-retention", "/professionals", "/for-professionals",
          "/for-portal-engineers", "/samples", "/samples/co-parenting", "/samples/joint-alignment-preview", "/join",
          "/join/sample-preview", "/mediator-badge", "/foundation/demo", "/help", "/calendar", "/safety", "/watch"]
PARENT = ["/", "/align", "/account", "/delete-account", "/cancel-subscription", "/case-settings", "/plan-options",
          "/communication", "/communication/reflection", "/communication/alignment", "/schedule/reflection", "/schedule/alignment",
          "/activities/reflection", "/activities/alignment", "/alignment/subjects", "/situation", "/joint-reports",
          "/joint-agreement", "/pathway-report", "/complete-alignment-report", "/complete-alignment-report/joint/SA-DEMO01",
          "/shared-with-professionals", "/share/professional", "/nd-risk-assessment", "/companion-assessment", "/interventions",
          "/problem-solving", "/my-plan", "/coach", "/learning", "/prep/child-goals", "/prep/issues", "/prep/priority",
          "/prep/communication", "/prep/readiness", "/summary", "/reflection", "/orientation", "/progress", "/special-needs-v2",
          "/special-needs-v2/report", "/special-needs-v2/compare", "/special-needs-v2/educational-deep-dive",
          "/special-needs-v2/psychological-deep-dive", "/special-needs-v2/medical-deep-dive", "/onboarding/what-do-you-need",
          "/professional/joint-alignment/new", "/professional/joint-alignment/mine", "/gmail", "/case/SA-DEMO01"]
ADMIN = ["/admin", "/admin/accounts", "/admin/consent", "/admin/consent-trend", "/admin/users", "/admin/surveys",
         "/admin/insights", "/admin/nudge-copy", "/admin/bridge-copy", "/admin/audit-log", "/admin/help-services",
         "/admin/reviewers", "/admin/nd-coordinator", "/admin/professionals"]
if len(sys.argv) > 3:
    keep = set(sys.argv[3].split(","))
    PUBLIC, PARENT, ADMIN = [p for p in PUBLIC if "guest:" + p in keep], [p for p in PARENT if "parent:" + p in keep], [p for p in ADMIN if "admin:" + p in keep]
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
JS = """(tags) => axe.run(document, {runOnly: {type: 'tag', values: tags}}).then(r => r.violations.map(v => ({
  id: v.id, impact: v.impact, n: v.nodes.length, help: v.help,
  nodes: v.nodes.slice(0, 40).map(x => ({t: x.target.join(' ').slice(-100), html: x.html.slice(0, 160), d: (x.any[0] || {}).data}))})))"""


async def scan(ctx, path, who):
    page = await ctx.new_page()
    out = {"path": path, "who": who}
    try:
        await page.goto(BASE + path, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(2500)
        await page.add_script_tag(content=AXE)
        out["violations"] = await page.evaluate(JS, TAGS)
        out["final_url"] = page.url.replace(BASE, "")
        out["overflow"] = await page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1")
        await page.evaluate("document.documentElement.style.fontSize = '200%'")
        await page.wait_for_timeout(400)
        out["overflow_200"] = await page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1")
    except Exception as e:
        out["error"] = str(e)[:200]
    await page.close()
    return out


async def run_group(b, who, cred, paths, results):
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    await ctx.add_init_script("try{localStorage.setItem('sac_ai_notice_ack','1')}catch(e){}")
    if cred:
        r = await ctx.request.post(BASE + "/api/auth/login", data={"email": cred[0], "password": cred[1]})
        print(who, "login", r.status, flush=True)
    for path in paths:
        r = await scan(ctx, path, who)
        results.append(r)
        print(who, path, len(r.get("violations", [])), r.get("error", ""), flush=True)
    await ctx.close()


async def main():
    results = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await asyncio.gather(
            run_group(b, "guest", None, PUBLIC, results),
            run_group(b, "parent", ("parent1@test.com", "TestPass123!"), PARENT, results),
            run_group(b, "admin", ("mattsossi@bsossi.com", "AdminPass123!"), ADMIN, results),
        )
        await b.close()
    json.dump(results, open(OUT, "w"), indent=1)
    print("DONE", flush=True)


asyncio.run(main())
