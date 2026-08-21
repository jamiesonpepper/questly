<p align="center">
  <img src="app/static/icons/icon-192.png" alt="" width="112" height="112">
</p>

<h1 align="center">Questly</h1>

<p align="center">
  <strong>A family points-and-rewards app.</strong><br>
  Grown-ups award points for quests and good behaviour.<br>
  Kids spend those points in a shop of rewards you control.
</p>

<p align="center">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.1-000?logo=flask&logoColor=white">
  <img alt="MongoDB" src="https://img.shields.io/badge/MongoDB-5%2B-13aa52?logo=mongodb&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-compose-2496ed?logo=docker&logoColor=white">
</p>

> [!NOTE]
> ### Built with AI
>
> Every line of this project — the application code, the stylesheet, the icons
> and this README — was written by **Claude** (Anthropic's Claude Opus 5)
> running in Claude Code, to a human's direction. Every commit carries a
> `Co-Authored-By: Claude` trailer, so the history is honest about it.
>
> It is not untested. `tests/smoke_test.py` walks every flow end to end against
> a real MongoDB — awarding, spending, approving, refunding, PIN login, account
> changes — and every screen was driven in a browser during development.
>
> It has **not** had a third-party security audit, and it hasn't run anywhere
> long enough to call it battle-tested. It is a family app intended for a
> trusted home network. Read the code before running it on anything you care
> about, as you would with any code you find on the internet.

---

Self-hosted, no accounts with anyone else, no ads, no subscriptions. It runs on
a spare machine or a NAS and is used from any phone, tablet or laptop on the
same network. The layout is mobile-first and installs to a home screen as a
web app.

- **Two sides.** Grown-ups log in with an email and password. Kids tap their
  avatar and type a 4–6 digit PIN — or no PIN at all for the youngest.
- **Quests** — recurring jobs worth points. A kid taps **Done!**, a grown-up
  approves, the points land.
- **A shop** you stock yourself, with prices, icons and optional limited stock.
- **A full ledger.** Every point in or out is recorded with a running balance.

---

## Requirements

Docker Engine with the Compose plugin (`docker compose`). Nothing else — Python
and MongoDB both run inside containers. Works on x86-64 and ARM64.

## Quick start

```bash
git clone https://github.com/mahansford/questly.git && cd questly
```

```bash
cp .env.example .env
```

Set a real `SECRET_KEY` in `.env`:

```bash
sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env && rm -f .env.bak
```

```bash
docker compose up --build -d
```

Open **http://localhost:37000**. The first visit asks you to create a grown-up
account, then walks you to the Family page to add your kids.

### Optional: start with example content

Fills the shop and quest board with sensible starter items (and, if the app is
completely empty, two demo kids):

```bash
docker compose exec web flask --app wsgi:app seed-demo
```

---

## How it works

| Thing | What happens |
| --- | --- |
| **Award points** | Quick `+10 / +25 / +50 / +100` buttons on each kid's card, or any custom amount, with an optional reason. Points can be taken away too. |
| **Quests** | Recurring jobs (daily, weekly or one-off) worth a set number of points, assignable to specific kids or everyone. A kid taps **Done!**, you approve, the points land. |
| **Shop** | Rewards you create, each with a point cost, an icon, a description and optional limited stock. |
| **Buying** | Points are deducted the moment a kid buys, and the reward queues up for you to hand over. Turning a request down refunds the points automatically. |
| **Approvals** | One page listing every quest and purchase waiting on you, with a count badge in the nav. |
| **Accounts** | Each grown-up can change their own name, login email, icon and password. |
| **Locked out?** | Either grown-up can set a new password for the other, confirmed with their own password. There is no email recovery, so this is the way back in. |

### The rules it enforces

- A kid can never go below zero points, and can't overspend by double-tapping
  Buy — the deduction is a conditional atomic update.
- Two kids racing for the last limited-stock item can't both win it, for the
  same reason.
- A daily quest can be claimed once per calendar day and a weekly one once per
  ISO week, both in the timezone set by `TZ`.
- Rejecting a quest claim lets the kid try again in the same period.
- Every mutation is CSRF-protected, and kids can't reach grown-up pages.

---

## Configuration

Everything is set in `.env`, which Docker Compose reads:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `37000` | Host port the app is served on |
| `SECRET_KEY` | — | **Set this.** Signs session cookies |
| `MONGO_DB` | `questly` | Database name |
| `MONGO_URI` | bundled container | Only needed for an external MongoDB — see below |
| `TZ` | `Europe/London` | Drives dates and daily/weekly quest resets |

`.env` is gitignored, so secrets stay out of version control.

---

## Using a MongoDB you already run

The compose file ships a MongoDB container for convenience, but the app is
happy talking to any MongoDB 5+ instance. Set `MONGO_URI` in `.env` and start
only the web service:

```bash
docker compose up -d --no-deps web
```

`--no-deps` is what stops Compose from also starting the bundled `mongo`
service. Without it you get two databases running and only one in use.

MongoDB has to be reachable from *inside* the web container, which means one of:

- **Same docker network** — put both containers on the same *user-defined*
  network and address it by container name (`mongodb://my-mongodb:27017/`).
  Docker's default `bridge` network does not resolve container names, so a
  custom network is required.
- **Via the host** — publish MongoDB's port and point at the host's LAN IP
  (`mongodb://192.168.1.50:27017/`).

With authentication enabled, include the credentials and the auth database:
`mongodb://user:pass@host:27017/?authSource=admin`.

The app creates its own collections and indexes on first use, so an empty
database is all it needs. It only ever touches the database named by
`MONGO_DB`, so sharing an instance with other apps is fine.

> **Running on a NAS?** Docker *named volumes* often live inside a fixed-size
> virtual disk that your normal share backups don't cover. Either bind-mount
> the database to real storage or point `MONGO_URI` at a MongoDB container you
> manage yourself.

---

## On your home network

Once it's running, the app is reachable from other devices at
`http://<server-ip>:37000` — handy for kids on tablets and phones. Find the
address with `hostname -I` (Linux) or `ipconfig getifaddr en0` (macOS). A DHCP
reservation in your router keeps it from changing.

### Install it to a home screen

Open that address on the device and choose **Add to Home Screen** (Share menu
on iOS, browser menu on Android). It launches full-screen with its own icon and
no browser chrome, which is how it's meant to be used.

> Questly speaks plain HTTP and assumes a trusted home network. Don't expose it
> to the internet without putting HTTPS and, ideally, a VPN in front of it.

---

## Everyday commands

```bash
docker compose up -d          # start
docker compose down           # stop (data is kept)
docker compose logs -f web    # tail the app logs
docker compose up --build -d  # rebuild after changing the code
```

Add a grown-up from the command line — useful if everyone is locked out:

```bash
docker compose exec web flask --app wsgi:app create-parent
```

### Backing up

All data lives in the `mongo-data` Docker volume.

```bash
docker compose exec -T mongo mongodump --db questly --archive --gzip > questly-backup.gz
```

Restore:

```bash
docker compose exec -T mongo mongorestore --archive --gzip --drop < questly-backup.gz
```

### Starting completely over

```bash
docker compose down -v        # -v also deletes the database volume
```

---

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=dev MONGO_URI=mongodb://localhost:27017/
flask --app wsgi:app run --debug --port 8000
```

You'll need MongoDB listening on `localhost:27017`.

### Tests

An end-to-end smoke test walks every flow — awarding, spending, approving,
refunding, PIN login, account changes, the lot — against a throwaway database:

```bash
docker compose exec -e MONGO_DB=questly_test web python tests/smoke_test.py
```

It refuses to run unless the database name ends in `_test`, so it can't touch
real data.

### Regenerating the icons

Every icon comes from one geometric spec, so the SVG and the PNGs can't drift
apart. Edit `tools/make_icons.py` and run:

```bash
pip install pillow && python tools/make_icons.py
```

---

## Project layout

```
app/
  __init__.py      app factory, CSRF, template filters
  db.py            Mongo connection + indexes
  models.py        all domain logic (points ledger, shop, quests, accounts)
  cli.py           flask CLI commands (seed-demo, create-parent)
  views/
    public.py      landing, who's-here, health check
    auth.py        first-run setup, grown-up login, kid PIN login
    kid.py         kid home, shop, history
    parent.py      dashboard, awards, approvals, shop & quests, family, account
  templates/       Jinja templates
  static/
    css/           one stylesheet
    js/            a little vanilla JS — no build step, no dependencies
    icons/         app icons, generated
    manifest.webmanifest
tools/
  make_icons.py    regenerates every icon from one spec
tests/
  smoke_test.py    end-to-end walk through every flow
```

### Collections

| Collection | Holds |
| --- | --- |
| `users` | grown-ups and kids (kids carry their cached balance) |
| `transactions` | the point ledger — every change, with balance after |
| `rewards` | shop items |
| `redemptions` | purchases and their approval state |
| `quests` | the quest board |
| `quest_claims` | a kid's claim on a quest for one period |

The app has no JavaScript build step and no frontend dependencies — it's Jinja
templates, one stylesheet and one small script.
