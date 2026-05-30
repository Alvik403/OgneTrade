"""Smoke tests for lids project. Run: docker compose exec app python test_smoke.py"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
errors = []
passed = 0


def req(method, path, body=None, headers=None, cookies=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if cookies:
        h["Cookie"] = cookies
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            set_cookie = resp.headers.get("Set-Cookie", "")
            return resp.status, json.loads(raw) if raw else {}, set_cookie
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw.decode(errors="replace")}
        return e.code, payload, ""


def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
        print(f"  OK  {name}")
    else:
        errors.append(f"{name}: {detail}")
        print(f" FAIL {name} — {detail}")


print("=== Public API ===")
code, data, _ = req("GET", "/health")
check("health", code == 200 and data.get("status") == "ok", str(data))

code, data, _ = req("GET", "/api/public/settings/contacts")
check("contacts", code == 200 and "phone" in data, str(data))

code, products, _ = req("GET", "/api/public/products")
check("products", code == 200 and len(products) >= 4, f"count={len(products) if isinstance(products, list) else products}")

code, _, _ = req("POST", "/api/public/track/view")
check("track view", code == 200)

pid = products[0]["id"] if products else None
if pid:
    code, _, _ = req("POST", "/api/public/track/click", {"product_id": pid})
    check("track click", code == 200)

# Get CSRF from homepage
r = urllib.request.Request(BASE + "/")
with urllib.request.urlopen(r) as resp:
    home_code = resp.status
    cookies_hdr = resp.headers.get("Set-Cookie", "")
check("homepage", home_code == 200)

csrf = ""
for part in cookies_hdr.split(","):
    if "csrf_token=" in part:
        csrf = part.split("csrf_token=")[1].split(";")[0].strip()
        break

code, lead_data, _ = req(
    "POST",
    "/api/public/leads",
    {
        "name": "Тест Тестов",
        "phone": "+7 (999) 111-22-33",
        "email": "test@example.ru",
        "product_id": pid,
        "product_name": "ЯГЕЛЬ 1 л — огнетушитель гидрогелевый",
        "comment": "smoke test",
    },
    headers={"X-CSRF-Token": csrf},
    cookies=f"csrf_token={csrf}" if csrf else None,
)
check("create lead", code == 200 and lead_data.get("ok"), f"code={code} {lead_data}")

print("\n=== Admin auth ===")
for email, password, role in [
    ("admin@example.ru", "admin12345", "super_admin"),
    ("manager@example.ru", "manager12345", "manager"),
]:
    code, login, cookie_hdr = req("POST", "/api/admin/auth/login", {"email": email, "password": password})
    check(f"login {role}", code == 200 and login.get("user", {}).get("role") == role, str(login))

    # Extract cookies for authenticated requests
    cookies = cookie_hdr
    code, me, _ = req("GET", "/api/admin/auth/me", cookies=cookies)
    check(f"me {role}", code == 200, str(me))

    code, leads, _ = req("GET", "/api/admin/leads", cookies=cookies)
    check(f"leads {role}", code == 200 and isinstance(leads, list), str(leads)[:100])
    code, counts, _ = req("GET", "/api/admin/leads/counts", cookies=cookies)
    check(f"lead counts {role}", code == 200 and "unread" in counts, str(counts))

    code, overview, _ = req("GET", "/api/admin/analytics/overview", cookies=cookies)
    check(f"analytics {role}", code == 200, str(overview)[:100])
    code, dashboard, _ = req("GET", "/api/admin/analytics/dashboard?period=7d", cookies=cookies)
    check(f"analytics dashboard {role}", code == 200 and "summary" in dashboard, str(dashboard)[:100])

    if role == "super_admin":
        code, users, _ = req("GET", "/api/admin/users", cookies=cookies)
        check("users admin only", code == 200, str(users)[:100])
        manager_user = next((u for u in users if u.get("role") == "manager"), None)
        if manager_user:
            mid = manager_user["id"]
            code, updated, _ = req("PATCH", f"/api/admin/users/{mid}", {"role": "super_admin"}, cookies=cookies)
            check("promote user role", code == 200 and updated.get("role") == "super_admin", str(updated)[:100])
            code, updated, _ = req("PATCH", f"/api/admin/users/{mid}", {"role": "manager"}, cookies=cookies)
            check("demote user role", code == 200 and updated.get("role") == "manager", str(updated)[:100])
        code, settings, _ = req("GET", "/api/admin/settings", cookies=cookies)
        check("settings", code == 200, str(settings)[:100])
    else:
        code, _, _ = req("GET", "/api/admin/users", cookies=cookies)
        check("manager blocked from users", code == 403, f"code={code}")
        code, _, _ = req("GET", "/api/admin/settings", cookies=cookies)
        check("manager blocked from settings", code == 403, f"code={code}")

    code, managers, _ = req("GET", "/api/admin/users/managers", cookies=cookies)
    check(f"managers list {role}", code == 200, str(managers)[:100])

print("\n=== Admin pages SSR ===")
for path in ["/admin/login", "/admin/clients", "/admin/analytics"]:
    r = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(r) as resp:
            check(f"page {path}", resp.status in (200, 302), f"status={resp.status}")
    except urllib.error.HTTPError as e:
        check(f"page {path}", e.code in (200, 302, 401), f"status={e.code}")

print(f"\n=== RESULT: {passed} passed, {len(errors)} failed ===")
if errors:
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("All smoke tests passed.")
