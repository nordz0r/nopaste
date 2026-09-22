# Telegram preview and Instant View

Nopaste exposes two different representations of a paste:

- `/paste/<id>` is an HTML page with Open Graph metadata and a stable semantic
  `article#instant-view-article` source for Telegram. Markdown pastes are
  rendered into escaped semantic HTML in that source; Telegram does not need
  to execute the browser's JavaScript Markdown renderer.
- `/raw/<id>` (and `/paste/<id>/raw`) is the exact paste body as
  `text/plain`, intended for curl, CI, and editors.

## Why Instant View does not appear from a bare paste URL

Sharing `https://paste.goldfinches.ru/paste/<id>` is **necessary but not
sufficient**. Telegram shows Instant View only when:

1. a template for that domain/`?path` is **publicly approved** by Telegram, or
2. the shared link is a private Instant View URL
   `https://t.me/iv?url=<canonical>&rhash=<template-rhash>` built from a
   template you own in the Instant View Editor.

Canonical markup alone never unlocks IV. Nopaste already serves TelegramBot a
minimal SSR preview (`paste_preview.html`) with `article#instant-view-article`,
Open Graph `article` tags, HTTPS, and `robots.txt` allow rules for
`TelegramBot`. Those pieces are ready; the missing switch is the Telegram-side
template (and optionally `TELEGRAM_IV_RHASH` below).

## Instant View template (required — Андрей)

Create a template for `paste.goldfinches.ru` in the
[Telegram Instant View Editor](https://instantview.telegram.org/) and enter:

```text
~version: "2.1"

?path: /paste/[A-Za-z0-9_-]+
title: //article[@id="instant-view-article"]/h1
body: //article[@id="instant-view-article"]
```

Then:

1. Open a real paste URL in the editor and confirm the right-hand IV pane
   renders title + body with no errors.
2. Use **View in Telegram** and copy the `rhash=` value from the
   `t.me/iv?url=…&rhash=…` link.
3. Set production env `TELEGRAM_IV_RHASH=<that value>` and redeploy.
4. Optional for *all* users (not only shared `t.me/iv` links): submit the
   template for Telegram team approval so bare `/paste/<id>` URLs also show
   the Instant View button.
5. If an old URL was shared before the template existed, refresh preview cache
   via [@WebpageBot](https://t.me/WebpageBot) or share a fresh paste.

### Go / no-go

| Check | Owner | Status needed for IV |
| --- | --- | --- |
| Prod share uses canonical `/paste/<id>` (not gldf.ru) | nopaste (#15) | done |
| TelegramBot gets SSR `article#instant-view-article` | nopaste | done |
| IV template saved + verified in editor | Андрей | **required** |
| `TELEGRAM_IV_RHASH` set in prod | Андрей / deploy | **required** for share→IV now |
| Public template approval | Telegram team | optional (bare URL IV) |

## Telegram share button

The in-app Telegram share button (`t.me/share`) never puts a SHRINK short link
(`gldf.ru`) into the shared target.

- Without `TELEGRAM_IV_RHASH`: shares the **canonical** paste URL
  (`/paste/<id>`). Instant View appears only after a public domain template.
- With `TELEGRAM_IV_RHASH`: shares
  `https://t.me/iv?url=<canonical>&rhash=<rhash>` so recipients open Instant
  View using your template immediately.

Copy-link and the short-URL / slug UI still prefer the short link when SHRINK
is configured — only the Telegram share target is forced to canonical / IV.

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
