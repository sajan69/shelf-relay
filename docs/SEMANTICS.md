# State and data semantics

ShelfRelay is a server-rendered Django 5.2 LTS application with PostgreSQL
storage. There is one organisation per installation. Authenticated Viewers read
all its catalogue and loan records; Lenders also reserve, hand over, cancel and
receive; Managers additionally create kits and resolve attention flags.
Borrowers are labels, not login accounts. Do not put government identifiers or
contact details in them.

## Availability and handovers

Reservations use half-open intervals: an end time can equal the next start time.
Active reserved/checked-out intervals cannot overlap for the same physical item.
PostgreSQL enforces this with a GiST exclusion constraint and `btree_gist`. A
separate partial unique constraint allows at most one physical checkout per
item, even when reservation windows do not overlap. An overdue physical loan
therefore blocks the next handover. Reservations can still be made for later
windows; they are not a promise that an overdue item will be back.

Application transitions lock the item before its booking in one transaction. A
competing request rechecks committed state after obtaining that lock.
Reservations last at most 30 elapsed days and start now (five-minute entry
tolerance) or within a year. Handover requires start ≤ now < due. Only reserved
bookings can be cancelled; only checked-out bookings can be returned. Expired
uncollected reservations remain reserved until cancelled and are not counted as
physical overdue loans.

The installation time zone defaults to Australia/Brisbane and can be set with
`SHELF_TIME_ZONE`. Django converts local form times to aware timestamps and
refuses ambiguous/nonexistent DST times. Database timestamps use UTC. No
browser-local zone or statutory borrowing policy is inferred.

## Kits, returns and history

Items have 1–20 unique named components, up to 60 characters each. A reservation
snapshots that list. The return form uses indexed choices from that snapshot;
unchecked components are recorded as missing. Empty checklists mean all
components are missing, not a successful complete return. The loan closes and
the item becomes unavailable. Existing reservations remain visible, but their
handover is blocked. Only a manager can clear the flag with a resolution note.
This records a staff assertion, not a safety inspection or proof of physical
recovery. The original missing list and event remain unchanged.

State changes and actor-labelled events commit together. Events are application
history, not an append-only database audit or tamper-proof record against
database administrators. No edit/delete endpoint for loans or historical events
is provided. The interface shows paginated loans and the latest 20
events/bookings on each item.

CSV exports contain at most 10,000 complete loan rows; larger exports are
refused rather than truncated. Unknown checkout/return timestamps stay empty.
Text is quoted and formula-like labels are apostrophe-prefixed after Unicode
compatibility checking; this reduces spreadsheet formula risks but is not
universal spreadsheet protection. Exports contain borrower labels and must be
protected like the database.

## Framework and tooling references

Guidance checked 2 November 2026:
[Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/),
[transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/),
[PostgreSQL exclusion constraints](https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/constraints/),
[Ruff](https://docs.astral.sh/ruff/formatter/),
[djLint](https://djlint.com/docs/configuration/) and
[Prettier](https://prettier.io/docs/install). Django 5.2.18 is the patched LTS
release selected for this project, not the latest feature release. The official
[download page](https://www.djangoproject.com/download/) describes supported
versions.
