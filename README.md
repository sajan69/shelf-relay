# ShelfRelay

A shared equipment-lending application for small clubs and studios. Reserve a
camera, record its handover and check each piece back in. Incomplete kit returns
stay unavailable until a manager records a resolution.

## Local demo

Use Docker with Compose. The supplied configuration binds the app to localhost
and contains **public, local-demo-only credentials**. Do not expose it on a
network.

```sh
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py demo --demo
docker compose up -d web
```

Open `http://127.0.0.1:8000`. Sign in as `demo-manager` or `demo-lender` with
password `demo-only-change-me`. The fictional camera reservation starts
immediately and is due the next day. The demo command refuses an existing
installation; it does not reset data. Stop containers with
`docker compose down`; the named database volume remains. Do not delete that
volume unless you intend to delete its records.

## Use

Search **The shelf**, open a kit and reserve its time for a minimal borrower
display name. **Record handover** is available only within that window and
refuses an item already out or needing attention. **Receive return** records
checked components; unchecked pieces keep the kit unavailable. A manager can
resolve the attention flag with a note while retaining the original
incomplete-return record.

**Loans** separates physical overdue loans from uncollected reservations and
exports CSV. Viewer, Lender and Manager permission groups are configured by
`python manage.py setup_roles`; accounts and group assignments are managed
through Django's management shell. This installation serves one organisation. It
has no public signup, payments, borrower messages, photos or safety
certification.

## Development and checks

Use Python 3.12, Node 24 and a disposable PostgreSQL 16 or 18 database. Supply
`DJANGO_SECRET_KEY`, `PGHOST`, `PGUSER`, `PGPASSWORD` and `PGDATABASE` as
environment variables. Set `DJANGO_DEBUG=1` for local HTTP only. The database
user needs migration rights, including installation of `btree_gist`; tests also
require `CREATEDB`.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
npm ci --ignore-scripts
ruff check .
ruff format --check .
djlint lending/templates --check
djlint lending/templates --lint
npm run format:check
npm run links
python manage.py test --exclude-tag browser
python -m playwright install --with-deps chromium
python manage.py test --tag browser
```

Use `ruff format .`, `djlint lending/templates --reformat` and `npm run format`
to format Python, Django templates and supported static/documentation files,
respectively. Prettier deliberately excludes Django templates, which djLint
handles. Dependencies are pinned; Django supplies authentication, CSRF, forms
and ORM transactions rather than custom substitutes. Node tools are
development-only.

See [state and data semantics](docs/SEMANTICS.md) and
[security and operational limits](docs/SECURITY.md). Fixtures and automated
tests use fictional records. A successful test run is not a claim of production
adoption or equipment safety. Docker and real-browser checks must be run in an
environment that supports them; no local execution of those checks is implied by
these commands.
