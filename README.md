# clible

[![CI](https://github.com/mvirtai/clible-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/mvirtai/clible-v2/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](#)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](#)

Offline-first Bible study tool with full-text search, text analytics, and AI-powered insights. Bible translations are seeded from open XML sources into a local SQLite database, so every verse lookup, search, and analytics call runs without an external API at query time.

The project ships two interfaces:

- A **web app** (the primary user interface): React 19 + Vite frontend, Node.js/Express bridge, deployed as a single Docker image.
- A **CLI tool** that powers the web app and is also a first-class user surface for power users and scripting.

> **Full documentation:** [https://mvirtai.github.io/clible-v2/](https://mvirtai.github.io/clible-v2/)

---

## Features

- **Verse lookup** — references like `John 3:16` or `Genesis 1:1-3` resolved instantly from local SQLite.
- **FTS5 full-text search** — scoped to whole-Bible, book, chapter, testament, or verse range; with statistics and top-book breakdown.
- **Text analytics** — word frequency, lexical diversity, n-grams, concordance, and side-by-side translation comparison.
- **AI insights** — optional Gemini-powered study notes, tone analysis, and original-language study (rate-limited; `ai_access` on the account).
- **User accounts** — registration, login, sessions, and per-user settings (preferred translation, theme, UI language EN/FI).
- **Reading plans (web)** — catalog plans with daily passages, progress, and streaks (stored in PostgreSQL).
- **Export** — Markdown, HTML, JSON, CSV, TXT, and XML output for any verse, search, or analytics command.

---

## Quick start

```bash
git clone https://github.com/mvirtai/clible-v2.git
cd clible-v2
uv sync --all-groups

# Seed an English translation (one-time, ~4 MB)
uv run clible seed install web

# Try the CLI
uv run clible verse "John 3:16"
uv run clible search "grace" --scope book --reference Romans
uv run clible analytics chapter John 3
```

For the web app, the development guide, and the deployment guide, see the [documentation site](https://mvirtai.github.io/clible-v2/).

---

## Architecture

```
Web UI (React 19 / Vite)
      │ HTTP
Express bridge (Node.js / TypeScript)   ← session auth, AI proxy, rate limiting
      │ child_process.spawn
clible CLI (Python 3.12)                ← verse engine, FTS5 search, analytics
      │ sqlite3
SQLite (clible.db)                      ← seeded from XML; read-only at runtime
      │
PostgreSQL (Neon)                       ← user accounts, sessions, settings, reading plans
```

The Express layer is a thin bridge: it sanitises request parameters, spawns `clible` subcommands with `--json`, and forwards the structured output to the browser. All Bible logic lives in the Python CLI; the web layer adds auth, AI, and user state on top.

**Design principles:**

- **Offline-first** — Bible text is seeded once; subsequent lookups never touch the network.
- **Layered architecture** — UI → Services → Repositories → SQLite, each layer testable in isolation.
- **Dependency injection** — no global state or singletons; tests inject in-memory connections and mock parsers.
- **FTS5** — SQLite full-text search with triggers keeping the index in sync; no external search engine.

For the rationale behind the major design choices, see the [Architecture Decision Records](https://mvirtai.github.io/clible-v2/architecture/adr/001-offline-first-sqlite).

---

## Tech stack

| Layer            | Technology                                            |
|------------------|-------------------------------------------------------|
| Web frontend     | React 19, TypeScript, Vite 6, Tailwind CSS 4          |
| Web backend      | Node.js, Express 4, TypeScript                        |
| CLI              | Python 3.12+, Click, Rich                             |
| Verse data       | SQLite + FTS5                                         |
| User data        | PostgreSQL (Neon)                                     |
| Sessions         | `express-session` + `connect-pg-simple` (HTTP-only cookie) |
| AI               | Google Gemini (`@google/genai`)                       |
| Container        | Docker (single image: CLI + web)                      |
| CI/CD            | GitHub Actions (lint, test, build, push, docs deploy) |
| Package managers | uv (Python), npm (Node)                               |

---

## Documentation

The canonical entry point is the [documentation site](https://mvirtai.github.io/clible-v2/). Highlights:

- [Getting started](https://mvirtai.github.io/clible-v2/guide/getting-started) — install, seed, first commands
- [CLI reference](https://mvirtai.github.io/clible-v2/cli/analytics) — command examples and output shapes
- [Architecture overview](https://mvirtai.github.io/clible-v2/architecture/overview) — layers, patterns, ADRs
- [Web architecture](https://mvirtai.github.io/clible-v2/architecture/web) — Express bridge and request flow
- [API reference](https://mvirtai.github.io/clible-v2/api/reference) — interactive OpenAPI 3.1 spec
- [Deployment](https://mvirtai.github.io/clible-v2/guide/deployment) — Cloud Run, Compute Engine, Fly.io, Render

The docs are versioned in this repo under [`docs-site/`](docs-site/). Source-of-truth Markdown for guides and architecture lives there; the OpenAPI spec lives at [`docs/api/openapi.yml`](docs/api/openapi.yml).

---

## Development

```bash
uv sync --all-groups              # install Python deps
uv run pytest -v                  # run the test suite
uv run ruff check .               # lint
uv run ruff format --check .      # format check
```

For the web app:

```bash
cd src/clible-web
npm install
npm run dev                       # Vite + Express, with /api/* proxy
```

For the docs site:

```bash
cd docs-site
npm install
npm run dev                       # http://localhost:5173
```

See the [development guide](https://mvirtai.github.io/clible-v2/guide/development) for the full workflow.

---

## Contributing

Contributions are welcome — please read the [contributing guide](https://mvirtai.github.io/clible-v2/contributing) before opening a PR. The architectural rules listed there are enforced in code review.

---

## License

Bible translation notices and data sources are listed in [`NOTICE.md`](NOTICE.md).

### Deuterocanonical and alternate book support (local engine)

The SQLite book catalog includes additional explicit book identifiers used by
USFX/OSIS editions, including the seven Catholic deuterocanonical books and
separate Greek Esther/Daniel and related additions. It is a superset of
identifiers, not a declaration of any particular translation's canon. Existing
book IDs and positions 1–66 remain unchanged; missing catalog rows are added
idempotently on connection without altering installed verses. Beblia/Zefania
numeric mappings remain the legacy 66-book scheme; extra numbers are not
assigned a meaning. Use explicit-ID USFX or OSIS for expanded editions. Greek
additions and alternative versifications are not merged into Esther, Daniel,
or Baruch automatically. Web picker and reading plans are unchanged by this
local-engine increment.

To import an edition that you are authorized to store locally, extract the
publisher's USFX or OSIS XML and use a distinct ID, for example:

```sh
clible seed import-local spablm /path/to/authorized.xml \
  --name 'Santa Biblia libre para el mundo' --language es --format USFX \
  --source-url https://ebible.org/find/details.php?id=spablm --rights-confirmed
clible verse 'Tobías 1:1' --translation spablm
```

This command does not download files, overwrite an existing translation, or
claim that you have redistribution rights. Verify the source's terms and
actual book coverage before importing. Existing translations are not augmented
or silently substituted. On gway-001, the installed `spanishdhh`, `spa-rv1909`
and `web` editions each currently have 66 books; migration alone adds no text.

Verified source information:

- [Dios Habla Hoy rights](https://ubscopyrights.org/index.php/translate/view/dhh_product):
  complete digital DHH with deuterocanonicals requires a verified authorized
  source/edition; no such import is included here.
- [World English Bible FAQ](https://ebible.org/eng-web/webfaq.htm): public domain;
  the existing bundled USFX already includes 18 additional book identifiers.
- [Santa Biblia libre para el mundo](https://ebible.org/find/details.php?id=spablm):
  public-domain Spanish draft with deuterocanonical contents documented in
  [its index](https://ebible.org/spablm/). It is not DHH. Do not relabel it as DHH.

No new Bible text or downloaded source file is committed by this change.
