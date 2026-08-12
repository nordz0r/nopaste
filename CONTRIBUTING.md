# Contributing

## Setup

```bash
uv sync --frozen --extra test --group dev
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```

## Commits

This repo uses [Conventional Commits](https://www.conventionalcommits.org/). Releases are cut automatically from `main`.

| Prefix | Effect |
|--------|--------|
| `feat:` | minor version |
| `fix:` / `perf:` | patch version |
| `docs:`, `chore:`, `ci:`, `test:`, `refactor:` | no bump |

Keep the subject under ~72 characters. One logical change per commit.

## Pull requests

- Add or update tests for behavior changes
- Do not commit `.env`, databases, or generated caches
- Match the existing style (`ruff format`)

## Security

Please do not open a public issue for vulnerabilities. See [SECURITY.md](./SECURITY.md).
