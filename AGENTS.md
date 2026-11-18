# AGENTS.md - Employee Support Ticket Application

## Project Overview
A spec-driven support ticket application where employees submit and track tickets, and support staff manage ticket lifecycle statuses.

## Architecture & Technology Stack
- Language: Python 3.14+
- Framework: Lightweight Python Service (`app.py`), HTML5/CSS3/Vanilla JS (`index.html`)
- Testing: `pytest`

## Critical Business Rules (Do Not Violate)
1. **Status Transition Authority:** Only users with `role == 'support'` are permitted to update ticket status (`Open`, `In Progress`, `Resolved`, `Closed`). Employees MUST NEVER be allowed to update ticket status.
2. **Data Isolation (RBAC):** An employee must only see and access tickets created by themselves (`created_by == user.username`). Support staff can view all tickets across all employees.
3. **Immutability of Closed Tickets:** Once a ticket has status `Closed`, its title, description, category, and priority cannot be modified. However, adding comments is still allowed.
4. **Input Constraints:** Ticket title is required, max 100 characters, and cannot be empty or whitespace. Description is required and cannot be empty or whitespace.
5. **Audit Timestamps:** Every modification must update `last_updated_date`.

## Code Style & Safety Guidelines
- Use clean, readable, modular functions with descriptive names and explicit type hints.
- Validate all incoming user data strictly at service boundaries.
- Never hardcode secrets, passwords, or personal credentials.
- Do not introduce heavy external dependencies (e.g. CDNs or bulky frameworks) unless explicitly approved.
- Every functional change must include corresponding automated unit tests.

## Definition of Done
- Feature matches the specification and acceptance criteria exactly.
- All unit and integration tests in `test_tickets.py` pass without errors.
- Unrelated files are untouched and no unexpected diffs are introduced.
