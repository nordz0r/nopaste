# Telegram preview and Instant View

Nopaste exposes two different representations of a paste:

- `/paste/<id>` is an HTML page with Open Graph metadata and a stable semantic
  `article#instant-view-article` source for Telegram. Markdown pastes are
  rendered into escaped semantic HTML in that source; Telegram does not need
  to execute the browser's JavaScript Markdown renderer.
- `/raw/<id>` (and `/paste/<id>/raw`) is the exact paste body as
  `text/plain`, intended for curl, CI, and editors.

## Why Instant View does not appear from a bare paste URL

Sharing a paste URL is **necessary but not sufficient**. Telegram shows Instant
View only when:

1. a template for that domain/`?path` is **publicly approved** by Telegram, or
2. the shared link is a private Instant View URL
   `https://t.me/iv?url=<paste-url>&rhash=<template-rhash>` built from a
   template you own in the Instant View Editor.

Canonical markup alone never unlocks IV. Nopaste already serves TelegramBot a
minimal SSR preview (`paste_preview.html`) with `article#instant-view-article`,
Open Graph `article` tags, HTTPS, and `robots.txt` allow rules for
`TelegramBot`. Those pieces are ready; the missing switch is the Telegram-side
template (and optionally `TELEGRAM_IV_RHASH` below).

## Telegram-reachable host (`TELEGRAM_PUBLIC_BASE_URL`)

`PUBLIC_BASE_URL` drives normal browser canonical / Open Graph (for example
`https://paste.goldfinches.ru`). Telegram's WebpageBot may be unable to fetch
that host (egress / IP filtering).

Set `TELEGRAM_PUBLIC_BASE_URL` to a Cloudflare (or other) front Telegram **can**
reach, for example `https://paste.bynord.dev`, pointing at the same nopaste.
Then:

- the in-app Telegram Share button and `t.me/iv?url=` use that origin;
- TelegramBot / Instant View Editor SSR rewrite `og:url` / canonical to that
  origin;
- ordinary browser UI on goldfinches keeps `PUBLIC_BASE_URL` unchanged.

Empty `TELEGRAM_PUBLIC_BASE_URL` falls back to `PUBLIC_BASE_URL` / request host.

## Instant View template (required — Андрей)

Create a template for the **Telegram-facing** host (the one in Share /
`TELEGRAM_PUBLIC_BASE_URL`, e.g. `paste.bynord.dev`) in the
[Telegram Instant View Editor](https://instantview.telegram.org/) and enter:

```text
~version: "2.1"

?path: /paste/[A-Za-z0-9_-]+
title: //article[@id="instant-view-article"]/h1
body: //article[@id="instant-view-article"]
```

Then:

1. Open a real paste URL **on that host** in the editor and confirm the
   right-hand IV pane renders title + body with no errors.
2. Use **View in Telegram** and copy the `rhash=` value from the
   `t.me/iv?url=…&rhash=…` link.
3. Set production env `TELEGRAM_IV_RHASH=<that value>` and redeploy.
4. Optional for *all* users (not only shared `t.me/iv` links): submit the
   template for Telegram team approval so bare `/paste/<id>` URLs also show
   the Instant View button.
5. If you previously used an rhash for another domain (e.g. goldfinches),
   create/verify a template for the new host — rhash is per template/domain.
6. If an old URL was shared before the template existed, refresh preview cache
   via [@WebpageBot](https://t.me/WebpageBot) or share a fresh paste.

### Go / no-go

| Check | Owner | Status needed for IV |
| --- | --- | --- |
| Prod share uses paste URL (not gldf.ru) | nopaste (#15) | done |
| `TELEGRAM_PUBLIC_BASE_URL` reachable by Telegram | deploy | **required** if primary host is blocked |
| TelegramBot gets SSR `article#instant-view-article` | nopaste | done |
| IV template saved + verified for Telegram-facing host | Андрей | **required** |
| `TELEGRAM_IV_RHASH` set in prod (for that host) | Андрей / deploy | **required** for share→IV now |
| Public template approval | Telegram team | optional (bare URL IV) |

## Telegram share button

The in-app Telegram share button (`t.me/share`) never puts a SHRINK short link
(`gldf.ru`) into the shared target.

- Without `TELEGRAM_IV_RHASH`: shares the Telegram-facing paste URL
  (`TELEGRAM_PUBLIC_BASE_URL` or canonical `/paste/<id>`). Instant View appears
  only after a public domain template.
- With `TELEGRAM_IV_RHASH`: shares
  `https://t.me/iv?url=<telegram-facing-paste>&rhash=<rhash>` so recipients
  open Instant View using your template immediately.

Copy-link and the short-URL / slug UI still prefer the short link when SHRINK
is configured — only the Telegram share target is forced to paste / IV.

## Preview privacy

The Telegram/social preview description contains a normalized excerpt of the
first 200 characters of the paste. Do not put passwords, tokens, or other
secrets at the start of a paste intended for sharing.

## Curl

Use the explicit raw endpoint (it is deterministic and recommended for curl,
CI, and editors):

```bash
curl -fsSL "https://paste.goldfinches.ru/raw/<paste_id>"
```
