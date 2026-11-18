# Employee Support Ticket Application

**Day 4 Lab: Spec-Driven Development & Agentic Coding**  
**Author:** Neha Tothadi (ID: 1899)  
**Date:** 18 Nov 2026  
**Repository:** `https://github.com/SoniaSudireddy/employee-support-ticket-app`

---

## 1. Project Overview & Architecture
The Employee Support Ticket Application is a role-based support desk portal designed according to strict specifications. It enables employees to raise support requests, monitor ticket progress, and contribute comments, while granting support staff administrative authority to review all enterprise requests and transition ticket lifecycle statuses.

- **Frontend:** Single-page responsive interface (`index.html`) featuring real-time role switching, priority/status filtering, and modal comment feeds.
- **Backend Service:** Pure Python service (`app.py`) enforcing business logic, role-based access control (RBAC), and data validation.
- **Test Suite:** Automated unit and regression test suite (`test_tickets.py`) executed with `pytest`.

---

## 2. What AI Generated
- Initial scaffolding for the Ticket data structure and basic CRUD function skeletons.
- Initial HTML/CSS layout for the ticket dashboard table and submission form.
- Baseline test case boilerplate for ticket creation.

---

## 3. What I Manually Changed / Corrected
- **Enforced Strict Status Control:** Removed client-side status dropdowns for employees. The AI originally allowed any user to alter status via the UI; this was corrected to ensure only `support` role users can update status.
- **Enforced Closed Ticket Immutability:** The AI allowed modifying details of closed tickets. Added explicit server-side validation rejecting updates to title, description, category, or priority when `status == 'Closed'`.
- **Enforced Comment Addition to Closed Tickets:** Updated comment logic so that while ticket attributes are immutable once closed, both employees and support staff can still post post-resolution comments.
- **Input Validation Hardening:** Added trim checks and length restrictions (`title <= 100` characters, non-empty whitespace checks).
- **Multi-Tenant Visibility Isolation:** Patched an information disclosure bug where employee users could view other users' tickets by querying specific IDs. Added strict ownership checks (`created_by == user.username`).

---

## 4. What I Checked & Tested
- **Rule 1 (Status Permissions):** Verified employees receive `403 TicketPermissionError` when attempting status changes; support staff successfully transition `Open` → `In Progress` → `Resolved` → `Closed`.
- **Rule 2 (Data Isolation):** Verified employee users (e.g. Ravi) only see their own tickets (#1, #3), while support staff (Kiran) see all 5 tickets.
- **Rule 3 (Closed Ticket Rules):** Verified ticket #5 (Closed) rejects field edits but accepts new comments.
- **Rule 4 (Input Validation):** Verified empty titles, whitespace-only descriptions, and titles > 100 characters are strictly rejected.
- **Automated Tests:** 5/5 automated pytest test cases executed with 100% pass rate.

---

## 5. Known Gaps & Future Roadmap
- **Persistent Storage:** Currently stores state in-memory / JSON dictionary. Future iteration will integrate SQLite / PostgreSQL with SQLAlchemy.
- **Authentication & SSO:** Currently uses role-selection simulation. Future release will integrate corporate SAML/OAuth2 SSO.
- **Email / Webhook Alerts:** Add automated notifications when status changes or new comments are posted.
- **File Attachments:** Add support for uploading screenshot diagnostics on hardware/software tickets.
