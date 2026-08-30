"""End-to-end smoke test: walks every user flow against a real MongoDB.

Run it against a throwaway database, never your family's data:

    MONGO_DB=questly_test python tests/smoke_test.py

Or inside the running stack:

    docker compose exec -e MONGO_DB=questly_test web python tests/smoke_test.py

It wipes every collection in the target database before it starts, so it
refuses to run unless the database name ends in `_test`.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB_NAME = os.environ.get("MONGO_DB", "")
if not DB_NAME.endswith("_test"):
    sys.exit("Refusing to run: point MONGO_DB at a database whose name ends "
             "in '_test' (this script deletes everything in it).")

from app import create_app
from app.db import get_db
from app.models import check_password

FAILS = []

def check(label, cond, extra=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"   [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(label)

app = create_app()
with app.app_context():
    db = get_db()
    for c in ("users", "rewards", "transactions", "redemptions", "quests", "quest_claims"):
        db[c].delete_many({})

def token(client, path):
    """Pull the CSRF token out of a rendered page."""
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="_csrf" value="([^"]+)"', html)
    return m.group(1) if m else None

parent = app.test_client()
kidcli = app.test_client()

print("\n--- first-run setup ---")
r = parent.get("/", follow_redirects=False)
check("/ redirects to /setup when empty", r.headers.get("Location", "").endswith("/setup"), r.headers.get("Location"))

t = token(parent, "/setup")
r = parent.post("/setup", data={"_csrf": t, "name": "Matt", "email": "matt@example.com",
                                "password": "password123", "confirm": "password123"},
                follow_redirects=True)
check("setup creates parent and logs in", "Family" in r.get_data(as_text=True))

print("\n--- csrf ---")
r = parent.post("/setup", data={"name": "X", "email": "x@y.z", "password": "password123",
                                "confirm": "password123"})
check("POST without a CSRF token is rejected", r.status_code == 400, str(r.status_code))

print("\n--- add a child ---")
t = token(parent, "/parent/family")
r = parent.post("/parent/family/kids", data={"_csrf": t, "name": "Ava", "avatar": "\U0001f984",
                                             "color": "#ff4d94", "pin": "1234", "points": "0"},
                follow_redirects=True)
check("child added", "Ava" in r.get_data(as_text=True))

with app.app_context():
    db = get_db()
    kid = db.users.find_one({"name": "Ava"})
kid_id = str(kid["_id"])
check("child starts on zero points", kid["points"] == 0, str(kid["points"]))

print("\n--- awarding points ---")
t = token(parent, "/parent/")
parent.post("/parent/award", data={"_csrf": t, "kid_id": kid_id, "amount": "25",
                                   "reason": "Tidied the whole kitchen"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("+25 applied", kid["points"] == 25, str(kid["points"]))

parent.post("/parent/award", data={"_csrf": t, "kid_id": kid_id, "amount": "5",
                                   "negate": "1", "reason": "Wouldn't share"}, follow_redirects=True)
with app.app_context():
    db = get_db()
    kid = db.users.find_one({"_id": kid["_id"]})
    ledger = list(db.transactions.find({"kid_id": kid["_id"]}).sort("created_at", 1))
check("take-away applied", kid["points"] == 20, str(kid["points"]))
check("ledger has both entries", len(ledger) == 2, str(len(ledger)))
check("ledger balance_after tracks", [e["balance_after"] for e in ledger] == [25, 20],
      str([e["balance_after"] for e in ledger]))

parent.post("/parent/award", data={"_csrf": t, "kid_id": kid_id, "amount": "9999",
                                   "negate": "1", "reason": "overdraw attempt"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("balance cannot go negative", kid["points"] == 0, str(kid["points"]))

parent.post("/parent/award", data={"_csrf": t, "kid_id": kid_id, "amount": "50",
                                   "reason": "Great week"}, follow_redirects=True)

print("\n--- shop admin ---")
t = token(parent, "/parent/rewards")
parent.post("/parent/rewards", data={"_csrf": t, "title": "Cinema trip", "emoji": "\U0001f37f",
                                     "cost": "30", "stock": "1",
                                     "description": "Popcorn included"}, follow_redirects=True)
parent.post("/parent/rewards", data={"_csrf": t, "title": "Very Expensive Thing", "emoji": "\U0001f48e",
                                     "cost": "5000", "stock": ""}, follow_redirects=True)
with app.app_context():
    db = get_db()
    reward = db.rewards.find_one({"title": "Cinema trip"})
    pricey = db.rewards.find_one({"title": "Very Expensive Thing"})
check("reward created with stock", reward and reward["stock"] == 1)
check("blank stock means unlimited", pricey and pricey["stock"] is None)

print("\n--- quest admin ---")
t = token(parent, "/parent/quests")
parent.post("/parent/quests", data={"_csrf": t, "title": "Read for 20 minutes", "emoji": "\U0001f4d6",
                                    "points": "5", "repeat": "daily"}, follow_redirects=True)
with app.app_context():
    quest = get_db().quests.find_one({"title": "Read for 20 minutes"})
check("quest created", quest is not None)

print("\n--- kid login by PIN ---")
r = kidcli.get(f"/hi/{kid_id}")
check("PIN page shown", "pinform" in r.get_data(as_text=True))
t = token(kidcli, f"/hi/{kid_id}")
r = kidcli.post(f"/hi/{kid_id}", data={"_csrf": t, "pin": "0000"}, follow_redirects=True)
check("wrong PIN refused", "pinform" in r.get_data(as_text=True))
t = token(kidcli, f"/hi/{kid_id}")
r = kidcli.post(f"/hi/{kid_id}", data={"_csrf": t, "pin": "1234"}, follow_redirects=True)
check("right PIN gets in", "Ava" in r.get_data(as_text=True) and "Today's quests" in r.get_data(as_text=True))

print("\n--- kid cannot reach parent pages ---")
r = kidcli.get("/parent/", follow_redirects=False)
check("kid bounced off parent area", r.status_code in (301, 302), str(r.status_code))

print("\n--- kid does a quest ---")
t = token(kidcli, "/me/")
r = kidcli.post(f"/me/quests/{quest['_id']}/done", data={"_csrf": t}, follow_redirects=True)
check("quest claim shows as waiting", "Waiting" in r.get_data(as_text=True))
t = token(kidcli, "/me/")
kidcli.post(f"/me/quests/{quest['_id']}/done", data={"_csrf": t}, follow_redirects=True)
with app.app_context():
    claims = list(get_db().quest_claims.find({"quest_id": quest["_id"]}))
check("same quest can't be claimed twice in a day", len(claims) == 1, str(len(claims)))

with app.app_context():
    claim = get_db().quest_claims.find_one({"quest_id": quest["_id"]})
t = token(parent, "/parent/approvals")
parent.post(f"/parent/approvals/quest/{claim['_id']}",
            data={"_csrf": t, "decision": "approve"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("approved quest pays out", kid["points"] == 55, str(kid["points"]))

print("\n--- kid buys a reward ---")
t = token(kidcli, "/me/shop")
r = kidcli.post(f"/me/shop/{reward['_id']}/buy", data={"_csrf": t}, follow_redirects=True)
with app.app_context():
    db = get_db()
    kid = db.users.find_one({"_id": kid["_id"]})
    red = db.redemptions.find_one({"reward_id": reward["_id"]})
    stock = db.rewards.find_one({"_id": reward["_id"]})["stock"]
check("points deducted at purchase", kid["points"] == 25, str(kid["points"]))
check("redemption queued for approval", red and red["status"] == "pending")
check("stock decremented", stock == 0, str(stock))

t = token(kidcli, "/me/shop")
r = kidcli.post(f"/me/shop/{reward['_id']}/buy", data={"_csrf": t}, follow_redirects=True)
check("sold-out item can't be bought again", "sold out" in r.get_data(as_text=True).lower())

t = token(kidcli, "/me/shop")
r = kidcli.post(f"/me/shop/{pricey['_id']}/buy", data={"_csrf": t}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("can't buy what you can't afford", kid["points"] == 25, str(kid["points"]))

print("\n--- parent refunds a purchase ---")
t = token(parent, "/parent/approvals")
parent.post(f"/parent/approvals/redemption/{red['_id']}",
            data={"_csrf": t, "decision": "reject"}, follow_redirects=True)
with app.app_context():
    db = get_db()
    kid = db.users.find_one({"_id": kid["_id"]})
    stock = db.rewards.find_one({"_id": reward["_id"]})["stock"]
check("refund returns the points", kid["points"] == 55, str(kid["points"]))
check("refund restores stock", stock == 1, str(stock))

t = token(parent, "/parent/approvals")
r = parent.post(f"/parent/approvals/redemption/{red['_id']}",
                data={"_csrf": t, "decision": "approve"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("a decided request can't be decided twice", kid["points"] == 55, str(kid["points"]))

print("\n--- remaining pages render ---")
for path in ["/me/", "/me/shop", "/me/stuff"]:
    check(f"kid page {path}", kidcli.get(path).status_code == 200)
for path in ["/parent/", "/parent/approvals", "/parent/rewards", "/parent/quests",
             "/parent/family", f"/parent/kid/{kid_id}"]:
    check(f"parent page {path}", parent.get(path).status_code == 200)
check("/who renders", app.test_client().get("/who").status_code == 200)
check("/healthz ok", app.test_client().get("/healthz").status_code == 200)
check("404 page renders", app.test_client().get("/nope").status_code == 404)

print("\n--- grown-up account: own details ---")
t = token(parent, "/parent/account")
parent.post("/parent/account/profile", data={
    "_csrf": t, "name": "Matt H", "email": "matt.new@example.com",
    "avatar": "\U0001f98a"}, follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"role": "parent", "name": "Matt H"})
check("name, email and icon all saved",
      me and me["email"] == "matt.new@example.com" and me["avatar"] == "\U0001f98a")

t = token(parent, "/parent/account")
r = parent.post("/parent/account/profile", data={
    "_csrf": t, "name": "Matt H", "email": "not-an-email"}, follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"_id": me["_id"]})
check("a malformed email is rejected", me["email"] == "matt.new@example.com")

print("\n--- grown-up account: password ---")
t = token(parent, "/parent/account")
parent.post("/parent/account/password", data={
    "_csrf": t, "current_password": "wrong-one",
    "new_password": "brandnewpass", "confirm_password": "brandnewpass"},
    follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"_id": me["_id"]})
check("wrong current password leaves it unchanged", check_password(me, "password123"))

t = token(parent, "/parent/account")
parent.post("/parent/account/password", data={
    "_csrf": t, "current_password": "password123",
    "new_password": "brandnewpass", "confirm_password": "mismatch"},
    follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"_id": me["_id"]})
check("mismatched confirmation is refused", check_password(me, "password123"))

t = token(parent, "/parent/account")
parent.post("/parent/account/password", data={
    "_csrf": t, "current_password": "password123",
    "new_password": "brandnewpass", "confirm_password": "brandnewpass"},
    follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"_id": me["_id"]})
check("correct current password changes it", check_password(me, "brandnewpass"))

fresh = app.test_client()
t = token(fresh, "/login")
r = fresh.post("/login", data={"_csrf": t, "email": "matt.new@example.com",
                               "password": "brandnewpass"}, follow_redirects=True)
check("can log in with the new password", "Award points" in r.get_data(as_text=True))

print("\n--- resetting the other grown-up's password ---")
t = token(parent, "/parent/family")
parent.post("/parent/family/parents", data={
    "_csrf": t, "name": "Partner", "email": "partner@example.com",
    "password": "partnerpass"}, follow_redirects=True)
with app.app_context():
    other = get_db().users.find_one({"email": "partner@example.com"})
check("second grown-up added", other is not None)

t = token(parent, "/parent/family")
parent.post(f"/parent/family/parents/{other['_id']}/password", data={
    "_csrf": t, "new_password": "resetbyme1", "your_password": "wrong"},
    follow_redirects=True)
with app.app_context():
    other = get_db().users.find_one({"_id": other["_id"]})
check("reset refused without your own password", check_password(other, "partnerpass"))

t = token(parent, "/parent/family")
parent.post(f"/parent/family/parents/{other['_id']}/password", data={
    "_csrf": t, "new_password": "resetbyme1", "your_password": "brandnewpass"},
    follow_redirects=True)
with app.app_context():
    other = get_db().users.find_one({"_id": other["_id"]})
check("reset works when you confirm with yours", check_password(other, "resetbyme1"))

t = token(parent, "/parent/account")
r = parent.post("/parent/account/profile", data={
    "_csrf": t, "name": "Matt H", "email": "partner@example.com"},
    follow_redirects=True)
with app.app_context():
    me = get_db().users.find_one({"_id": me["_id"]})
check("can't take an email another account uses",
      me["email"] == "matt.new@example.com")

print("\n--- a kid can't reach the account pages ---")
check("kid blocked from /parent/account",
      kidcli.get("/parent/account", follow_redirects=False).status_code in (301, 302))

print("\n--- child picks a theme ---")
t = token(kidcli, "/me/theme")
kidcli.post("/me/theme", data={"_csrf": t, "theme": "ocean"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("theme saved", kid.get("theme") == "ocean", str(kid.get("theme")))
check("accent mirrored onto colour so grown-up views match",
      kid.get("color") == "#0ea5e9", str(kid.get("color")))
check("theme reaches the page", 'data-theme="ocean"' in kidcli.get("/me/").get_data(as_text=True))

t = token(kidcli, "/me/theme")
kidcli.post("/me/theme", data={"_csrf": t, "theme": "not-a-theme"}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("a bogus theme is refused", kid.get("theme") == "ocean")

print("\n--- child saves up for a chosen reward ---")
t = token(parent, "/parent/rewards")
parent.post("/parent/rewards", data={"_csrf": t, "title": "Big Telescope", "emoji": "\U0001f52d",
                                     "cost": "9000", "stock_mode": "unlimited"},
            follow_redirects=True)
with app.app_context():
    telescope = get_db().rewards.find_one({"title": "Big Telescope"})

html = kidcli.get("/me/").get_data(as_text=True)
check("with no goal set, home shows the cheapest unaffordable reward",
      "Next reward" in html and "Big Telescope" not in html)

t = token(kidcli, "/me/shop")
kidcli.post(f"/me/goal/{telescope['_id']}", data={"_csrf": t}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("goal stored on the child", kid.get("goal_reward_id") == telescope["_id"])
html = kidcli.get("/me/").get_data(as_text=True)
check("home now tracks the chosen reward", "Saving for" in html and "Big Telescope" in html)

t = token(kidcli, "/me/shop")
kidcli.post("/me/goal/clear", data={"_csrf": t}, follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("goal cleared", kid.get("goal_reward_id") is None)

t = token(kidcli, "/me/shop")
kidcli.post(f"/me/goal/{telescope['_id']}", data={"_csrf": t}, follow_redirects=True)
t = token(parent, "/parent/rewards")
parent.post(f"/parent/rewards/{telescope['_id']}", data={"_csrf": t, "action": "delete"},
            follow_redirects=True)
with app.app_context():
    kid = get_db().users.find_one({"_id": kid["_id"]})
check("deleting a reward stops anyone saving for a ghost",
      kid.get("goal_reward_id") is None)

print("\n--- stock that replenishes ---")
t = token(parent, "/parent/family")
parent.post("/parent/family/kids", data={"_csrf": t, "name": "Sibling", "avatar": "\U0001f43c",
                                         "color": "#28c8f5", "points": "500"},
            follow_redirects=True)
with app.app_context():
    db = get_db()
    sibling = db.users.find_one({"name": "Sibling"})
sibcli = app.test_client()
sibcli.get(f"/hi/{sibling['_id']}")     # no PIN, straight in

t = token(parent, "/parent/")
parent.post("/parent/award", data={"_csrf": t, "kid_id": str(kid["_id"]), "amount": "500",
                                   "reason": "stock test"}, follow_redirects=True)

t = token(parent, "/parent/rewards")
parent.post("/parent/rewards", data={"_csrf": t, "title": "Screen Time", "emoji": "\U0001f4f1",
                                     "cost": "5", "stock_mode": "periodic", "stock_limit": "2",
                                     "stock_period": "daily", "stock_scope": "child"},
            follow_redirects=True)
parent.post("/parent/rewards", data={"_csrf": t, "title": "Family Film", "emoji": "\U0001f37f",
                                     "cost": "5", "stock_mode": "periodic", "stock_limit": "1",
                                     "stock_period": "weekly", "stock_scope": "family"},
            follow_redirects=True)
with app.app_context():
    db = get_db()
    screen = db.rewards.find_one({"title": "Screen Time"})
    film = db.rewards.find_one({"title": "Family Film"})
check("periodic reward stored", screen and screen["stock_mode"] == "periodic"
      and screen["stock_limit"] == 2 and screen["stock_period"] == "daily")

def buy(client, reward):
    tok = token(client, "/me/shop")
    return client.post(f"/me/shop/{reward['_id']}/buy", data={"_csrf": tok},
                       follow_redirects=True).get_data(as_text=True)

buy(kidcli, screen); buy(kidcli, screen)
with app.app_context():
    n = get_db().redemptions.count_documents({"reward_id": screen["_id"], "kid_id": kid["_id"]})
check("both of the daily allowance can be bought", n == 2, str(n))

buy(kidcli, screen)
with app.app_context():
    n = get_db().redemptions.count_documents({"reward_id": screen["_id"], "kid_id": kid["_id"]})
check("a third is refused once the allowance is gone", n == 2, str(n))

buy(sibcli, screen)
with app.app_context():
    n = get_db().redemptions.count_documents({"reward_id": screen["_id"], "kid_id": sibling["_id"]})
check("per-child allowance is separate for a sibling", n == 1, str(n))

buy(kidcli, film)
buy(sibcli, film)
with app.app_context():
    n = get_db().redemptions.count_documents({"reward_id": film["_id"]})
check("a whole-family allowance is shared, not per child", n == 1, str(n))

with app.app_context():
    db = get_db()
    before = db.users.find_one({"_id": kid["_id"]})["points"]
    red = db.redemptions.find_one({"reward_id": screen["_id"], "kid_id": kid["_id"],
                                   "status": "pending"})
t = token(parent, "/parent/approvals")
parent.post(f"/parent/approvals/redemption/{red['_id']}",
            data={"_csrf": t, "decision": "reject"}, follow_redirects=True)
with app.app_context():
    db = get_db()
    after = db.users.find_one({"_id": kid["_id"]})["points"]
check("rejecting a periodic purchase refunds the points", after == before + 5,
      f"{before} -> {after}")
buy(kidcli, screen)
with app.app_context():
    n = get_db().redemptions.count_documents({"reward_id": screen["_id"], "kid_id": kid["_id"],
                                              "status": {"$in": ["pending", "approved"]}})
check("...and frees the slot back up", n == 2, str(n))

print("\n--- remember me ---")
rc = app.test_client()
t = token(rc, "/login")
rc.post("/login", data={"_csrf": t, "email": "matt.new@example.com",
                        "password": "brandnewpass", "remember": "1"}, follow_redirects=True)
cookie = rc.get_cookie("questly_email")
check("ticking remember stores the email in a cookie",
      cookie is not None and cookie.value == "matt.new@example.com",
      str(cookie.value if cookie else None))
check("the password is never stored",
      not any("brandnewpass" in (c.value or "") for c in [rc.get_cookie("questly_email")] if c))

page = rc.get("/login").get_data(as_text=True)
check("the login form is prefilled next time", 'value="matt.new@example.com"' in page)

t = token(rc, "/login")
rc.post("/forget-me", data={"_csrf": t}, follow_redirects=True)
check("forget-me clears it", rc.get_cookie("questly_email") is None)

plain = app.test_client()
t = token(plain, "/login")
plain.post("/login", data={"_csrf": t, "email": "matt.new@example.com",
                           "password": "brandnewpass"}, follow_redirects=True)
check("leaving remember unticked logs you in but stores nothing",
      plain.get("/parent/").status_code == 200 and plain.get_cookie("questly_email") is None)

print("\n--- logout ---")
t = token(kidcli, "/me/")
r = kidcli.post("/logout", data={"_csrf": t}, follow_redirects=False)
check("logout redirects to who's here", r.headers.get("Location", "").endswith("/who"))
check("session really gone", kidcli.get("/me/", follow_redirects=False).status_code in (301, 302))

print("\n" + ("=" * 46))
print(f"FAILED: {len(FAILS)}" if FAILS else "ALL CHECKS PASSED")
for f in FAILS:
    print("  -", f)
sys.exit(1 if FAILS else 0)
