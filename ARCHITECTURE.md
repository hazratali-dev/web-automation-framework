# Distributed Web Automation Framework — Technical Specification

**Scope:** নিজস্ব ওয়েবসাইট পারফরম্যান্স মনিটরিং, কম্পিটিটর অ্যানালাইসিস, UX সিমুলেশন (বৈধ ও এথিক্যাল অটোমেশন ইউজ-কেস)।
**Status:** Design document — কোনো কোড এখনো লেখা হয়নি। ফেজ-বাই-ফেজ ইমপ্লিমেন্টেশনের জন্য রেফারেন্স হিসেবে ব্যবহার হবে।
**ডেভেলপমেন্ট নোট:** ডেভেলপার মেশিনে ১৬GB RAM — তাই Phase 1-5 একটি হালকা single-process dev configuration-এ বানানো হবে (কোনো Docker/Postgres/Redis/Celery/Grafana ছাড়া), আর Phase 6-এ একই ইন্টারফেসের প্রোডাকশন adapter যোগ হয়। বিস্তারিত: **Appendix A** (ডকুমেন্টের শেষে)।

---

## ১. সিস্টেম আর্কিটেকচার (High-Level, প্রোডাকশন টপোলজি)

> এই ডায়াগ্রাম প্রোডাকশন ডিপ্লয়মেন্ট বোঝায়। লোকাল ডেভেলপমেন্টে একই ডোমেইন/অ্যাপ্লিকেশন লজিক একটিমাত্র Python process-এ চলে (SQLite + in-process asyncio task runner + in-memory dict + টার্মিনাল লগ) — দেখুন **Appendix A**।

```
                                   ┌─────────────────────────┐
                                   │        Dashboard         │
                                   │   (React SPA, Browser)   │
                                   └────────────┬─────────────┘
                                                │ HTTPS / WSS
                                   ┌────────────▼─────────────┐
                                   │   Reverse Proxy (Nginx/   │
                                   │   Traefik) + TLS termination│
                                   └────────────┬─────────────┘
                                                │
                          ┌─────────────────────▼─────────────────────┐
                          │              API Gateway Layer              │
                          │            (FastAPI, stateless)             │
                          │  - Auth (JWT/API-Key)  - Rate limiting      │
                          │  - Task CRUD  - Metrics query  - WS stream  │
                          └───────┬────────────────────────┬────────────┘
                                  │                         │
                     ┌────────────▼───────────┐   ┌─────────▼──────────┐
                     │      PostgreSQL          │   │        Redis        │
                     │  (source of truth:        │   │  - Task queue broker│
                     │  tasks, proxies, runs,    │   │  - Proxy pool cache │
                     │  metrics, alerts, users)  │   │  - Rate-limit state │
                     └────────────▲───────────┘   └─────────▲──────────┘
                                  │                         │
                     ┌────────────┴─────────────────────────┴────────────┐
                     │                  Celery Beat (Scheduler)            │
                     │   DB থেকে schedule পড়ে হুবহু cron অনুযায়ী task     │
                     │   push করে Redis queue-তে (hourly/daily triggers)  │
                     └────────────┬────────────────────────────────────┘
                                  │ enqueue
                     ┌────────────▼─────────────────────────────────────┐
                     │            Celery Worker Pool (N containers)       │
                     │  ┌───────────────────────────────────────────┐    │
                     │  │  Worker Process (asyncio event loop)        │    │
                     │  │  ┌─────────────┐   ┌──────────────────┐    │    │
                     │  │  │ Proxy Manager│──▶│ Browser Automation│    │    │
                     │  │  │ (rotate/pick)│   │ Engine (Playwright)│   │    │
                     │  │  └─────────────┘   └────────┬──────────┘    │    │
                     │  │      Semaphore(N concurrent contexts)        │    │
                     │  └──────────────────────────────┬────────────┘    │
                     └─────────────────────────────────┼─────────────────┘
                                                        │ results/metrics
                     ┌──────────────────────────────────▼─────────────────┐
                     │       Monitoring & Logging Pipeline                   │
                     │  structlog(JSON) → Loki/Promtail → Grafana            │
                     │  Prometheus client → Prometheus → Grafana Alerts      │
                     │  Exceptions → Sentry                                  │
                     └────────────────────────────────────────────────────┘
```

**ডেটা ফ্লো (একটি টাস্কের জীবনচক্র, প্রোডাকশন):**

1. Celery Beat নির্ধারিত সময়ে (DB থেকে schedule পড়ে) একটি টাস্ক Redis queue-তে push করে।
2. একটি ফ্রি Celery worker টাস্ক তুলে নেয় → Proxy Manager থেকে একটি হেলদি প্রক্সি রিকোয়েস্ট করে।
3. Browser Automation Engine সেই প্রক্সি দিয়ে একটি isolated browser context তৈরি করে, টার্গেট URL-এ human-like আচরণ সিমুলেট করে।
4. রেজাল্ট (মেট্রিক্স, স্ক্রিনশট, error) PostgreSQL-এ persist হয়, লগ structlog দিয়ে emit হয়।
5. Prometheus metrics স্ক্র্যাপ করে, থ্রেশহোল্ড ক্রস করলে Grafana/Alertmanager অ্যালার্ট পাঠায়।
6. Dashboard API PostgreSQL + Redis থেকে রিয়েল-টাইম স্ট্যাটাস সার্ভ করে (REST + WebSocket)।

_(লোকাল dev-এ ধাপ ১-২-এর Celery Beat/Redis queue-এর বদলে একটি in-process asyncio scheduler+queue, আর ধাপ ৬-এর Redis-এর বদলে in-memory dict কাজ করে — Appendix A দেখুন।)_

---

## ২. টেকনোলজি স্ট্যাক

| স্তর                 | নির্বাচিত টুল (প্রোডাকশন)                   | কেন                                                         | বিকল্প                                      | লোকাল dev-এ                                               |
| -------------------- | ------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------- |
| ভাষা                 | Python 3.12                                 | Native asyncio পারফরম্যান্স উন্নতি, টাইপ হিন্ট improvements | Node.js (ইকোসিস্টেম কম রিচ)                 | অপরিবর্তিত                                                |
| ব্রাউজার ইঞ্জিন      | Playwright (async API)                      | Multi-browser, auto-wait, network interception              | Selenium+undetected-chromedriver, Puppeteer | অপরিবর্তিত (শুধু Chromium ইনস্টল)                         |
| স্টিলথ লেয়ার        | playwright-stealth / patchright             | ফিঙ্গারপ্রিন্ট leak কমায়                                   | Camoufox                                    | অপরিবর্তিত                                                |
| কনকারেন্সি           | asyncio + Semaphore                         | I/O-bound task-এর জন্য native                               | multiprocessing                             | অপরিবর্তিত (cap ৫)                                        |
| মেসেজ ব্রোকার        | Redis 7                                     | Queue+cache+rate-limit — একই ইনফ্রা তিন কাজে                | RabbitMQ                                    | **নেই** — asyncio-নেটিভ ইন-প্রসেস কিউ                     |
| টাস্ক কিউ            | Celery                                      | Retry, priority queue, Beat scheduler বিল্ট-ইন              | RQ, Dramatiq                                | **নেই** — সরাসরি `asyncio` (§Appendix A.4)                |
| ডেটাবেজ              | PostgreSQL 16                               | ACID, JSONB, শক্তিশালী indexing                             | TimescaleDB extension                       | **SQLite** ফাইল (§Appendix A.1)                           |
| ORM/Migration        | SQLAlchemy 2.0 + Alembic                    | Async সাপোর্ট, dialect-agnostic generic JSON টাইপ           | Django ORM                                  | অপরিবর্তিত (একই মডেল, dialect সুইচ)                       |
| API ফ্রেমওয়ার্ক     | FastAPI                                     | Native async, Pydantic validation, WebSocket সাপোর্ট        | Django REST Framework                       | অপরিবর্তিত                                                |
| ফ্রন্টএন্ড           | React + Vite + TypeScript                   | রিয়েল-টাইম ড্যাশবোর্ড                                      | Streamlit                                   | অপরিবর্তিত                                                |
| লগিং                 | structlog (JSON)                            | Structured, correlation-ID friendly                         | standard `logging`                          | `rich.logging.RichHandler` কনসোল renderer (§Appendix A.5) |
| লগ এগ্রিগেশন         | Grafana Loki + Promtail                     | হালকা, cost-effective vs ELK                                | ELK Stack                                   | **নেই** — টার্মিনাল আউটপুট যথেষ্ট                         |
| মেট্রিক্স            | Prometheus + Grafana                        | Pull-based scraping, alerting                               | Datadog                                     | **নেই**                                                   |
| এরর ট্র্যাকিং        | Sentry                                      | Stack trace grouping                                        | Rollbar/Bugsnag                             | **নেই** — rich traceback কনসোলে                           |
| কনটেইনারাইজেশন       | Docker + docker-compose                     | সহজ single-host orchestration                               | Kubernetes (স্কেল বড় হলে)                  | **নেই** — native Python venv (§Appendix A)                |
| সিক্রেট ম্যানেজমেন্ট | .env (dev)/Docker secrets/Vault (prod)      | সহজ dev flow, prod isolation                                | Cloud secret manager                        | `.env.local`                                              |
| এনক্রিপশন            | `cryptography` (Fernet)                     | at-rest এনক্রিপশন                                           | Vault Transit                               | অপরিবর্তিত                                                |
| টেস্টিং              | pytest + pytest-asyncio + pytest-playwright | Async-নেটিভ টেস্ট                                           | —                                           | অপরিবর্তিত                                                |

---

## ৩. ডেটাবেজ স্কিমা (PostgreSQL — dev-এ SQLite dialect-এ একই স্কিমা চলে)

### ER ডায়াগ্রাম (টেক্সট)

```
users ──────────────────────┐
  │ 1                        │ 1
  │                          │
  │ N                        │ N
audit_logs              alert_rules
                              │ 1
                              │
                              │ N
                           alerts ─────────────┐
                              │ N                │ N
                              │                  │
                              │ 1                │ 1
targets ──1───N── tasks ──1───N── task_runs ─────┘
                              │                  │ 1
                              │                  │
                              │                  │ N
                              │                metrics
                              │
proxies ──1───N── task_runs (proxy_id FK)
                              │ 1
                              │
                              │ N
                          sessions
```

### টেবিল-ভিত্তিক বিস্তারিত

**`users`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| email | TEXT UNIQUE NOT NULL | |
| hashed_password | TEXT NOT NULL | bcrypt/argon2 |
| role | TEXT | `admin`, `viewer`, `operator` |
| api_key_hash | TEXT | dashboard API access-এর জন্য |
| created_at | TIMESTAMPTZ DEFAULT now() | |

Index: `UNIQUE(email)`

**`proxies`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| host | TEXT NOT NULL | |
| port | INTEGER NOT NULL | |
| protocol | TEXT | `http`, `socks5` |
| username | TEXT | |
| password_encrypted | BYTEA | Fernet এনক্রিপ্টেড |
| provider | TEXT | e.g. `brightdata`, `self-hosted` |
| country | TEXT | |
| is_active | BOOLEAN DEFAULT true | |
| consecutive_failures | INTEGER DEFAULT 0 | |
| success_count | BIGINT DEFAULT 0 | |
| failure_count | BIGINT DEFAULT 0 | |
| avg_latency_ms | INTEGER | |
| last_checked_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

Index: `(is_active, last_checked_at)` — health-check দ্রুত stale proxy খুঁজে বের করার জন্য

**`targets`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| name | TEXT NOT NULL | |
| base_url | TEXT NOT NULL | |
| target_type | TEXT | `own_site`, `competitor` |
| config | JSON | selectors, viewport, custom headers ইত্যাদি (dialect-agnostic generic JSON — Postgres-এ JSONB, SQLite-এ TEXT-ব্যাকড) |
| is_active | BOOLEAN DEFAULT true | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

**`tasks`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| target_id | UUID FK → targets.id | |
| task_type | TEXT | `performance_check`, `competitor_analysis`, `ux_simulation` |
| schedule_cron | TEXT | e.g. `0 * * * *` |
| priority | SMALLINT DEFAULT 5 | |
| status | TEXT DEFAULT 'active' | `active`, `paused`, `archived` — pause/resume কন্ট্রোলের জন্য (§৫.৩) |
| created_at | TIMESTAMPTZ DEFAULT now() | |

Index: `(target_id, status)`

**`task_runs`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| task_id | UUID FK → tasks.id | |
| proxy_id | UUID FK → proxies.id NULLABLE | |
| status | TEXT | `queued`, `running`, `success`, `failed`, `retrying` |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | |
| duration_ms | INTEGER | |
| retry_count | SMALLINT DEFAULT 0 | |
| error_message | TEXT | |
| result | JSON | raw metrics/summary |
| screenshot_path | TEXT | object storage path |
| created_at | TIMESTAMPTZ DEFAULT now() | |

Index: `(task_id, started_at DESC)`, `(status)` — dashboard queries ও queue-backlog মনিটরিং-এর জন্য

**`sessions`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| task_run_id | UUID FK → task_runs.id | |
| browser_type | TEXT | `chromium`/`firefox`/`webkit` |
| user_agent | TEXT | |
| viewport | JSON | `{width, height}` |
| fingerprint_config | JSON | stealth randomization params |
| created_at | TIMESTAMPTZ DEFAULT now() | |

**`metrics`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | BIGSERIAL PK | high-volume table |
| task_run_id | UUID FK → task_runs.id | |
| metric_name | TEXT | `lcp`, `fcp`, `ttfb`, `cls`, `load_time_ms` |
| metric_value | DOUBLE PRECISION | |
| unit | TEXT | |
| recorded_at | TIMESTAMPTZ DEFAULT now() | |

Index: `(task_run_id, metric_name)` — পরে ভলিউম বাড়লে TimescaleDB hypertable-এ কনভার্ট করার প্রার্থী

**`alert_rules`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| name | TEXT | |
| condition | JSON | e.g. `{"metric":"lcp","op":">","value":2500}` |
| severity | TEXT | `info`,`warning`,`critical` |
| is_active | BOOLEAN DEFAULT true | |

**`alerts`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | UUID PK | |
| rule_id | UUID FK → alert_rules.id | |
| task_run_id | UUID FK → task_runs.id | |
| message | TEXT | |
| is_resolved | BOOLEAN DEFAULT false | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

Index: `(is_resolved, created_at DESC)`

**`audit_logs`**
| কলাম | টাইপ | নোট |
|---|---|---|
| id | BIGSERIAL PK | |
| user_id | UUID FK → users.id | |
| action | TEXT | |
| resource | TEXT | |
| metadata | JSON | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

**`runtime_config`** *(নতুন — ডায়নামিক/runtime-configurable সেটিংস, §৫.৬)*
| কলাম | টাইপ | নোট |
|---|---|---|
| key | TEXT PK | |
| value | TEXT NOT NULL | টাইপ কোয়ার্স করা হয় অ্যাপ্লিকেশন লেয়ারে (int/str/bool), কলামে সবসময় TEXT |
| updated_at | TIMESTAMPTZ DEFAULT now() | |

```sql
CREATE TABLE runtime_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

ডিফল্ট রো (seed migration-এ ইনসার্ট হবে):
| key | ডিফল্ট value | ব্যবহার |
|---|---|---|
| `max_concurrent_browsers` | `5` | Browser Engine concurrency cap (§৫.২) |
| `proxy_strategy` | `round_robin` | Proxy Manager রোটেশন স্ট্র্যাটেজি (§৫.১) — `round_robin` অথবা `weighted` |
| `default_timeout_seconds` | `30` | Browser context/navigation-এর ডিফল্ট timeout, `targets.config`-এ per-target override না থাকলে প্রযোজ্য |

*(এটি entity-graph-এর অংশ নয় — কোনো FK নেই, তাই উপরের ER ডায়াগ্রামে দেখানো হয়নি; একটি স্বাধীন গ্লোবাল key-value স্টোর।)*

---

## ৪. প্রজেক্ট ফোল্ডার স্ট্রাকচার (Clean Architecture)

```
web-automation/
├── src/
│   ├── domain/                     # Framework-agnostic business rules
│   │   ├── entities/                # Task, Proxy, TaskRun, Metric dataclasses
│   │   ├── value_objects/           # Url, ProxyAddress, ScheduleExpr
│   │   └── interfaces/              # Ports: ProxyRepository, TaskRunnerPort,
│   │                                #        SchedulerPort, StatusStorePort,
│   │                                #        RuntimeConfigPort
│   │
│   ├── application/                 # Use cases (orchestration, no I/O detail)
│   │   ├── use_cases/                # RunTask, RunVisitorBatch, RotateProxy,
│   │   │                              # EvaluateAlertRules, PauseTask, ResumeTask,
│   │   │                              # RunTaskNow, UpdateRuntimeConfig
│   │   └── dto/                      # Pydantic request/response models
│   │
│   ├── infrastructure/              # Adapters — concrete implementations
│   │   ├── database/
│   │   │   ├── models/               # SQLAlchemy ORM models (dialect-agnostic)
│   │   │   ├── repositories/         # Interface implementations
│   │   │   └── migrations/           # Alembic versions
│   │   ├── browser/
│   │   │   ├── engine.py             # Playwright context lifecycle mgmt
│   │   │   ├── stealth/              # Fingerprint randomization
│   │   │   └── behaviors/            # Mouse/scroll/typing human-simulation
│   │   ├── proxy/
│   │   │   ├── providers/            # Per-provider adapters
│   │   │   ├── health_check.py
│   │   │   └── manager.py            # Rotation/selection strategy
│   │   ├── task_runner/              # TaskRunnerPort adapters
│   │   │   ├── asyncio_runner.py     # dev: in-process Queue + Semaphore(N),
│   │   │   │                        #      N = runtime_config.max_concurrent_browsers
│   │   │   └── celery_runner.py      # prod: Celery + Redis broker
│   │   ├── scheduler/                # SchedulerPort adapters
│   │   │   ├── asyncio_scheduler.py  # dev: APScheduler AsyncIOScheduler
│   │   │   └── celery_beat_scheduler.py  # prod: dynamic DB-driven Celery Beat
│   │   ├── status_store/             # StatusStorePort adapters
│   │   │   ├── memory_store.py       # dev: in-memory dict (single process)
│   │   │   └── redis_store.py        # prod: Redis pub/sub
│   │   ├── config/
│   │   │   └── runtime_config_service.py  # RuntimeConfigPort adapter — DB-ব্যাকড,
│   │   │                                  # write-through cache (§৫.৬), dev/prod অভিন্ন
│   │   └── monitoring/
│   │       ├── logging_setup.py      # structlog config (console/JSON renderer)
│   │       ├── metrics.py            # Prometheus client (prod-only)
│   │       └── sentry_setup.py       # prod-only
│   │
│   ├── interfaces/                  # Entry points
│   │   ├── api/
│   │   │   ├── routers/              # tasks.py, proxies.py, metrics.py, auth.py,
│   │   │   │                        # config.py (runtime_config CRUD)
│   │   │   ├── schemas/
│   │   │   ├── dependencies/         # auth, DB session injection
│   │   │   └── websocket.py
│   │   ├── cli/                      # Admin/ops CLI (typer)
│   │   └── workers/                  # dev: none needed (in-process);
│   │                                 # prod: celery_worker_entry.py, beat_entry.py
│   │
│   ├── config/                       # Settings (pydantic-settings, APP_ENV-driven
│   │                                 # factory selecting dev/prod adapters)
│   └── shared/                       # exceptions, constants, utils
│
├── dashboard/                        # React frontend (separate app)
│   ├── src/
│   └── package.json
│
├── tests/
│   ├── unit/
│   ├── integration/                  # dev: SQLite; CI: dockerized Postgres too
│   └── e2e/
│
├── docker/                           # প্রোডাকশন-only — dev-এ ব্যবহৃত হয় না
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── docker-compose.yml
│
├── scripts/                          # one-off ops scripts
├── docs/                             # ADRs, runbooks
├── .env.example
├── .env.local.example                # APP_ENV=local ডিফল্ট টেমপ্লেট
├── pyproject.toml
└── README.md
```

**নীতি:** ডিপেন্ডেন্সি সবসময় বাইরে থেকে ভেতরে (`infrastructure`/`interfaces` → `application` → `domain`) যায়, উল্টো কখনো নয়। `domain` লেয়ার Playwright/SQLAlchemy/Celery/Redis-এর কিছুই জানে না — শুধু abstract interface (port)। এই কারণেই dev-এর asyncio adapter আর prod-এর Celery adapter একই port ইমপ্লিমেন্ট করে বলে বিজনেস লজিক/use case কোড একবার লিখলেই দুই environment-এ চলে।

---

## ৫. মূল মডিউলসমূহ

### ৫.১ Proxy Manager

- **স্টোরেজ:** প্রোডাকশনে PostgreSQL = source of truth, Redis-এ active pool cache (sorted set)। dev-এ শুধু SQLite (কোনো cache layer লাগে না, ৫-প্রক্সি স্কেলে সরাসরি DB query যথেষ্ট দ্রুত)।
- **রোটেশন স্ট্র্যাটেজি (ডায়নামিক, §৫.৬):**
  - _Round-robin_ — সাধারণ লোড ছড়ানোর জন্য ডিফল্ট।
  - _Weighted-random_ — success rate অনুযায়ী ওজন।
  - _Sticky-session_ — একই task-run-এর সব রিকোয়েস্ট একই প্রক্সি দিয়ে।
  - সক্রিয় স্ট্র্যাটেজি হার্ডকোড নয় — প্রতিটি প্রক্সি-সিলেকশন কলে `runtime_config.proxy_strategy` (`round_robin`/`weighted`) পড়া হয় `RuntimeConfigPort`-এর মাধ্যমে। API দিয়ে ভ্যালু বদলালে **পরবর্তী প্রক্সি সিলেকশন কল থেকেই** নতুন স্ট্র্যাটেজি কার্যকর হয় (এটি batch-bound নয়, কারণ প্রতিটি সিলেকশন একটি স্বতন্ত্র রিড — সেমাফোরের মতো কোনো লাইভ-অবজেক্ট resize সমস্যা এখানে নেই)।
- **হেলথ চেক:** একটি periodic coroutine প্রতিটি active প্রক্সিতে lightweight HTTP HEAD পাঠায়, লেটেন্সি/success-fail রেকর্ড করে। প্রোডাকশনে এটি Celery Beat-ট্রিগার্ড টাস্ক; dev-এ একই কোড `asyncio_scheduler`-এর একটি periodic job হিসেবে চলে (§Appendix A.4)।
- **মৃত প্রক্সি বাদ দেওয়া:** `consecutive_failures >= 3` হলে `is_active = false` (soft-delete)। প্রতি ঘণ্টায় inactive প্রক্সি re-test (self-healing)।
- **ক্রেডেনশিয়াল সুরক্ষা:** পাসওয়ার্ড DB-তে Fernet-এনক্রিপ্টেড; লগে কখনো plaintext যায় না।

### ৫.২ Browser Automation Engine

- **কনকারেন্সি মডেল:** একটিমাত্র browser instance-এর ভেতর একাধিক isolated `BrowserContext` (আলাদা cookie/storage) — full browser instance-এর তুলনায় memory সাশ্রয়ী। `asyncio.Semaphore(N)` দিয়ে concurrent context সংখ্যা সীমিত (dev ডিফল্ট N=৫, prod ডিফল্ট N=১০+/worker replica, দেখুন §৭)।
- **ডায়নামিক concurrency cap (§৫.৬):** `N` হার্ডকোড নয় — `runtime_config.max_concurrent_browsers`-এ রাখা হয়। **টেকনিক্যাল সীমাবদ্ধতা:** Python-এর `asyncio.Semaphore` লাইভ-রিসাইজযোগ্য নয় (একবার তৈরি হলে internal counter ফিক্সড)। তাই সত্যিকারের mid-batch resize সম্ভব নয় — এর বদলে প্রতিটি নতুন ব্যাচ/task-dispatch cycle শুরুর ঠিক আগে `RunVisitorBatch`/dispatcher use case `RuntimeConfigPort` থেকে সর্বশেষ `max_concurrent_browsers` পড়ে **একটি নতুন `asyncio.Semaphore(N)` তৈরি করে** সেই ব্যাচের জন্য। ফলাফল ঠিক ব্যবহারকারীর চাওয়া আচরণ: বর্তমানে চলমান (পুরনো semaphore থেকে permit-হোল্ডিং) কনটেক্সটগুলো নির্বিঘ্নে শেষ হয়, আর পরবর্তী ব্যাচ নতুন cap মেনে চলে। কনফিগ-আপডেট সাথে সাথে DB + ইন-মেমরি cache দুটোতেই লেখা হয় (write-through, কোনো TTL-lag নেই), তাই dispatcher সবসময় সর্বশেষ ভ্যালু দেখে।
- **Human-like behavior:**
  - মাউস মুভমেন্ট: bezier-curve পাথ দিয়ে ধাপে ধাপে move।
  - টাইপিং: প্রতি key-stroke-এ randomized delay (৫০–২০০ms)।
  - স্ক্রল: ধাপে ধাপে স্ক্রল + র‍্যান্ডম pause।
  - Think-time: প্রতিটি action-এর মাঝে randomized wait।
  - প্রতি সেশনে randomized viewport, user-agent, timezone, locale।
- **ফিঙ্গারপ্রিন্ট রেজিস্ট্যান্স:** stealth patch দিয়ে headless-detection markers মাস্ক করা; Canvas/WebGL noise injection।
- **লাইফসাইকেল:** semaphore acquire → context create → navigate → action sequence → metrics capture → screenshot (প্রয়োজনে) → context close → semaphore release। প্রতিটি ধাপ try/except-এ wrap, ব্যর্থ হলে structured error persist।

### ৫.৩ Scheduler ও Task Execution

`domain/interfaces`-এ দুটি port ডিফাইন করা হবে — `SchedulerPort` ও `TaskRunnerPort` — যাদের dev ও prod-এ ভিন্ন adapter থাকে, কিন্তু `application/use_cases` কোড উভয় ক্ষেত্রেই অভিন্ন থাকে:

|                | **Local dev**                                                                       | **Production**                                               |
| -------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Task execution | `asyncio.Queue` + কনজিউমার কোরুটিন, `asyncio.Semaphore(N)`-বাউন্ড (N = ডায়নামিক, §৫.৬), একই process | Celery worker pool (আলাদা container, N replica)              |
| Scheduling     | APScheduler `AsyncIOScheduler` — DB থেকে `schedule_cron` পড়ে একই process-এ trigger | Celery Beat + dynamic DB-driven scheduler (`redbeat`/কাস্টম) |
| Broker         | দরকার নেই                                                                           | Redis                                                        |
| Manual trigger | dashboard API → সরাসরি `asyncio.Queue.put()`                                        | dashboard API → Celery task enqueue                          |

**Pause/Resume (`tasks.status`):** প্রতিটি scheduling pass-এ (dev: `AsyncIOScheduler` tick; prod: Celery Beat tick) নতুন task_run enqueue করার আগে `tasks.status = 'active'` চেক করা হয়। `paused`/`archived` টাস্কের জন্য নতুন কোনো task_run তৈরি হয় না। **ইতিমধ্যে dispatch হওয়া/চলমান task_run-এ কোনো প্রভাব পড়ে না** — সেগুলো স্বাধীনভাবে (scheduler থেকে decoupled) চলতে থাকে ও স্বাভাবিকভাবে শেষ হয় (browser context lifecycle, §৫.২), যাতে মাঝপথে থামিয়ে ডেটা/স্ক্রিনশট নষ্ট না হয়। Pause শুধু ভবিষ্যতের enqueue বন্ধ করে, চলমান কাজে interrupt পাঠায় না।

**Run-Now (ম্যানুয়াল ওভাররাইড, §৫.৫):** `POST /api/tasks/{task_id}/run-now` শিডিউল/cron টাইমিং উপেক্ষা করে সরাসরি একটি task_run dispatch করে (dev: `asyncio.Queue.put()`; prod: Celery enqueue) — কিন্তু concurrency cap (`Semaphore(N)`, §৫.২) এড়ায় না, শুধু queue-তে ঢোকে এবং স্বাভাবিক নিয়মে slot খালি হলে execute হয়। **ডিজাইন সিদ্ধান্ত:** `paused`/`archived` টাস্কে run-now কল করলে `409 Conflict` — অর্থাৎ pause মানে সত্যিই "এই টাস্ক এখন চলবে না", ম্যানুয়াল বা শিডিউল্ড কোনোভাবেই না; প্রয়োজনে আগে resume করে তারপর run-now কল করতে হবে (ধারাবাহিক, বিভ্রান্তিমুক্ত আচরণ)।

**Celery worker লঞ্চ কমান্ড (প্রোডাকশন) ও একটি জরুরি সংশোধনী:**

```bash
celery -A src.infrastructure.task_runner.celery_runner worker --pool=solo
```

প্রস্তাবিত মূল কমান্ডে (`--pool=solo --concurrency=2 --max-memory-per-child=1200000`) দুটো ফ্ল্যাগ বাস্তবে কার্যকর হয় না, তাই বাদ দেওয়া হয়েছে — কারণ জানা দরকার যাতে ভুল ধারণায় প্রোডাকশনে সমস্যা না হয়:

- **`--concurrency=2` কাজ করে না:** Celery-র `solo` pool কোনো child process fork করে না — এটি একটিমাত্র (main) প্রসেসে task সিকোয়েনশিয়ালি প্রসেস করে, তাই `--concurrency` ফ্ল্যাগ solo pool-এ সম্পূর্ণ ignored হয় (Celery নিজে warning লগ করে)। ভালো খবর হলো, এই আর্কিটেকচারে ব্রাউজার-কনকারেন্সি এমনিতেই Celery-লেয়ারে নয় — §৫.২-এ বর্ণিত `asyncio.Semaphore(N)` দিয়ে টাস্ক কোডের **ভেতরে** নিয়ন্ত্রিত হয় (dev-এ একই প্যাটার্ন, Appendix A.2)। তাই "প্রতি worker-এ সর্বোচ্চ ২টি ব্রাউজার কনটেক্সট" আসলে সেট হবে `infrastructure/browser/engine.py`-তে `asyncio.Semaphore(2)` দিয়ে — কোনো Celery CLI ফ্ল্যাগ দিয়ে নয়।
- **`--max-memory-per-child` কাজ করে না:** এই ফ্ল্যাগ prefork pool-এর child-process recycling মেকানিজমের উপর নির্ভরশীল; solo pool-এ কোনো child process নেই বলে এটি silently no-op থাকে। বাস্তব মেমোরি সেফটি-নেট এখানে Docker-level `mem_limit: 2g` (§৬) — সীমা ছাড়ালে container OOM-kill হয়ে `restart: on-failure` পলিসি অনুযায়ী পুনরায় চালু হয়।
- **ফলাফল (মেমোরি বাজেট):** ২টি browser context (২×~১৫০-৩০০MB) + Playwright/Celery process overhead (~২০০-৩০০MB) ধরে স্বাভাবিক ব্যবহার ≈৬০০MB-১GB — মূল ১.৫GB টার্গেটের মধ্যেই থাকে; `mem_limit: 2g` শুধু leak/spike-এর বিরুদ্ধে বাইরের হার্ড সেফটি সীমা, স্বাভাবিক অবস্থায় স্পর্শ হওয়ার কথা না।

### ৫.৪ Monitoring ও Logging

- **Logging:** structlog দিয়ে প্রতিটি লগ structured, প্রতিটি task-run-এ correlation ID (task_run_id) attach।
  - **dev:** কনসোল renderer = `rich.logging.RichHandler` — কালারড, human-readable, pretty traceback।
  - **prod:** কনসোল renderer = JSON → Promtail → Loki → Grafana Explore।
- **Metrics:** prod-এ Prometheus custom metric (task success/fail rate, avg duration, active proxy %, queue depth) → Grafana dashboard। dev-এ metrics কালেকশন বাদ (RAM সাশ্রয়) — task-level ডেটা তো DB-তেই আছে, দরকারে সরাসরি query করা যায়।
- **Error tracking:** prod-এ Sentry। dev-এ শুধু rich traceback কনসোলে।
- **Alerting:** prod-এ Grafana Alerting/Alertmanager → Slack/email। dev-এ প্রযোজ্য নয় (একজন ডেভেলপার সরাসরি টার্মিনাল দেখছেন)।

### ৫.৫ Dashboard/API

- **REST API (FastAPI):** task CRUD, task-run history (paginated + filter), proxy pool status, metrics query, alert acknowledgement। **নতুন ডায়নামিক-কন্ট্রোল এন্ডপয়েন্ট (§৫.৬):**
  - `POST /api/tasks/{task_id}/run-now` — cron উপেক্ষা করে সঙ্গে সঙ্গে dispatch (§৫.৩)।
  - `PATCH /api/tasks/{task_id}/status` — `active`/`paused`/`archived` সেট করে (pause/resume, §৫.৩)।
  - `PATCH /api/targets/{target_id}` — `config` JSON (viewport, headers, timeout) আপডেট; পরবর্তী task_run নতুন কনফিগ পড়ে (per-run lookup, কোনো caching নেই বলে সবসময় সর্বশেষ)।
  - `GET /api/config` — সব `runtime_config` key/value লিস্ট করে।
  - `PATCH /api/config/{key}` — একটি key (যেমন `max_concurrent_browsers`, `proxy_strategy`) আপডেট করে; সব ক্ষেত্রে `audit_logs`-এ কে/কখন/কী বদলাল রেকর্ড হয় (§৮)।
- **WebSocket (লাইভ স্ট্যাটাস):** টাস্ক-রান স্ট্যাটাস (`queued`→`running`→`success`/`failed`) পুশ করার জন্য `StatusStorePort`-এর dev/prod adapter ব্যবহার হয়, WebSocket handler কোড উভয় ক্ষেত্রে অভিন্ন:
  - **dev:** in-memory Python `dict` (`{task_run_id: status}`)। যেহেতু dev-এ task execution ও API একই process-এ চলে (§৫.৩ — Celery নেই), dict সরাসরি শেয়ারযোগ্য, কোনো cross-process boundary নেই। RAM খরচ ৫-১০MB।
  - **prod:** Redis pub/sub — Celery worker আলাদা container বলে plain dict কাজ করবে না (memory শেয়ার হয় না); worker publish করে, API subscribe করে WebSocket-এ ফরওয়ার্ড করে।
- **Auth:** dashboard user login → JWT; প্রোগ্রাম্যাটিক অ্যাক্সেসের জন্য API key (hashed storage, per-key rate limit)।
- **Frontend:** React — task list/detail view, proxy pool health view, metrics চার্ট, লাইভ ভিজিটর-ব্যাচ প্রগ্রেস, alert feed (alert feed শুধু prod-এ সক্রিয়)। নতুন UI কন্ট্রোল: concurrency স্লাইডার/ইনপুট (`max_concurrent_browsers`), proxy strategy টগল, প্রতি টাস্কে Pause/Resume বাটন ও "Run Now" বাটন।

### ৫.৬ Runtime Configuration Service (ডায়নামিক কনফিগারেশন)

সিস্টেমের গুরুত্বপূর্ণ প্যারামিটার (concurrency cap, proxy strategy, default timeout) অ্যাপ রিস্টার্ট ছাড়াই API/ড্যাশবোর্ড থেকে বদলানো যায় — এই ক্রস-কাটিং কনসার্নটি একটি স্বতন্ত্র `RuntimeConfigPort` (domain) + `runtime_config_service.py` (infrastructure) কম্পোনেন্টে থাকে, যা Proxy Manager (§৫.১), Browser Engine (§৫.২), ও Scheduler (§৫.৩) — সবাই ব্যবহার করে:

- **স্টোরেজ:** `runtime_config` টেবিল (§৩) — key-value, `value` সবসময় TEXT, অ্যাপ লেয়ারে int/str/bool-এ কোয়ার্স হয়।
- **রিড প্যাটার্ন:** dev ও prod উভয়ে একটি ছোট **write-through in-memory cache** (dict, TTL নেই) — API-তে `PATCH /api/config/{key}` কল হলে DB লেখার সাথে সাথে cache-ও আপডেট হয়, তাই কোনো stale-read উইন্ডো নেই। সাধারণ read (Proxy Manager/Browser Engine থেকে) সবসময় এই cache থেকে আসে — প্রতিটি প্রক্সি-সিলেকশন/ব্যাচ-ডিসপ্যাচে DB round-trip লাগে না।
- **প্রয়োগের সময়সীমা (গুরুত্বপূর্ণ, প্রত্যাশা স্পষ্ট রাখতে):**
  - `proxy_strategy` — **তাৎক্ষণিক**, পরের প্রক্সি-সিলেকশন কল থেকেই কার্যকর (প্রতিটি সিলেকশন একটি স্বতন্ত্র read)।
  - `max_concurrent_browsers` — **পরবর্তী ব্যাচ/dispatch cycle থেকে** কার্যকর (§৫.২ — চলমান browser context বাধাগ্রস্ত হয় না, কারণ `asyncio.Semaphore` লাইভ-রিসাইজযোগ্য নয়)।
  - `default_timeout_seconds` — **পরবর্তী task_run থেকে** কার্যকর (প্রতিটি রান শুরুতে ফ্রেশ read করে)।
- **dev/prod-এ অভিন্ন:** যেহেতু এটি সবসময় DB-ব্যাকড (SQLite dev-এ, PostgreSQL prod-এ) এবং in-process cache ব্যবহার করে — কোনো Redis/Celery নির্ভরতা নেই, তাই dev/prod উভয়েই একই adapter কোড চলে (অন্য পোর্টগুলোর মতো আলাদা dev/prod adapter লাগে না)।

---

## ৬. ডিপ্লয়মেন্ট স্ট্র্যাটেজি (প্রোডাকশন)

> লোকাল dev-এ Docker/docker-compose লাগে না — Appendix A দেখুন। এই সেকশন শুধু Phase 6 (প্রোডাকশন) প্রযোজ্য।

### docker-compose সার্ভিস লেআউট (হার্ড মেমরি লিমিটসহ)

১৬GB RAM মেশিনেও যেন প্রোডাকশন-কনফিগ টেস্ট/স্টেজিং চালানো গেলে Docker Desktop/host ফুলে-ফেঁপে না ওঠে, তাই প্রতিটি সার্ভিসে `mem_limit` (hard cap — এই সীমার বেশি ব্যবহার করলে container OOM-kill হয়) নির্ধারিত থাকবে; `worker`-এ অতিরিক্ত `mem_reservation` (soft minimum — Docker স্টার্টআপেই এটুকু guarantee রাখে) দেওয়া হয়েছে যাতে Chromium-heavy worker resource-starve না হয়:

```yaml
services:
  postgres:
    # persistent volume, healthcheck
    mem_limit: 512m

  redis:
    # persistent volume (AOF), healthcheck
    mem_limit: 256m

  api:
    # FastAPI (uvicorn/gunicorn+uvicorn workers)
    mem_limit: 512m

  worker:
    # Celery worker (replicas: N, Playwright browsers pre-installed)
    command: celery -A src.infrastructure.task_runner.celery_runner worker --pool=solo
    # concurrency Celery flag নয় — asyncio.Semaphore(2) টাস্ক কোডে সেট (§৫.৩)
    mem_limit: 2g # সর্বোচ্চ ২GB প্রতি replica — এর বেশি হলে OOM-kill
    mem_reservation: 1g # ন্যূনতম ১GB guaranteed, যাতে Docker স্টার্টআপেই এটুকু বরাদ্দ রাখে
    restart: on-failure

  beat:
    # Celery beat (single replica — leader lock দিয়ে duplicate scheduling এড়ানো)
    mem_limit: 256m

  flower:
    # Celery monitoring UI (optional, internal-only)
    mem_limit: 128m

  prometheus:
    # metrics scrape
    mem_limit: 256m

  grafana:
    # dashboards + alerting
    mem_limit: 256m

  loki:
    # log aggregation storage/query
    mem_limit: 256m

  promtail:
    # log shipping agent
    mem_limit: 128m

  dashboard:
    # React static build served via nginx
    mem_limit: 64m

  nginx: # বা traefik
    # reverse proxy + TLS termination (single public entrypoint)
    mem_limit: 128m
```

**⚠️ Replica-count সতর্কতা:** `worker`-এর `mem_limit: 2g` **প্রতি replica**-য় প্রযোজ্য, মোট নয়। উপরের non-worker সার্ভিসগুলোর যোগফল ≈ ২.৭৩GB — তাই ১৬GB হোস্টে (Docker Desktop/WSL2 overhead + OS বাদ দিয়ে) নিরাপদে ১-২টি worker replica (২-৪GB) চালিয়ে প্রোডাকশন-কনফিগ লোকালি স্টেজ/টেস্ট করা যায়। কিন্তু §৭-এ বর্ণিত ১০০-concurrent টার্গেটের জন্য ১০টি replica (১০×২GB = ২০GB শুধু worker-এই) এই ১৬GB মেশিনে ধরবে না — full-scale ১০০-concurrent লোড টেস্ট (Phase 6) একটি বড় RAM-এর হোস্ট/CI রানারে চালাতে হবে; লোকাল মেশিনে replica সংখ্যা ছোট রেখে (`docker-compose up --scale worker=2`) শুধু orchestration/fault-tolerance যাচাই করা যাবে।

- **Dockerfile স্ট্র্যাটেজি:** multi-stage build — worker image-এ `playwright install --with-deps chromium firefox webkit` বিল্ড-টাইমে বেক করা থাকবে। API ও worker আলাদা image।
- **এনভায়রনমেন্ট ভেরিয়েবল ম্যানেজমেন্ট:**
  - dev: `.env.local` (gitignored), `APP_ENV=local`।
  - prod: Docker secrets (`docker-compose.yml`-এ `secrets:` ব্লক) অথবা external secret manager mount।
  - সেন্সিটিভ ভ্যালু (DB পাসওয়ার্ড, proxy provider API key, Fernet key, JWT secret, Sentry DSN) সব env-driven।
- **Networking:** Postgres/Redis শুধু internal Docker network-এ। শুধু nginx/traefik ৪৪৩ পোর্টে পাবলিক।
- **Health checks:** প্রতিটি সার্ভিসে docker-compose `healthcheck`, worker restart policy `on-failure` with backoff।

---

## ৭. স্কেলেবিলিটি ও ফেইল-টলারেন্স (প্রোডাকশন)

- **১০০ কনকারেন্ট সেশন হ্যান্ডলিং:** প্রতিটি worker `--pool=solo`-তে চলে (§৫.৩), Celery-র নিজস্ব concurrency ব্যবহার হয় না — বরং টাস্ক কোডের ভেতরে `asyncio.Semaphore(N)` দিয়ে concurrency cap সেট হয় (যেমন ১০/worker)। ১০টি worker replica চালিয়ে ১০০ concurrent browser context অর্জন করা হয়। প্রতিটি worker-এর Docker `mem_limit` N অনুযায়ী সাইজ করা হয় (context প্রতি ~১৫০-২৫০MB + ~২৫০MB process overhead ধরে; §৬-এর ১৬GB dev/staging প্রোফাইলে N=২, `mem_limit: 2g`)।
- **Retry logic:** exponential backoff + jitter, max retry (৩) এর পর task `failed` স্ট্যাটাসে ও dead-letter queue-তে।
- **Circuit breaker:** প্রতি target ও প্রতি proxy-এর জন্য আলাদা circuit breaker (`pybreaker`) — পরপর N ব্যর্থতায় "open", cooldown-এর পর half-open probe।
- **Backpressure:** queue depth মনিটর করা হয়; থ্রেশহোল্ড ক্রস করলে নতুন non-critical task enqueue সাময়িক বন্ধ (graceful degradation)।
- **Graceful shutdown:** worker `SIGTERM` পেলে চলমান context শেষ করে বন্ধ হয়।

_(dev-এ retry/circuit-breaker লজিক একই থাকে, শুধু asyncio-নেটিভভাবে ইমপ্লিমেন্টেড — Appendix A.4।)_

---

## ৮. সিকিউরিটি কনসার্ন

- **Secrets:** কোনো credential কোডে/গিটে হার্ডকোড নয়। dev-এ `.env.local` (gitignored), prod-এ Docker secrets/Vault। রোটেশন পলিসি (৯০ দিন) ডকুমেন্টেড।
- **At-rest এনক্রিপশন:** proxy পাসওয়ার্ড, third-party API key — Fernet symmetric key দিয়ে DB-তে এনক্রিপ্টেড।
- **API সুরক্ষা:** JWT + API key, rate limiting (prod: Redis-ব্যাকড; dev: in-memory)।
- **নেটওয়ার্ক আইসোলেশন:** prod-এ DB/Redis internal network-only।
- **Least privilege:** dashboard read-only DB role আলাদা, worker-এর write role আলাদা।
- **Audit trail:** সেন্সিটিভ অ্যাকশন `audit_logs`-এ persist।
- **Dependency hygiene:** `pip-audit`/Dependabot নিয়মিত স্ক্যান।
- **এথিক্যাল/লিগ্যাল বাউন্ডারি:** কম্পিটিটর অ্যানালাইসিসে target site-এর `robots.txt` ও rate-limit সম্মান করা, per-target rate cap।

---

## ৯. ইমপ্লিমেন্টেশন রোডম্যাপ — ৬টি ফেজ

**কৌশল:** Phase 1-5 সম্পূর্ণ **Appendix A**-এর dev configuration-এ বানানো হবে (SQLite, asyncio-নেটিভ task runner, in-memory dict, টার্মিনাল লগ) — কোনো Docker লাগবে না, ১৬GB RAM মেশিনে সরাসরি `python`/`uvicorn` দিয়ে চলবে। যেহেতু domain/application লেয়ার abstract port-এর উপর লেখা হয় (§৪), Phase 6-এ শুধু প্রোডাকশন adapter (PostgreSQL, Celery+Redis, Grafana/Loki/Prometheus/Sentry) যোগ করলেই একই কোডবেজ প্রোডাকশন-রেডি হয়ে যায় — Phase 1-5-এর বিজনেস লজিক পুনর্লিখন লাগে না।

### **Phase 1 — Foundation & Core Infra (dev-first, zero Docker)**

কাজ:

- Clean Architecture ফোল্ডার স্কেলিটন, `pyproject.toml`, dependency management (venv-ভিত্তিক)।
- `config/` — pydantic-settings, ডিফল্ট `APP_ENV=local`, `DATABASE_URL=sqlite:///local.db`।
- SQLAlchemy মডেল (dialect-agnostic generic `JSON` টাইপ, যাতে পরে Postgres-এ নিরাপদে চলে) + Alembic migration।
- `structlog` + `rich.logging.RichHandler` কনসোল লগিং সেটআপ, basic exception hierarchy।
  **আউটপুট:** `alembic upgrade head` চালালে লোকাল SQLite ফাইলে সব টেবিল তৈরি হয়; অ্যাপ বুট হলে টার্মিনালে কালারড স্ট্রাকচার্ড লগ দেখা যায়; কোনো Docker/container প্রয়োজন নেই।

### **Phase 2 — Proxy Manager মডিউল**

কাজ:

- `domain/entities/Proxy`, `interfaces/ProxyRepository` (port) ডিফাইন।
- `infrastructure/proxy/` — provider adapter, health-check কোরুটিন, রোটেশন স্ট্র্যাটেজি (round-robin + weighted), Fernet এনক্রিপশন।
- Standalone CLI দিয়ে লোকাল SQLite-এর বিপরীতে টেস্ট (কোনো broker/Celery লাগে না)।
  **আউটপুট:** প্রক্সি অ্যাড/টেস্ট/রোটেট লোকাল DB-তে কাজ করে, dead proxy স্বয়ংক্রিয়ভাবে deactivate হয়, ইউনিট টেস্ট পাস করে — সম্পূর্ণ ইনফ্রা-ছাড়া।

### **Phase 3 — Browser Automation Engine**

কাজ:

- Playwright ইনস্টল (শুধু Chromium dev-এ), `infrastructure/browser/engine.py` — context lifecycle, `asyncio.Semaphore(5)` cap (Phase 3-এ এখনো হার্ডকোডেড ৫; Phase 4-এ `runtime_config`-চালিত ডায়নামিক cap-এ রূপান্তরিত হবে, §৫.২)।
- `behaviors/` — human-like mouse/scroll/typing simulation; `stealth/` — fingerprint randomization।
- Proxy Manager ইন্টিগ্রেশন, পারফরম্যান্স মেট্রিক ক্যাপচার → SQLite।
  **আউটপুট:** ম্যানুয়াল রান করলে প্রক্সি দিয়ে টার্গেট সাইট লোড হয়, human-like আচরণ দেখা যায়, একসাথে সর্বোচ্চ ৫টি browser context-এই সীমাবদ্ধ, রেজাল্ট লোকাল DB-তে সেভ হয়।

### **Phase 4 — Task Orchestration ও Fault-Tolerance (asyncio-নেটিভ, Celery ছাড়া)**

কাজ:

- `infrastructure/task_runner/asyncio_runner.py` — in-process `asyncio.Queue` + কনজিউমার কোরুটিন; `TaskRunnerPort` ইন্টারফেস মেনে লেখা হবে যাতে Phase 6-এ Celery adapter সহজে সোয়াপ করা যায়।
- `infrastructure/scheduler/asyncio_scheduler.py` — APScheduler `AsyncIOScheduler`, DB থেকে `schedule_cron` পড়ে একই process-এ periodic trigger (hourly/daily সিমুলেট); enqueue করার আগে `tasks.status = 'active'` চেক (pause/resume, §৫.৩)।
- `infrastructure/config/runtime_config_service.py` — `runtime_config` টেবিল seed (Alembic migration-এ ডিফল্ট রো: `max_concurrent_browsers=5`, `proxy_strategy=round_robin`, `default_timeout_seconds=30`) + write-through cache (§৫.৬)।
- Browser/dispatch কোড আপডেট: প্রতিটি নতুন ব্যাচের শুরুতে `RuntimeConfigPort` থেকে `max_concurrent_browsers` পড়ে ফ্রেশ `asyncio.Semaphore(N)` তৈরি (হার্ডকোডেড Semaphore(5) নয়, §৫.২)।
- Retry logic (ম্যানুয়াল exponential backoff+jitter), circuit breaker (per-proxy/per-target, `pybreaker`) — সরাসরি asyncio কোডে।
- ৫০-ভিজিটর ব্যাচ সিমুলেশন (`RunVisitorBatch` use case, ডিফল্টে ১০ ব্যাচ × ৫ সেশন — cap পরিবর্তন হলে ব্যাচ সংখ্যা/আকার স্বয়ংক্রিয়ভাবে সমন্বিত হয়)।
  **আউটপুট:** টাস্ক নির্ধারিত সময়ে স্বয়ংক্রিয়ভাবে ট্রিগার হয় (একই process-এ), `runtime_config` আপডেট করলে পরবর্তী ব্যাচে নতুন concurrency cap/proxy strategy কার্যকর হয় (অ্যাপ রিস্টার্ট ছাড়াই), `paused` টাস্কে নতুন enqueue বন্ধ হয় কিন্তু চলমান রান নির্বিঘ্নে শেষ হয়, ৫০-ভিজিটর ব্যাচ সিমুলেশন এন্ড-টু-এন্ড কাজ করে, ফল্ট-ইনজেকশন টেস্টে retry/circuit-breaker যাচাই হয় — সব একটিমাত্র Python process-এ, কোনো broker/worker container ছাড়া।

### **Phase 5 — Dashboard/API ও লাইভ স্ট্যাটাস**

কাজ:

- FastAPI REST এন্ডপয়েন্ট (task CRUD, run history, proxy status, metrics query) + JWT/API-key auth।
- WebSocket live status — `infrastructure/status_store/memory_store.py` (in-memory dict) — dev-এ API ও task execution একই process বলে সরাসরি শেয়ারযোগ্য।
- ডায়নামিক-কন্ট্রোল এন্ডপয়েন্ট (§৫.৫, §৫.৬): `POST /api/tasks/{id}/run-now`, `PATCH /api/tasks/{id}/status` (pause/resume/archive), `PATCH /api/targets/{id}` (viewport/headers/timeout), `GET /api/config` ও `PATCH /api/config/{key}` — সব সেন্সিটিভ আপডেট `audit_logs`-এ রেকর্ড হয় (§৮)।
- React ড্যাশবোর্ড (task list, metrics চার্ট, proxy health, লাইভ ভিজিটর-ব্যাচ প্রগ্রেস, concurrency/proxy-strategy কন্ট্রোল, Pause/Resume ও Run Now বাটন)।
  **আউটপুট:** ব্রাউজারে ড্যাশবোর্ড খুলে লাইভ টাস্ক/ব্যাচ স্ট্যাটাস ও হিস্টোরিক্যাল মেট্রিক্স দেখা যায়; concurrency cap/proxy strategy ড্যাশবোর্ড থেকে বদলালে রিস্টার্ট ছাড়াই পরবর্তী ব্যাচে প্রতিফলিত হয়; টাস্ক pause/resume ও ম্যানুয়াল Run Now কাজ করে — সম্পূর্ণ ফ্রেমওয়ার্ক একটিমাত্র `uvicorn` process-এ, কোনো Docker/Postgres/Redis/Celery/Grafana ছাড়াই ১৬GB RAM মেশিনে সম্পূর্ণ ফিচার-সম্পন্ন চলে।

### **Phase 6 — Production Adapters, Deployment Hardening ও Scaling**

কাজ:

- Phase 1-5-এ বানানো abstract port-গুলোর জন্য প্রোডাকশন adapter লেখা হয়:
  - `database`: PostgreSQL adapter (একই SQLAlchemy মডেল, Postgres dialect)।
  - `task_runner`/`scheduler`: Celery + Redis broker adapter, dynamic DB-driven Celery Beat।
  - `status_store`: Redis pub/sub adapter (multi-container cross-process status শেয়ারিং)।
  - `monitoring`: Prometheus/Grafana/Loki/Promtail/Sentry ইন্টিগ্রেশন।
- ফুল প্রোডাকশন `docker-compose.yml` (§৬), worker replica scaling (১০০-concurrent টার্গেটে), nginx/traefik TLS, Docker secrets/Vault।
- ১০০-concurrent লোড টেস্ট, circuit-breaker/retry এন্ড-টু-এন্ড ফল্ট-ইনজেকশন টেস্ট (prod adapter-এ)।
- সিকিউরিটি রিভিউ (dependency scan, secret leak চেক, rate-limit ভেরিফিকেশন, least-privilege DB role অডিট)।
- README + runbook — dev (`APP_ENV=local`) ও prod (`APP_ENV=production`) দুই মোডেই কীভাবে চালাতে হয়।
  **আউটপুট:** একই কোডবেজ দুই মোডে চলে — dev (SQLite + asyncio + in-memory dict + rich console, Docker-ছাড়া) এবং production (PostgreSQL + Celery/Redis + Grafana/Loki, ফুল docker-compose) — প্রোডাকশন-রেডি ডিপ্লয়মেন্ট সম্পন্ন।

---

**ব্যবহারবিধি:** প্রতিটি ফেজ শেষ হলে বলুন _"ফেজ-২ শুরু করো"_ (বা প্রাসঙ্গিক নম্বর) — তখন শুধু ওই ফেজের স্কোপ অনুযায়ী কোড লেখা হবে, আগের ফেজের আউটপুটের উপর ভিত্তি করে।

---

## Appendix A: Local Development Constraints (16GB RAM)

Production স্ট্যাক (PostgreSQL + Redis + Celery worker/Beat + Prometheus + Grafana + Loki/Promtail + Sentry + nginx, সব ডকারে) একসাথে চালালে একটি ১৬GB RAM মেশিনে (Docker Desktop/WSL2 overhead + IDE + ব্রাউজার + একাধিক Playwright Chromium instance) দ্রুত মেমরি চাপে পড়ে। তাই Phase 1-5 সম্পূর্ণভাবে নিচের constraint-গুলো মেনে বানানো হবে — production আর্কিটেকচার (§১-৮) অপরিবর্তিত থাকে, শুধু dev-এ প্রতিটি abstract port-এর একটি হালকা adapter ব্যবহৃত হয় (`APP_ENV=local`)।

### A.1 ডেটাবেজ: SQLite (PostgreSQL-এর বদলে)

- dev-এ `DATABASE_URL=sqlite:///local.db` — কোনো DB container/সার্ভার লাগে না, একটি ফাইল।
- SQLAlchemy মডেলে Postgres-specific টাইপ (`JSONB`, `ARRAY`) নয়, generic `JSON` টাইপ ব্যবহার করা হবে — Postgres-এ JSONB, SQLite-এ TEXT-ব্যাকড JSON-এ ম্যাপ হয়, dialect-agnostic migration নিশ্চিত করতে।
- **সীমাবদ্ধতা:** SQLite-এ native JSONB indexing/concurrent write নেই — সলো dev-এ সমস্যা না, কিন্তু পূর্ণ প্রতিস্থাপন নয়। প্রতিটি Phase merge-এর আগে অন্তত একবার dockerized Postgres-এর বিপরীতে integration smoke test চালানো উচিত (CI-তে), যাতে dialect-নির্ভর বাগ প্রোডাকশনে না পৌঁছায়।

### A.2 কনকারেন্সি: সর্বোচ্চ ৫টি concurrent browser (ডিফল্ট, runtime-configurable)

- `asyncio.Semaphore(N)`, ডিফল্ট `N=5` — মান `runtime_config.max_concurrent_browsers`-এ থাকে, API (`PATCH /api/config/max_concurrent_browsers`) দিয়ে ২ বা ১০-এ বদলানো যায় অ্যাপ রিস্টার্ট ছাড়াই; নতুন মান পরের ব্যাচ থেকে কার্যকর হয় (§৫.২, §৫.৬)। সম্পূর্ণ dev অ্যাপ একটিমাত্র Python process-এ চলে বলে (Celery worker replica নেই, A.4 দেখুন) এটিই একমাত্র concurrency gate — সিস্টেম-ওয়াইড কনকারেন্ট ব্রাউজার নিশ্চিতভাবে ≤N, কোনো multi-process ambiguity নেই। নিচের RAM হিসাব ডিফল্ট N=৫ ধরে করা — N বাড়ালে RAM খরচও সেই অনুপাতে বাড়বে (N=১০ ধরলে ≈১.৫-৩GB), তাই ১৬GB মেশিনে খুব বড় মান (>১০) সেট করার আগে হেডরুম মাথায় রাখা উচিত।
- প্রতিটি Chromium instance ~১৫০-৩০০MB RAM নেয় — ৫টি সমান্তরাল context ≈ ০.৭৫-১.৫GB, ১৬GB মেশিনে নিরাপদ হেডরুম।
- **৫০-ভিজিটর রিয়েল-টাইম সিমুলেশন (UX simulation টাস্ক):** একসাথে ৫০টি context খোলা হবে না। ৫০টি ভার্চুয়াল ভিজিটর সেশনকে **১০টি ব্যাচে ভাগ করে**, প্রতি ব্যাচে ৫টি সেশন সমান্তরালে রান হবে; একটি ব্যাচ শেষ হলে (semaphore slot ফ্রি) পরের ব্যাচ শুরু হয়। প্রতিটি সেশন শেষ হওয়ার সাথে সাথে (ব্যাচ শেষের অপেক্ষা না করে) WebSocket-এ রেজাল্ট push হয়, ফলে ড্যাশবোর্ডে "৫টি করে ধাপে ধাপে এগোচ্ছে" — একটি সততা-বান্ধব UX (ভুয়া concurrency দাবি নয়)। এই batch-orchestration `application/use_cases/RunVisitorBatch`-এ থাকবে, `Semaphore(5)`-নির্ভর — প্রোডাকশনে cap বাড়লে (§৭) একই কোড স্বয়ংক্রিয়ভাবে বড় ব্যাচ হ্যান্ডেল করবে।
- শুধু `playwright install chromium` (Firefox/WebKit বাদ) — ডিস্ক/RAM সাশ্রয়; cross-browser টেস্ট শুধু CI-তে ফুল সেটে চলবে।
- Headless-only dev — GUI browser window এড়ানো হবে যদি না ভিজ্যুয়াল ডিবাগিং দরকার হয়।

### A.3 স্ট্যাটাস-শেয়ারিং: in-memory dict (Redis-এর বদলে)

- `{task_run_id: status}` — একটি সাধারণ Python dict, `infrastructure/status_store/memory_store.py`-তে।
- এটি নির্ভরযোগ্যভাবে কাজ করে **কারণ** A.4-এ Celery সম্পূর্ণ বাদ দেওয়ায় task execution ও FastAPI API একই OS process/একই asyncio event loop-এ চলে — dict-এ কোনো cross-process boundary নেই।
- RAM খরচ ৫-১০MB। WebSocket handler dict poll/watch করে ক্লায়েন্টে পুশ করে।
- প্রোডাকশনে Celery worker আলাদা container হওয়ায় (memory শেয়ার হয় না) এই adapter অকার্যকর — সেখানে Redis pub/sub ব্যবহার হয় (§৫.৫)।

### A.4 টাস্ক এক্সিকিউশন: Celery বাদ, সরাসরি asyncio

- Celery + Redis broker সম্পূর্ণ বাদ dev-এ — কোনো আলাদা worker/broker container নেই।
- Task execution: `asyncio.Queue` + কয়েকটি কনজিউমার কোরুটিন, একই process-এ, `Semaphore(N)`-বাউন্ড (ডিফল্ট N=৫, runtime-configurable, §A.2)।
- Periodic scheduling (hourly/daily): APScheduler-এর `AsyncIOScheduler`, একই event loop-এ চলে — Celery Beat-এর dev-প্রতিস্থাপন।
- এই সিদ্ধান্তের সরাসরি ফলাফল হলো A.3 (in-memory dict কাজ করে) — Celery বাদ দেওয়াই সেই cross-process সমস্যা দূর করে যা Redis-নির্ভরতা তৈরি করত।
- Production-এ Celery+Redis+Beat অপরিবর্তিত থাকে (§৫.৩, §৭) — dev/prod-এর মধ্যে সুইচ হয় `TaskRunnerPort`/`SchedulerPort`-এর dev ও prod adapter দিয়ে, `application` লেয়ারের কোড অপরিবর্তিত।

### A.5 Monitoring: Grafana/Loki বাদ, টার্মিনাল লগ

- dev-এ Prometheus, Grafana, Loki, Promtail, Sentry, Flower — কোনোটাই চলবে না।
- `structlog` + `rich.logging.RichHandler` — কনসোলে কালারড, structured, human-readable লগ (traceback pretty-print, task correlation ID হাইলাইট)। প্রোডাকশনে একই structlog config JSON renderer ব্যবহার করে — শুধু output renderer `APP_ENV` অনুযায়ী সুইচ হয়, লগিং কল-সাইট কোডে কোনো পরিবর্তন লাগে না।

### সারসংক্ষেপ — dev-এ কী লাগে না

SQLite ফাইল, in-process asyncio task runner, in-memory dict, আর টার্মিনাল লগ ব্যবহার করায় dev-এ **PostgreSQL, Redis, Celery, Prometheus, Grafana, Loki/Promtail, Sentry, এমনকি Docker — কোনোটাই লাগে না।** পুরো ফ্রেমওয়ার্ক একটি Python venv-এ `pip install` + `playwright install chromium` + `alembic upgrade head` + `uvicorn app:app --reload` দিয়ে সরাসরি চালানো যায়। Phase 6-এ প্রোডাকশন adapter যোগ হলে তবেই Docker/docker-compose প্রথমবার দরকার হয়।
