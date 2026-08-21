# ⭐ Questly

A family points-and-rewards app. Grown-ups award points for quests and good
behaviour; kids spend those points in a shop of rewards you control.

Built with Flask + MongoDB, runs in Docker.

---

## Quick start

Already done on this machine — the stack is built and running, and `.env`
has a freshly generated `SECRET_KEY`. Just open **http://localhost:8080**.

Starting from scratch elsewhere:

```bash
cp .env.example .env          # then set SECRET_KEY
docker compose up --build -d
```

The first visit asks you to create a grown-up account, then walks you to the
Family page where you add your kids.

### Optional: start with example content

Fills the shop and quest board with sensible starter items (and, if the app is
completely empty, two demo kids):

```bash
docker compose exec web flask --app wsgi:app seed-demo
```

---

## How it works

**Grown-ups** log in with an email and password. **Kids** tap their avatar on
the front page and type a 4–6 digit PIN — or no PIN at all for younger kids.

| Thing | What happens |
| --- | --- |
| **Award points** | Quick `+1 / +5 / +10 / +25` buttons on each kid's card, or any custom amount, with an optional reason. Points can be taken away too. |
| **Quests** | Recurring jobs (daily, weekly or one-off) worth a set number of points. A kid taps **Done!**, you approve, the points land. |
| **Shop** | Rewards you create, each with a point cost, an emoji and optional limited stock. |
| **Buying** | Points are deducted the moment a kid buys, and the reward queues up for you to hand over. Turning a request down refunds the points automatically. |
| **Approvals** | One page listing every quest and purchase waiting on you. The nav shows a count badge. |

Every point movement is written to a ledger, so each kid gets a full history
with a running balance.

### Notes on the rules

- A kid can never go below zero points, and can't overspend by double-tapping
  Buy — the deduction is a conditional atomic update.
- A daily quest can be claimed once per calendar day, a weekly one once per ISO
  week, both in the timezone set by `TZ`.
- Rejecting a quest claim lets the kid try again in the same period.

---

## Configuration

Everything is set in `.env` (read by Docker Compose):

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8080` | Host port the app is served on |
| `SECRET_KEY` | — | **Change this.** Signs session cookies |
| `MONGO_DB` | `questly` | Database name |
| `TZ` | `Europe/London` | Drives dates and daily/weekly quest resets |

Generate a key with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running it on your home network

By default the app is reachable from other devices on your LAN at
**http://10.11.10.33:8080** — handy for kids on tablets or phones. The layout is
mobile-first, so it works well saved to a home screen.

(That address is this Mac's current IP; it can change when your router hands
out a new lease. A DHCP reservation in your router settings pins it.)

It speaks plain HTTP and is meant for a trusted home network. Don't expose it
directly to the internet without putting HTTPS in front of it.

---

## Everyday commands

```bash
docker compose up -d          # start
docker compose down           # stop (data is kept)
docker compose logs -f web    # tail the app logs
docker compose up --build -d  # rebuild after changing the code
```

Add another grown-up from the command line:

```bash
docker compose exec web flask --app wsgi:app create-parent
```

### Backing up

All data lives in the `mongo-data` Docker volume.

```bash
docker compose exec mongo mongodump --db questly --archive=/tmp/questly.gz --gzip
docker compose cp mongo:/tmp/questly.gz ./questly-backup.gz
```

Restore:

```bash
docker compose cp ./questly-backup.gz mongo:/tmp/questly.gz
docker compose exec mongo mongorestore --archive=/tmp/questly.gz --gzip --drop
```

### Starting completely over

```bash
docker compose down -v        # -v also deletes the database volume
```

---

## Running without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=dev MONGO_URI=mongodb://localhost:27017/
flask --app wsgi:app run --debug --port 8000
```

You'll need MongoDB listening on `localhost:27017`.

---

## Checking everything still works

There's an end-to-end smoke test that walks every flow — awarding, spending,
approving, refunding, PIN login, the lot — against a throwaway database:

```bash
docker compose exec -e MONGO_DB=questly_test web python tests/smoke_test.py
```

It refuses to run unless the database name ends in `_test`, so it can't touch
your family's data.

---

## Project layout

```
app/
  __init__.py      app factory, CSRF, template filters
  db.py            Mongo connection + indexes
  models.py        all domain logic (points ledger, shop, quests)
  cli.py           flask CLI commands (seed-demo, create-parent)
  views/
    public.py      landing, who's-here, health check
    auth.py        setup, parent login, kid PIN login
    kid.py         kid home, shop, history
    parent.py      dashboard, awards, approvals, shop & quest admin
  templates/       Jinja templates
  static/          stylesheet and a little vanilla JS
tests/
  smoke_test.py    end-to-end walk through every flow
```

### Collections

| Collection | Holds |
| --- | --- |
| `users` | parents and kids (kids carry their cached balance) |
| `transactions` | the point ledger — every change, with balance after |
| `rewards` | shop items |
| `redemptions` | purchases and their approval state |
| `quests` | the quest board |
| `quest_claims` | a kid's claim on a quest for one period |
