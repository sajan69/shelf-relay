# Security and operational limits

The provided Compose setup is a localhost development/demo installation. It uses
Django's development server, public dummy credentials and a database owner for
migrations. It is not a hardened public service. The PostgreSQL port is not
exposed to the host; the web port binds to 127.0.0.1. Major container tags are
mutable, not immutable deployment evidence. No paid deployment or external
integration is needed.

All catalogue/loan routes require Django authentication and the appropriate
permission. Mutation routes require POST and CSRF; there are no GET mutations.
Passwords, sessions, form validation, template escaping and CSRF are provided by
Django. Application services also check permissions; hiding a button is not the
access boundary. Templates use no JavaScript or third-party assets, and
responses set a restrictive CSP, no-store and frame-denial headers. There is no
telemetry.

Staff can see the organisation's borrower labels and staff event names. Minimise
those labels and do not enter sensitive identifiers. Data is neither anonymised
nor encrypted by this application. PostgreSQL administrators and host
administrators can access or change it. Direct ORM/SQL modifications bypass
application component and transition validation; database constraints defend
specific invariants, not all business rules. This is not a multi-tenant service
or a legal-compliance assessment.

Use a unique secret key and non-demo accounts for retained records. Outside
local HTTP development, secure session/CSRF cookies default on. Public adoption
additionally needs a production server, TLS, trusted host configuration,
least-privilege runtime DB role, login abuse controls, account recovery,
monitoring and tested operational backups. None is implied by a local demo. Do
not expose demo accounts or enable debug on a public host. Follow Django's
[deployment guidance](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
for an actual deployment review.

Retained data belongs in a backed-up PostgreSQL volume. Use PostgreSQL backup
tools, protect dumps and test restoration in a separate database before relying
on them. CSV is an export view and cannot restore users, reservations, item
checklists or history. No backup-restore UI, file uploads, imports, external
mail or safety-critical equipment decisions are provided. Database outages fail
the request; they do not silently replace records with an empty dataset.
Real-world operational validation, human usability studies and accessibility
certification have not been performed.
