# Changelog

All notable changes to Questly are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.1] — 2026-08-21

No changes to the app itself — this release exists to publish container images
and list Questly on Unraid.

### Added

- Multi-architecture container images (`linux/amd64`, `linux/arm64`) published
  automatically on every tag to GitHub Container Registry, and to Docker Hub
  once a token is configured. The workflow smoke-tests the published image
  before finishing.
- `ca_profile.xml` and `templates/questly.xml` so Questly can be listed in
  Unraid Community Applications.
- Docs and screenshots are now excluded from the image, trimming its size.

## [1.0.0] — 2026-08-21

First release.

### Added

**Kids**

- Sign in by tapping your face on the front page, then a 4–6 digit PIN on a
  large keypad — or no PIN at all, for children too young to manage one.
- A home screen with a progress bar counting down to the next reward you can't
  yet afford, today's quests, and your recent points.
- A quest list with **Done!** buttons that send a claim to a grown-up.
- A shop separating what you can buy now from how many points short you are of
  the rest.
- A history page with lifetime totals, rewards won and a running balance.
- Confetti and a message when something lands.

**Grown-ups**

- Quick `+10 / +25 / +50 / +100` award buttons per child, plus custom amounts
  and take-aways, each with an optional reason.
- A quest board: daily, weekly or one-off quests worth a set number of points,
  assigned to specific children or to everyone.
- A shop editor: title, icon, description, cost and optional limited stock,
  with items hideable without deleting them.
- One approvals page for every purchase and quest claim awaiting a decision,
  with a count badge in the navigation.
- Family management — add, edit and remove children, set or clear their PINs,
  and add or remove other grown-ups.
- An account page for your own name, login email, icon and password. Either
  grown-up can reset the other's password, confirmed with their own.

**Behaviour**

- Balances can never go negative, and repeated taps on **Buy** cannot overdraw
  one — the deduction is a conditional atomic update.
- Two children racing for the last limited-stock item cannot both win it.
- Daily quests can be claimed once per calendar day and weekly ones once per
  ISO week, in the configured timezone.
- Rejecting a purchase refunds the points and restores the stock; rejecting a
  quest claim lets the child try again in the same period.
- Every point movement is written to a ledger with the balance after it.

**Operations**

- Docker Compose stack with a bundled MongoDB, or point `MONGO_URI` at one you
  run yourself and start only the web service.
- First-run setup wizard, plus `seed-demo` and `create-parent` CLI commands.
- A `/healthz` endpoint wired to the container health check.
- `tests/smoke_test.py` — 53 end-to-end checks against a real MongoDB, guarded
  so it can only run against a database named `*_test`.

**Interface**

- Installable to a phone or tablet home screen, with a web app manifest and a
  full icon set generated from a single spec by `tools/make_icons.py`.
- Safe-area padding throughout, so nothing hides behind an iOS status bar or
  home indicator when running full-screen.
- CSRF protection on every mutation, and route guards keeping children out of
  grown-up pages.

[Unreleased]: https://github.com/mahansford/questly/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/mahansford/questly/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/mahansford/questly/releases/tag/v1.0.0
