# Changelog

All notable changes to this project will be documented in this file.

<!-- version list -->

## v1.13.1 (2026-08-12)

### Bug Fixes

- **highlighting**: Detect YAML instead of mislabeling as Markdown
  ([`12250ac`](https://github.com/nordz0r/nopaste/commit/12250acb4d85d4dfd1c1a6d3e2e975d2f7e09f8d))

### Code Style

- Format test_main with ruff
  ([`026e357`](https://github.com/nordz0r/nopaste/commit/026e357396ee758bb5ae5241980bf4b4373a5520))


## Unreleased

### Bug Fixes

- **highlighting**: Detect YAML configs (including `---` documents with `#` comments and `-` lists) instead of mislabeling them as Markdown/Diff

## v1.13.0 (2026-08-11)

### Features

- Increase paste id length to 8, add slug validation and in-app rate limit
  ([`63b03c2`](https://github.com/nordz0r/nopaste/commit/63b03c29765909fa516b033d73ff027f9cc8a3b3))


## v1.12.0 (2026-08-09)

### Chores

- Remove AGENTS.md and compose helper shell scripts
  ([`1c406fc`](https://github.com/nordz0r/nopaste/commit/1c406fc6fb74e159fc236f91af32143e5494cfa2))

### Features

- Disallow search engine indexing with robots.txt and noindex headers
  ([`3a391fc`](https://github.com/nordz0r/nopaste/commit/3a391fca2a01b2d52a8a80bb7017be02d99f9cb5))


## v1.11.0 (2026-08-06)

### Features

- **ui**: Slug as display name; changelog modal
  ([`709fa47`](https://github.com/nordz0r/nopaste/commit/709fa47f35cc1ac6fdce12f3dc79d6d341ae6623))


## v1.10.4 (2026-08-06)

### Bug Fixes

- **ui**: Stop clipping characters in short-url slug input
  ([`27ee819`](https://github.com/nordz0r/nopaste/commit/27ee8198f4f6f50b65b26b4b5195cbaccdc536f2))


## v1.10.3 (2026-08-06)

### Bug Fixes

- **docker**: Pin uv image ref for buildx COPY --from
  ([`ef8b4b9`](https://github.com/nordz0r/nopaste/commit/ef8b4b9ae258a9839e907543deec8356c9ea7e87))


## v1.10.2 (2026-08-06)

### Bug Fixes

- **docker**: Healthcheck without wget; upgrade deps and uv 0.12
  ([`910cb50`](https://github.com/nordz0r/nopaste/commit/910cb501e2a56801bc744c542670761272d9e39f))

### Chores

- Remove unused assets and slim static images
  ([`2e3ca67`](https://github.com/nordz0r/nopaste/commit/2e3ca67559a15ca55038884deb368213ab61ab8f))


## v1.10.1 (2026-08-06)

### Bug Fixes

- **storage**: Always ensure schema via create_all after alembic
  ([`e91b9f3`](https://github.com/nordz0r/nopaste/commit/e91b9f316a0232a0fb233bdf3ab05bbf2538de16))


## v1.10.0 (2026-08-06)

### Bug Fixes

- **paste**: Hide custom slug on create and restyle inline editor
  ([`c3bf74a`](https://github.com/nordz0r/nopaste/commit/c3bf74ac509bd8df94299f2d8a5cbbd9d4953596))

- **paste**: Restore short url placement and add edit tooltip
  ([`da743b3`](https://github.com/nordz0r/nopaste/commit/da743b349c95beb38f291ff9f586d4d6fed7a8d1))

### Features

- Multi-db storage, optional encryption, i18n and paste UX
  ([`9e01c4f`](https://github.com/nordz0r/nopaste/commit/9e01c4f5c54abc708b08a2bec1a0cfa4a3cfbf6d))

- **storage**: Support PostgreSQL for durable pastes
  ([`a00a05b`](https://github.com/nordz0r/nopaste/commit/a00a05bbb01424c3cbe56d592a1da98fdd99cc56))

- **ui**: Improve footer scroll behavior and expose changelog
  ([`b8c8a38`](https://github.com/nordz0r/nopaste/commit/b8c8a38c3dbb69ced3720ce9819957636f8601fa))


## v1.9.0 (2026-08-06)

### Chores

- Fix release formatting and lock version
  ([`604cd22`](https://github.com/nordz0r/nopaste/commit/604cd22693809aac39a9e225020afe2be226b81d))

### Code Style

- **format**: Apply ruff code formatting
  ([`13b4e87`](https://github.com/nordz0r/nopaste/commit/13b4e875aedfbf6f2ed5500998bb6a5f6fcdf943))

### Features

- **paste**: Support Ctrl+A text selection and editable short url slug
  ([`57628d5`](https://github.com/nordz0r/nopaste/commit/57628d52aa8924b6f09efa9797f2ba98716b276e))


## v1.8.0 (2026-08-04)

### Features

- Add raw paste endpoints
  ([`fde3013`](https://github.com/nordz0r/nopaste/commit/fde3013f4601482f3a78da78cf39d36895fd8195))


## v1.7.5 (2026-08-04)

### Bug Fixes

- **frontend**: Handle token object parameter in marked.js v1.7.4 code renderer
  ([`6ce15c7`](https://github.com/nordz0r/nopaste/commit/6ce15c7581c86b1d07d0b72c016ba3e514d42345))

### Code Style

- **header**: Change site-header positioning from sticky to relative
  ([`6c8e3fc`](https://github.com/nordz0r/nopaste/commit/6c8e3fcc398b65d09c6583ba916d157c949580b6))

- **header**: Hide header after scrolling past threshold
  ([`f090f16`](https://github.com/nordz0r/nopaste/commit/f090f168e2346e27c90c88a4189d0210abfefac8))


## v1.7.4 (2026-08-04)

### Bug Fixes

- **highlighting**: Autodetect valid JSON before Pygments fallback
  ([`da6d179`](https://github.com/nordz0r/nopaste/commit/da6d1799b7c8a6ae9cc85b42318e1e78777e9626))


## v1.7.3 (2026-08-03)

### Bug Fixes

- Refine light theme and markdown detection
  ([`2bc7353`](https://github.com/nordz0r/nopaste/commit/2bc735350b5d8edaeda2ae5432efd75358eebc81))


## v1.7.2 (2026-08-03)

### Bug Fixes

- Improve markdown detection for text containing inline backticks
  ([`b6d1423`](https://github.com/nordz0r/nopaste/commit/b6d1423095acac85ddceac0e8540782d51fc5e70))

### Code Style

- Darken light theme to a soft slate aesthetic
  ([`088abf0`](https://github.com/nordz0r/nopaste/commit/088abf05cab025b8dbdbec6b84c5d400f1033e4b))

- Replace bright white surfaces with muted grey tones
  ([`280e7f5`](https://github.com/nordz0r/nopaste/commit/280e7f5f685ab0f487d0327d74889bb6dfe4b7c1))


## v1.7.1 (2026-08-03)

### Bug Fixes

- Position footer in document flow and hide on scroll
  ([`ce3f8ec`](https://github.com/nordz0r/nopaste/commit/ce3f8ec0fb06f99c1a01d6f1ac4fbb842248aa81))

### Code Style

- Compact mobile borders and wrap long lines on small screens
  ([`4e4afb0`](https://github.com/nordz0r/nopaste/commit/4e4afb065806233905b111257d726ef9b68b8038))

- Support mobile safe area inset for footer
  ([`e74c747`](https://github.com/nordz0r/nopaste/commit/e74c747d7199ac7d9bc34dfda278ee3c2fa655eb))

### Documentation

- Add production deployment instructions
  ([`24c0dbf`](https://github.com/nordz0r/nopaste/commit/24c0dbf918ae4f96560ac1a303a689e623f1b48d))


## v1.7.0 (2026-08-03)

### Features

- Redesign light theme and animate footer on scroll
  ([`4577eef`](https://github.com/nordz0r/nopaste/commit/4577eef58c95a7a9fef29684b73fd9393132ee17))


## v1.6.2 (2026-08-03)

### Bug Fixes

- Eliminate false positives in Markdown detection for code and configs
  ([`ed72d3d`](https://github.com/nordz0r/nopaste/commit/ed72d3db51387d7ca50405c49d825ce305c3f595))


## v1.6.1 (2026-08-03)

### Bug Fixes

- Restrict auto-markdown detection to prevent false positives on code and scripts
  ([`b911bfc`](https://github.com/nordz0r/nopaste/commit/b911bfc3f823150a12baf36e0938fc4e57ab5ed9))

### Documentation

- Update CHANGELOG.md for v1.6.0 release
  ([`7ff25ec`](https://github.com/nordz0r/nopaste/commit/7ff25ec8d52c8f6bc29a8969053855c2aefecc99))

### Refactoring

- Remove tab buttons and make Markdown badge clickable for raw view
  ([`23f4191`](https://github.com/nordz0r/nopaste/commit/23f419181862add5d2fea03fb4c34cf334185113))


## v1.6.0 (2026-08-03)

### Features

- Add automatic Markdown detection, document rendering, and interactive Mermaid diagram support (`marked.js`, `mermaid.js`)
  ([`a8cfb34`](https://github.com/nordz0r/nopaste/commit/a8cfb3474a3934190d41e6e72a50c9c115d20bfb))
- Overhaul Light Theme design system (Studio Light palette, glass header, custom Pygments syntax tokens, gradient buttons)


## v1.5.1 (2026-08-03)

### Bug Fixes

- Improve light theme typography and code block colors
  ([`213d5a8`](https://github.com/nordz0r/nopaste/commit/213d5a8493462e9e2fe8162754d8cfc34fb123a0))


## v1.5.0 (2026-08-03)

### Features

- Add automatic syntax highlighting
  ([`729bc7e`](https://github.com/nordz0r/nopaste/commit/729bc7e22340bf7c42bfa869ed90e067b9d36050))

- Add light design template and interactive theme switcher
  ([`9c3415e`](https://github.com/nordz0r/nopaste/commit/9c3415e6690dbe9ec584db43e394d00f222c32b4))


## v1.4.0 (2026-06-18)

### Bug Fixes

- Delete old agents
  ([`4638e55`](https://github.com/nordz0r/nopaste/commit/4638e5524a6c15a6d73c14b74c66992673584e56))

### Features

- Add templates
  ([`435a832`](https://github.com/nordz0r/nopaste/commit/435a8324805255de4b2976c6505601c7cfd860fa))

- Expose design_name in template context alongside base_template
  ([`62d92e4`](https://github.com/nordz0r/nopaste/commit/62d92e4891b81b1166ccbf3c479587d763ab4eae))

- Extract UI design into pluggable design templates
  ([`4a6474d`](https://github.com/nordz0r/nopaste/commit/4a6474d28f0e0774c8912b5fa2c2249a01d7d97a))

- Support DOCS_ALLOWLIST + provide .env and .env.example
  ([`1466e91`](https://github.com/nordz0r/nopaste/commit/1466e918b7fb4553af68c90b280ef397875a5c6e))


## v1.3.5 (2026-04-24)

### Bug Fixes

- Improve editor layout responsiveness
  ([`ba960f3`](https://github.com/nordz0r/nopaste/commit/ba960f3c63a865079c5a98b7d65b8a5cb067fced))


## v1.3.4 (2026-04-24)

### Bug Fixes

- Surface the author profile from the footer
  ([`5f9c0ca`](https://github.com/nordz0r/nopaste/commit/5f9c0ca8508bfded709206216d9ca810793a62fb))


## v1.3.3 (2026-04-24)

### Bug Fixes

- Keep displayed app version aligned with releases
  ([`6f8c3a8`](https://github.com/nordz0r/nopaste/commit/6f8c3a80fb5ff355411fd717b66e3ec80ca0ce3f))

- Update uv.lock
  ([`eb898bb`](https://github.com/nordz0r/nopaste/commit/eb898bbf36ae0b78fa8412f95ca7f6b33d343933))


## v1.3.2 (2026-04-23)

### Bug Fixes

- Prevent stale cached CSS after deploys
  ([`b3b26a6`](https://github.com/nordz0r/nopaste/commit/b3b26a6ef586e49c59743a062ffe97133d74c676))


## v1.3.1 (2026-04-23)

### Bug Fixes

- Improve save button legibility without enlarging it
  ([`720e3bf`](https://github.com/nordz0r/nopaste/commit/720e3bf4df9151e0a56d206e0e981a1f82cd6717))


## v1.3.0 (2026-04-23)

### Features

- Make nopaste links and branding easier to recognize
  ([`c7d90f0`](https://github.com/nordz0r/nopaste/commit/c7d90f09ba6bfe44d5f3c47ca70c90b771bea67a))


## v1.2.2 (2026-04-05)

### Bug Fixes

- Enable proxy headers for correct HTTPS URL generation
  ([`04b3317`](https://github.com/nordz0r/nopaste/commit/04b3317dd88845560e013992cd9b001d603eedcf))

### Documentation

- Document Shlink URL shortener integration
  ([`8829043`](https://github.com/nordz0r/nopaste/commit/882904362fbf65ca0708416085d85ef4a5707f9d))


## v1.2.1 (2026-04-05)

### Bug Fixes

- Copy link button uses Shlink short URL when available
  ([`ca5eaa6`](https://github.com/nordz0r/nopaste/commit/ca5eaa6b0ac524b9f8b7698b24153b135cb2e53b))


## v1.2.0 (2026-04-05)

### Features

- Add Shlink URL shortener integration
  ([`304f85b`](https://github.com/nordz0r/nopaste/commit/304f85b6f0ca345a16d17cdbbbc9c2deb4fa6680))


## v1.1.2 (2026-03-25)

### Bug Fixes

- Bundle fonts for offline deployments
  ([`a6723d4`](https://github.com/nordz0r/nopaste/commit/a6723d4b9d70e129f3c77829f95ef2d20a9433cc))


## v1.1.1 (2026-03-17)

### Bug Fixes

- Restore docker publish pipeline
  ([`43e1daf`](https://github.com/nordz0r/nopaste/commit/43e1daf9033eadc5cc98829877bb4ff369afad25))


## v1.1.0 (2026-03-17)

### Features

- Refined studio design with accurate goldfinch logo and SVG icons
  ([`8fd0fd1`](https://github.com/nordz0r/nopaste/commit/8fd0fd1671ba81db70341a27ea06179f534f6cb1))

- Switch to studio dark theme and restore original logo
  ([`d3b8a7b`](https://github.com/nordz0r/nopaste/commit/d3b8a7b629bfc32a8b95e348671b6911a2df1e60))

- Современный редизайн и поддержка тестирования в Docker
  ([`9b96b06`](https://github.com/nordz0r/nopaste/commit/9b96b0673399669276003182e20e29ca181bd456))


## v1.0.0 (2026-03-16)

### Bug Fixes

- Move copy link icon beside brand
  ([`2ca41d7`](https://github.com/nordz0r/nopaste/commit/2ca41d761d33974bc1c39a33d8bc711c38d6d619))

### Build System

- **docker**: Use multi-stage image with uv builder
  ([`a277bc3`](https://github.com/nordz0r/nopaste/commit/a277bc31466b3f570511c6ca2a446841eaf3c0fd))

### Chores

- Enforce lf line endings
  ([`d0087b4`](https://github.com/nordz0r/nopaste/commit/d0087b499ffdffb4c0515a411793f4c6b124ef7d))

### Continuous Integration

- Add lint and test workflow
  ([`1b3d1ce`](https://github.com/nordz0r/nopaste/commit/1b3d1ced2d5c078a0c6e5db7585de2d8f09edf9f))

### Features

- Shorten paste ids and simplify releases
  ([`e468269`](https://github.com/nordz0r/nopaste/commit/e468269d4d1f0980cacbcc67152b943b1ca99cc4))


## [0.7.2](https://github.com/nordz0r/nopaste/compare/v0.7.1...v0.7.2) (2026-03-11)


### Bug Fixes

* refine header layout and goldfinch mark ([4dfc62a](https://github.com/nordz0r/nopaste/commit/4dfc62a4b5991c6e68deb8fdc009895768d245e7))

## [0.7.1](https://github.com/nordz0r/nopaste/compare/v0.7.0...v0.7.1) (2026-03-11)


### Bug Fixes

* fix Dockerfile WORKDIR ordering so venv is created in /app ([eb4aaa0](https://github.com/nordz0r/nopaste/commit/eb4aaa060ff95c516a02119ef1cfaba6974c2058))

## [0.7.0](https://github.com/nordz0r/nopaste/compare/v0.6.0...v0.7.0) (2026-03-11)


### Features

* redesign UI to minimalist utility style ([68db407](https://github.com/nordz0r/nopaste/commit/68db407a169c43851b7f8f55da34ef9bcae74c68))
* warm minimalist redesign with SVG icons and goldfinch animation ([4b1b71e](https://github.com/nordz0r/nopaste/commit/4b1b71e232096072ffc76b4aeebdbdeccea0543a))

## [0.6.0](https://github.com/nordz0r/nopaste/compare/v0.5.0...v0.6.0) (2026-03-11)


### Features

* support legacy history cookies and line ranges ([b14a374](https://github.com/nordz0r/nopaste/commit/b14a37445ab0f873226efed41ab1e3be4780014d))

## [0.5.0](https://github.com/nordz0r/nopaste/compare/v0.4.0...v0.5.0) (2026-03-11)


### Features

* add copyable line links ([ae59e12](https://github.com/nordz0r/nopaste/commit/ae59e12956d7eb2e58a54fa9b36ebfd651328c5e))
* refresh nopaste interface ([78f51f0](https://github.com/nordz0r/nopaste/commit/78f51f0e4339f24612d83a07fade858eecc21310))

## [0.4.0](https://github.com/nordz0r/nopaste/compare/v0.3.1...v0.4.0) (2026-03-11)


### Features

* improve paste history and line navigation ([1ccdebf](https://github.com/nordz0r/nopaste/commit/1ccdebfe98e5c7a4f7643244d2a304d016554677))


### Bug Fixes

* harden paste creation and cookie tracking ([57f5096](https://github.com/nordz0r/nopaste/commit/57f5096c7f70caa5fd745705777fda98cf63e058))

## [0.3.1](https://github.com/nordz0r/nopaste/compare/v0.3.0...v0.3.1) (2026-03-11)


### Bug Fixes

* automate GitHub releases and compose deployment ([1bff53b](https://github.com/nordz0r/nopaste/commit/1bff53bff54b1f3e56d030eba1d2072c8ab77709))
