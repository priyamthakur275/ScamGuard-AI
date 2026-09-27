import re, sys, time, json, os
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get("BASE","http://127.0.0.1:3000")
SHOTS=os.environ.get("SHOTS","/tmp/shots")
os.makedirs(SHOTS,exist_ok=True)
EMAIL=f"e2e{int(time.time())}@example.com"; PW="Str0ngPassw0rd"
results=[]; errors=[]
def check(name, fn):
    try:
        fn(); results.append((name,"PASS",""))
        print("PASS",name,flush=True)
    except Exception as e:
        results.append((name,"FAIL",str(e)[:300])); print("FAIL",name,str(e)[:300],flush=True)
def solve(page):
    q=page.locator("text=/What is \\d+ [+-] \\d+\\?/").first
    q.wait_for(timeout=15000)
    m=re.search(r"(\d+) ([+-]) (\d+)",q.inner_text())
    a,op,b=int(m[1]),m[2],int(m[3]); return str(a+b if op=="+" else a-b)
SCAM="URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone. Call +91 9876543210."
EMAILTXT="""From: "SBI Security" <alerts@sbi-secure-mail.xyz>
Reply-To: verify@gmail.com
Subject: Account suspended - action required
Authentication-Results: spf=fail dkim=fail

Dear customer, your account is suspended. Click http://sbi-login-verify.top to verify your password and OTP within 24 hours."""
def wait_verdict(page, timeout=60000):
    page.locator("text=/scam probability/").first.wait_for(timeout=timeout)
def go_tab(page,label):
    page.get_by_role("button",name=re.compile(label)).first.click()
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={"width":1440,"height":900}, accept_downloads=True)
    page=ctx.new_page()
    page.on("pageerror",lambda e: errors.append(("pageerror",page.url,str(e))))
    page.on("console",lambda m: errors.append(("console",page.url,m.text)) if m.type=="error" else None)
    def landing():
        page.goto(BASE); page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{SHOTS}/01_landing.png",full_page=True)
    check("landing renders",landing)
    def register():
        page.goto(BASE+"/register"); page.wait_for_load_state("networkidle")
        page.get_by_label("Email").fill(EMAIL)
        page.get_by_label("Password",exact=True).fill(PW)
        page.get_by_label("Confirm password").fill(PW)
        page.get_by_label("Verification answer").fill(solve(page))
        page.screenshot(path=f"{SHOTS}/02_register.png",full_page=True)
        page.get_by_role("button",name=re.compile("Create account")).click()
        page.wait_for_url("**/dashboard",timeout=30000); page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{SHOTS}/03_dashboard_empty.png",full_page=True)
    check("register with CAPTCHA -> dashboard",register)
    def text_scan():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{SHOTS}/04_analyze.png",full_page=True)
        page.get_by_label("text evidence").fill(SCAM)
        page.get_by_role("button",name=re.compile("Analyze evidence")).click()
        wait_verdict(page)
        page.wait_for_timeout(800)
        page.screenshot(path=f"{SHOTS}/05_text_verdict.png",full_page=True)
    check("text scan -> verdict",text_scan)
    def feedback():
        page.get_by_role("button",name="Mark as accurate").click()
        page.locator("text=/feedback/i").first.wait_for(timeout=10000)
    check("feedback submit",feedback)
    def copilot():
        panel=page.locator("[id^=copilot-]").first
        panel.scroll_into_view_if_needed()
        btns=panel.get_by_role("button")
        print("copilot buttons:",[btns.nth(i).inner_text() for i in range(min(btns.count(),8))])
        btns.first.click()
        page.wait_for_timeout(2500)
        panel.screenshot(path=f"{SHOTS}/06_copilot.png")
    check("copilot answer",copilot)
    def report():
        btn=page.get_by_role("button",name=re.compile("Export|report|Download",re.I)).first
        btn.click(); page.wait_for_timeout(300)
        with page.expect_download(timeout=30000) as d:
            page.get_by_role("menuitem",name="PDF",exact=True).first.click() if page.get_by_role("menuitem").count() else page.get_by_role("button",name="PDF",exact=True).first.click()
        path=d.value.path(); assert os.path.getsize(path)>500, "empty pdf"
        assert open(path,"rb").read(4)==b"%PDF"
    check("PDF report download",report)
    def url_scan():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        go_tab(page,"^URL$")
        page.get_by_label("url evidence").fill("http://paypal-secure-login.verify-account.top/signin")
        page.get_by_role("button",name=re.compile("Analyze evidence")).click()
        wait_verdict(page)
        page.screenshot(path=f"{SHOTS}/07_url_verdict.png",full_page=True)
    check("URL scan -> verdict",url_scan)
    def email_scan():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        go_tab(page,"^Email$")
        page.get_by_label("email evidence").fill(EMAILTXT)
        page.get_by_role("button",name=re.compile("Analyze evidence")).click()
        wait_verdict(page)
        page.screenshot(path=f"{SHOTS}/08_email_verdict.png",full_page=True)
    check("email scan -> verdict + forensics",email_scan)
    def file_scan(tab, f, shot):
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        go_tab(page,tab)
        page.locator("input[type=file]").set_input_files(f)
        page.get_by_role("button",name=re.compile("Analyze evidence")).click()
        wait_verdict(page,90000)
        page.screenshot(path=f"{SHOTS}/{shot}.png",full_page=True)
    check("image OCR scan -> verdict",lambda: file_scan("Image","/tmp/fx/scam.png","09_image"))
    check("PDF scan -> verdict",lambda: file_scan("^PDF$","/tmp/fx/scam.pdf","10_pdf"))
    check("QR scan -> verdict",lambda: file_scan("QR","/tmp/fx/qr.png","11_qr"))
    def voice():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        go_tab(page,"Voice")
        page.screenshot(path=f"{SHOTS}/12_voice_tab.png",full_page=True)
        ta=page.locator("textarea").first
        ta.fill("Hello sir this is calling from RBI, your card is blocked, please tell me the OTP now or your account will be frozen today.")
        page.get_by_role("button",name=re.compile("Analy[sz]e transcript|Analyze",re.I)).last.click()
        wait_verdict(page)
        page.screenshot(path=f"{SHOTS}/13_voice_verdict.png",full_page=True)
    check("voice transcript -> verdict",voice)
    def camera_tab():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        go_tab(page,"Camera"); page.wait_for_timeout(1500)
        page.screenshot(path=f"{SHOTS}/14_camera_tab.png",full_page=True)
    check("camera tab renders (no device)",camera_tab)
    for name,path,shot in [("dashboard","/dashboard","15_dashboard"),("history","/history","16_history"),("analytics","/analytics","17_analytics"),("cases","/cases","18_cases"),("settings","/settings","19_settings"),("demo","/demo","20_demo")]:
        def pg(path=path,shot=shot):
            page.goto(BASE+path); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
            page.screenshot(path=f"{SHOTS}/{shot}.png",full_page=True)
            assert "Something went wrong" not in page.content()
        check(f"{name} page renders",pg)
    def admin_denied():
        page.goto(BASE+"/admin"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
        page.screenshot(path=f"{SHOTS}/21_admin_denied.png",full_page=True)
    check("admin page as regular user",admin_denied)
    def wrong_captcha():
        c3=b.new_context(); p3=c3.new_page(); p3.goto(BASE+"/register"); p3.wait_for_load_state("networkidle")
        q1=p3.locator("text=/What is \\d+ [+-] \\d+\\?/").first; q1.wait_for(timeout=10000)
        p3.get_by_label("Email").fill("wrongcap"+EMAIL); p3.get_by_label("Password",exact=True).fill(PW); p3.get_by_label("Confirm password").fill(PW)
        p3.get_by_label("Verification answer").fill("999")
        tok_before=p3.evaluate("1")
        p3.get_by_role("button",name=re.compile("Create account")).click()
        p3.locator("text=/verification answer wasn't correct/").wait_for(timeout=10000)
        # answer box cleared by the fresh challenge and a new question is solvable
        for _ in range(50):
            if p3.get_by_label("Verification answer").input_value()=="": break
            p3.wait_for_timeout(200)
        assert p3.get_by_label("Verification answer").input_value()=="", "answer not reset"
        p3.get_by_label("Verification answer").fill(solve(p3))
        p3.get_by_role("button",name=re.compile("Create account")).click()
        p3.wait_for_url("**/dashboard",timeout=30000); c3.close()
    check("wrong CAPTCHA -> new challenge -> register succeeds",wrong_captcha)
    def case_flow():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        page.get_by_label("text evidence").fill(SCAM)
        page.get_by_role("button",name=re.compile("Analyze evidence")).click(); wait_verdict(page)
        page.get_by_role("button",name="Create case").click()
        page.wait_for_url(re.compile(r"/cases/[0-9a-f-]+"),timeout=20000); page.wait_for_load_state("networkidle")
        page.get_by_role("button",name=re.compile("^investigating$",re.I)).click(); page.wait_for_timeout(1200)
        assert page.get_by_role("button",name=re.compile("^investigating$",re.I)).get_attribute("aria-pressed")=="true"
        page.get_by_label("Investigation note").fill("Called bank; number is not official.")
        page.get_by_role("button",name="Add note").click()
        page.locator("li", has_text="Called bank; number is not official.").first.wait_for(timeout=10000)
        assert page.get_by_label("Investigation note").input_value()==""
        page.screenshot(path=f"{SHOTS}/27_case_detail.png",full_page=True)
        page.get_by_role("button",name="Export report").click()
        with page.expect_download(timeout=30000) as d:
            page.get_by_role("menuitem",name="PDF",exact=True).click()
        pth=d.value.path(); assert open(pth,"rb").read(4)==b"%PDF"
        page.get_by_role("button",name="Export report").click()
        with page.expect_download(timeout=30000) as d:
            page.get_by_role("menuitem",name="JSON",exact=True).click()
        json.load(open(d.value.path()))
        page.goto(BASE+"/cases"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(600)
        page.screenshot(path=f"{SHOTS}/28_cases_list.png",full_page=True)
    check("case: create from scan, status, note, PDF+JSON report",case_flow)
    def history_ops():
        page.goto(BASE+"/history"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(600)
        sw=page.evaluate("(()=>{const el=document.querySelector('table').parentElement;return [el.scrollWidth, el.clientWidth]})()")
        assert sw[0]<=sw[1]+1, f"table overflows {sw}"
        page.get_by_label("Filter threat level").select_option("critical"); page.wait_for_timeout(300)
        rows=page.locator("tbody tr").count(); assert rows>=1
        page.get_by_label("Filter threat level").select_option("low"); page.wait_for_timeout(300)
        page.get_by_text("No matching entries found").wait_for(timeout=3000)
        page.get_by_label("Filter threat level").select_option("all")
        with page.expect_download() as d: page.get_by_role("button",name=re.compile("CSV")).click()
        txt=open(d.value.path()).read(); assert txt.startswith('id,created_at'), txt[:40]
        page.get_by_role("button",name="Expand details").first.click(); page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/29_history_expanded.png",full_page=True)
        n=page.locator("tbody tr").count()
        page.once("dialog",lambda dlg: dlg.accept())
        page.get_by_role("button",name="Delete entry").first.click()
        page.get_by_text("Scan deleted").wait_for(timeout=10000)
    check("history: fits width, threat filter, CSV export, expand, delete",history_ops)
    def copilot_width():
        page.goto(BASE+"/analyze"); page.wait_for_load_state("networkidle")
        page.get_by_label("text evidence").fill(SCAM)
        page.get_by_role("button",name=re.compile("Analyze evidence")).click(); wait_verdict(page)
        box=page.get_by_label("Ask Copilot a question").bounding_box(); panel=page.locator("[id^=copilot-]").first.bounding_box()
        assert box["width"]>panel["width"]*0.6, (box,panel)
        page.get_by_label("Ask Copilot a question").fill("What should I do?"); page.keyboard.press("Enter")
        page.locator("text=/Evidence template|LLM/").first.wait_for(timeout=15000)
        page.locator("[id^=copilot-]").first.screenshot(path=f"{SHOTS}/30_copilot.png")
    check("copilot: free-text question, full-width input",copilot_width)
    def dark():
        page.goto(BASE+"/dashboard"); page.wait_for_load_state("networkidle")
        page.get_by_role("button",name=re.compile("theme|dark|light",re.I)).first.click(); page.wait_for_timeout(500)
        assert page.evaluate("document.documentElement.classList.contains('dark')")
        page.screenshot(path=f"{SHOTS}/31_dashboard_dark.png",full_page=True)
        page.goto(BASE+"/analytics"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1500)
        page.screenshot(path=f"{SHOTS}/32_analytics_dark.png",full_page=True)
        page.get_by_role("button",name=re.compile("theme|dark|light",re.I)).first.click(); page.wait_for_timeout(300)
    check("dark theme toggle",dark)
    # mobile
    CLIP_JS = """() => {
      const W = window.innerWidth, bad = [];
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (el.closest('.sr-only,[aria-hidden=true],svg,.skip-link')) continue;
        if (getComputedStyle(el).visibility === 'hidden') continue;
        // content inside an intentional horizontal scroller is fine
        let p = el.parentElement, scroller = false;
        while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll') { scroller = true; break; } p = p.parentElement; }
        if (scroller) continue;
        if (r.right > W + 1 || r.left < -1) bad.push((el.tagName + '.' + (el.className && el.className.baseVal === undefined ? el.className : '')).slice(0, 80) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
      }
      return bad.slice(0, 8);
    }"""
    def mobile():
        m=b.new_context(viewport={"width":390,"height":844}, storage_state=ctx.storage_state())
        mp=m.new_page()
        problems=[]
        for path,shot in [("/","22_m_landing"),("/dashboard","23_m_dashboard"),("/analyze","24_m_analyze"),("/history","25_m_history"),("/analytics","33_m_analytics"),("/cases","34_m_cases"),("/settings","35_m_settings"),("/demo","36_m_demo")]:
            mp.goto(BASE+path); mp.wait_for_load_state("networkidle"); mp.wait_for_timeout(900)
            sw=mp.evaluate("document.documentElement.scrollWidth")
            if sw>390: problems.append(f"{path} page overflow {sw}")
            bad=mp.evaluate(CLIP_JS)
            if bad: problems.append(f"{path}: {bad}")
            mp.screenshot(path=f"{SHOTS}/{shot}.png",full_page=True)
        # a verdict on mobile
        mp.goto(BASE+"/analyze"); mp.wait_for_load_state("networkidle")
        mp.get_by_label("text evidence").fill(SCAM)
        mp.get_by_role("button",name=re.compile("Analyze evidence")).click(); wait_verdict(mp); mp.wait_for_timeout(800)
        bad=mp.evaluate(CLIP_JS)
        if bad: problems.append(f"verdict: {bad}")
        mp.screenshot(path=f"{SHOTS}/37_m_verdict.png",full_page=True)
        m.close()
        assert not problems, problems
    check("mobile 390px: no page overflow or clipped elements (8 pages + verdict)",mobile)
    def logout():
        page.goto(BASE+"/dashboard"); page.wait_for_load_state("networkidle")
        page.get_by_role("button",name=re.compile("Sign out|Log out|Logout",re.I)).first.click()
        page.wait_for_url(re.compile(r"/(login|$)"),timeout=10000)
    check("logout",logout)
    def login():
        page.goto(BASE+"/login"); page.get_by_label("Email").fill(EMAIL); page.get_by_label("Password").fill(PW)
        page.screenshot(path=f"{SHOTS}/26_login.png",full_page=True)
        page.get_by_role("button",name=re.compile("^Sign in")).click()
        page.wait_for_url("**/dashboard",timeout=20000)
    check("login",login)
    def protected():
        c2=b.new_context(); p2=c2.new_page(); p2.goto(BASE+"/history"); p2.wait_for_url("**/login**",timeout=10000); c2.close()
    check("protected route redirects when logged out",protected)
    b.close()
print(json.dumps({"email":EMAIL,"results":results,"errors":errors},indent=1))
