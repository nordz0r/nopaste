# Changelog

All notable changes to this project will be documented in this file.

<!-- version list -->

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
