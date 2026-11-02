# Verification and worked outcomes

Verification uses a fictional two-component camera kit and synthetic staff
accounts. It does not measure actual club adoption, staff time saved or
equipment safety.

## Reproduce the handover

The README demo creates three kits and a camera reservation for `Demo · Alex`.
Open the camera, record its handover, then choose **Receive return**. Tick
everything except **Charger** and record the return. The loan closes with
Charger missing; the kit is unavailable for new reservations and existing
reservations cannot be handed over. A Manager can enter a resolution note and
clear the attention flag. The original missing-component list remains visible in
the returned loan.

For a complete return, tick every component: the kit becomes available for
another reservation without an attention flag. If nothing is ticked, every
component is recorded as missing. Recording a return is not a safety or
condition inspection.

## Test method and observed results

The
[verification run](https://github.com/sajan69/shelf-relay/actions/runs/41405617912)
at
[d6fb763](https://github.com/sajan69/shelf-relay/commit/d6fb76320a410df94d47cb4978660bb2ec06a125)
passed all four jobs on 2 November 2026: code quality, PostgreSQL 16, PostgreSQL
18 and the Docker Compose demo. Later commits rerun the checks; this link
identifies the run supporting the results below.

| Workload                                                                              | Observed outcome                                                                                                           |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 27 backend test methods, each on PostgreSQL 16.15 and 18.6                            | Passed with Django 5.2.18 and Python 3.12 on GitHub-hosted Ubuntu runners                                                  |
| Two simultaneous requests for the same reservation window, independent DB connections | One saved reservation, one refusal, one reservation event                                                                  |
| Two simultaneous handovers of one reservation                                         | One handover event; the other request refused                                                                              |
| Direct ORM inserts bypassing service overlap checks                                   | PostgreSQL refused overlapping active reservations, nonpositive windows and a second physical checkout                     |
| Injected event-write exception                                                        | Booking creation or handover state change rolled back; no partial successful transition                                    |
| Three Chromium browser scenarios                                                      | Kit creation, reservation/handover/incomplete return/resolution and mobile search completed against the running Django app |
| 390-pixel browser view                                                                | No page-level horizontal overflow or external requests in the exercised catalogue/search flow                              |
| Fresh Docker Compose installation                                                     | Image built, migrations and fictional demo succeeded, web health check passed and login page served                        |

The 27 backend methods are 5 form, 11 workflow, 7 HTTP, 2 concurrency and 2
setup methods. Repeating them on two PostgreSQL versions is not 54 distinct test
designs. The three browser methods are additional end-to-end cases. Checks cover
permission refusals, CSRF and POST-only mutation, escaped labels, unknown
checklist choices, CSV unknown values/formula mitigation, adjacent windows,
future checkout refusal, incomplete-kit blocking, demo reseed refusal and
validated non-admin staff creation.

Quality CI runs Ruff lint/format, djLint lint/template formatting, Prettier
checks, pinned dependency consistency, model/migration drift checks and
markdown-link-check against repository links and external documentation. Link
errors fail the job; transient network refusals are not silently counted as
valid links. No general vulnerability assessment or accessibility certification
is inferred.

Docker CI also exercises `pg_dump`/`pg_restore` in a separate synthetic database
and compares every ordered row in seven application/account tables without
logging their contents. This checks the supplied fixture's restore path, not
arbitrary production backup retention, recovery objectives or administrator
procedures. The original database is not replaced. CI containers and their
test-only volume are removed after the job; users' retained Compose volumes are
not part of that test.

## Evidence limits

Desktop and mobile screenshots from the browser suite were visually inspected.
The browser tests use Chromium, not every browser or native mobile device.
Docker and real PostgreSQL tests execute in CI; local checks do not imply a
local Docker or PostgreSQL installation. Browser screenshots are CI artifacts
retained for seven days. All recorded names and equipment are fictional.

Two-request races are targeted integrity checks, not a load test, latency
benchmark or proof against every possible interleaving. Mutable container tags,
shared runners and platform versions limit exact environment replication. Human
usability studies, network deployment, security review, real equipment
calibration, production recovery and real-world operational reliability are
outside this evidence. No users, business savings, public deployment or
compliance approval are claimed.
