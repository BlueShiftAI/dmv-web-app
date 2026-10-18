# Security Limitations

> **Educational prototype — IBM SkillsBuild AI Experiential Learning Lab.**
> Not affiliated with the SCDMV. All registration outcomes are simulated.
> This document lists known security limitations that must be addressed before
> any public-facing or production deployment.

---

## 1. JWT Secret Key

**Risk:** The default `SECRET_KEY` in [`backend/app/config.py`](../backend/app/config.py)
is a plaintext fallback (`"insecure-dev-secret-replace-in-production"`). Any JWT
signed with this key can be forged if the key is known.

**Required action before deployment:**
Generate a strong random key and set it in `.env`:
```bash
openssl rand -hex 32
```
Never commit `.env` to Git.

---

## 2. Authentication Model

**Risk:** The app uses email/password only. There is no:
- Multi-factor authentication (MFA)
- Account lockout after repeated failures
- Password reset flow
- Email verification on registration
- Session revocation (tokens are stateless JWTs with a fixed expiry)

**Required action before deployment:** Integrate a proper identity provider (IdP)
with MFA support. Do not expose this app to untrusted users without it.

---

## 3. No Rate Limiting

**Risk:** All API endpoints are unprotected against brute-force and enumeration
attacks. `/api/auth/login` can be called unlimited times.

**Required action before deployment:** Add rate limiting at the reverse-proxy or
application level (e.g. slowapi, nginx `limit_req`).

---

## 4. No CSRF Protection

**Risk:** The API uses bearer tokens (not cookies), so traditional CSRF is not
applicable, but the CORS policy (`allow_origins` from config) must be tightly
scoped in production. The development default allows `localhost:5173` and
`localhost:3000` only.

**Required action before deployment:** Set `CORS_ORIGINS` to the exact production
domain. Do not use `*`.

---

## 5. File Upload Security

**Risk:**
- Uploaded files are not scanned for malware or malicious content.
- MIME type is validated against both the `Content-Type` header and file magic
  bytes, but this is not a substitute for antivirus scanning.
- Files are stored at `UPLOAD_DIR` outside the web root, which is correct, but
  the storage path is derived from a UUID prefix — not a content hash — so
  storage path guessing is not easily possible but is also not impossible.

**Required action before deployment:** Integrate file scanning (e.g. ClamAV).
Consider storing files in an object store (S3, COS) with signed URLs.

---

## 6. Database TLS

**Risk:** PostgreSQL runs without TLS in the Docker Compose development
configuration. Credentials and query results travel in plaintext between the
backend container and the database container on the Docker network.

**Required action before deployment:** Enable TLS on PostgreSQL and set
`sslmode=require` in `DATABASE_URL`.

---

## 7. SSE Token in URL

**Risk:** The queue SSE stream (`/api/queue/{id}/stream`) accepts the JWT as a
`?token=` query parameter because the browser `EventSource` API cannot set
custom headers. Query parameters may appear in server logs, browser history,
and referrer headers.

**Acceptable for demo:** This is a well-known limitation of `EventSource`.
The fallback to polling means the token-in-URL path is only used when SSE is
actively connected.

**Required action before production over HTTP:** Use WebSockets instead of SSE,
or proxy the SSE connection through a backend component that strips the token
from the URL before logging.

---

## 8. Simulated Government Data

**Risk:** Tax records, ownership records, queue data, and appointment slots are
entirely synthetic. The app does not connect to any SCDMV or York County system.

**This is intentional by design** and is disclosed on every relevant response
via a `simulated: true` flag and a `disclaimer` field.

**Do not:**
- Present outputs of this prototype as authoritative government data.
- Use this prototype for legal vehicle registration or ownership transfer.
- Remove or suppress the `simulated` and `disclaimer` fields from API responses.

---

## 9. Case Lifecycle Is Simulated

**Risk:** The submit → review → approve/reject flow added in the case lifecycle
update does not integrate with any government system. An "approved" status in
this app has no legal meaning.

Every approval notification sent to users explicitly states:
> "This is a demo approval only — bring your documents to the Rock Hill SCDMV
> office to complete the official registration."

---

## 10. No Audit Log Enforcement

**Risk:** The `audit_events` table exists in the schema but is not yet written
to by any router. Sensitive actions (login, document upload, case submission,
staff approval) are not currently audited.

**Required action before deployment:** Instrument audit event writes at each
sensitive action endpoint.

---

## 11. Orchestrate API Key Scope

**Risk:** If `ORCHESTRATE_API_KEY` has broad IBM Cloud permissions, a backend
compromise could expose more than just this application's agent.

**Required action:** Use a minimally-scoped service credential that only grants
access to the specific Orchestrate agent used by this application.

---

*Last updated: Case lifecycle milestone.*
*This document must be reviewed and updated before any deployment outside of a
local development environment.*
