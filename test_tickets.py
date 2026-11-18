"""
Unit and Integration Tests for Employee Support Ticket App
Spec-Driven Testing against Day 4 Acceptance Criteria
"""

import io
import json
from typing import Any, Dict, Optional, Tuple

import pytest
from app import (
    TicketNotFoundError,
    TicketPermissionError,
    TicketRequestHandler,
    TicketService,
    TicketValidationError,
    populate_sample_tickets,
)

# ==============================================================================
# EXISTING UNIT TESTS (PRESERVED INTACT)
# ==============================================================================

@pytest.fixture
def service():
    srv = TicketService()
    # Populate initial sample tickets from specification
    u_ravi = {"username": "Ravi", "role": "employee"}
    u_priya = {"username": "Priya", "role": "employee"}
    u_amit = {"username": "Amit", "role": "employee"}
    u_sneha = {"username": "Sneha", "role": "employee"}
    u_support = {"username": "Kiran", "role": "support"}

    # 1. Laptop not charging (Hardware, High, Open)
    srv.create_ticket("Laptop not charging", "My laptop shows 0% even when plugged in", "Hardware", "High", u_ravi)
    # 2. Cannot log in to VPN (Network, High, In Progress)
    t2 = srv.create_ticket("Cannot log in to VPN", "Cisco VPN client throwing error 403", "Network", "High", u_priya)
    srv.update_status(t2["id"], "In Progress", u_support)
    # 3. Need access to the shared project folder (Access, Medium, Open)
    srv.create_ticket("Need access to the shared project folder", "Require read/write access to Q4-Deliverables", "Access", "Medium", u_ravi)
    # 4. Excel keeps crashing on startup (Software, Medium, Resolved)
    t4 = srv.create_ticket("Excel keeps crashing on startup", "Excel crashes with runtime error 0x80004005", "Software", "Medium", u_amit)
    srv.update_status(t4["id"], "Resolved", u_support)
    # 5. Request a second monitor (Hardware, Low, Closed)
    t5 = srv.create_ticket("Request a second monitor", "Need external 24-inch monitor for data analysis", "Hardware", "Low", u_sneha)
    srv.update_status(t5["id"], "Closed", u_support)
    return srv

def test_rule_1_only_support_can_change_status(service):
    """Rule 1: Only support staff can change a ticket's status."""
    employee_user = {"username": "Ravi", "role": "employee"}
    support_user = {"username": "Kiran", "role": "support"}

    # Employee attempt should fail
    with pytest.raises(TicketPermissionError, match="Only support staff can change ticket status"):
        service.update_status(1, "In Progress", employee_user)

    # Support attempt should succeed
    updated = service.update_status(1, "In Progress", support_user)
    assert updated["status"] == "In Progress"

def test_rule_2_employee_sees_only_own_tickets(service):
    """Rule 2: An employee sees only their own tickets; support staff see all tickets."""
    ravi = {"username": "Ravi", "role": "employee"}
    priya = {"username": "Priya", "role": "employee"}
    support = {"username": "Kiran", "role": "support"}

    # Ravi submitted tickets #1 and #3
    ravi_tickets = service.list_tickets(ravi)
    assert len(ravi_tickets) == 2
    assert all(t["created_by"] == "Ravi" for t in ravi_tickets)

    # Priya submitted ticket #2
    priya_tickets = service.list_tickets(priya)
    assert len(priya_tickets) == 1
    assert priya_tickets[0]["created_by"] == "Priya"

    # Support sees all 5 sample tickets
    all_tickets = service.list_tickets(support)
    assert len(all_tickets) == 5

    # Ravi cannot access Priya's ticket directly
    with pytest.raises(TicketPermissionError, match="Forbidden"):
        service.get_ticket(2, ravi)

def test_rule_3_closed_ticket_cannot_be_edited_except_comments(service):
    """Rule 3: A Closed ticket can't be edited, but comments can still be added."""
    sneha = {"username": "Sneha", "role": "employee"}
    
    # Ticket #5 is Closed
    ticket_5 = service.get_ticket(5, sneha)
    assert ticket_5["status"] == "Closed"

    # Attempting to edit fields fails
    with pytest.raises(TicketValidationError, match="A Closed ticket cannot be edited"):
        service.edit_ticket(5, title="Updated monitor request", description=None, category=None, priority=None, user=sneha)

    # Adding a comment succeeds
    comment = service.add_comment(5, "Received the monitor today, thank you!", sneha)
    assert comment["text"] == "Received the monitor today, thank you!"
    assert len(ticket_5["comments"]) == 1

def test_rule_4_validation_title_and_description(service):
    """Rule 4: Title and description can't be empty or exceed limits."""
    ravi = {"username": "Ravi", "role": "employee"}

    # Empty title
    with pytest.raises(TicketValidationError, match="Title is required"):
        service.create_ticket("", "Some description", "Hardware", "High", ravi)

    # Whitespace only title
    with pytest.raises(TicketValidationError, match="Title is required"):
        service.create_ticket("    ", "Some description", "Hardware", "High", ravi)

    # Title over 100 characters
    long_title = "A" * 101
    with pytest.raises(TicketValidationError, match="Title cannot exceed 100 characters"):
        service.create_ticket(long_title, "Some description", "Hardware", "High", ravi)

    # Empty description
    with pytest.raises(TicketValidationError, match="Description is required"):
        service.create_ticket("Valid Title", "   ", "Hardware", "High", ravi)

def test_valid_ticket_creation_and_defaults(service):
    """Verifies default fields on new ticket creation."""
    ravi = {"username": "Ravi", "role": "employee"}
    t = service.create_ticket("Headset microphone not working", "Clients cannot hear me on Teams calls", "Hardware", "Medium", ravi)
    assert t["id"] == 6
    assert t["status"] == "Open"
    assert t["created_by"] == "Ravi"
    assert t["created_date"] is not None
    assert t["last_updated_date"] is not None
    assert t["comments"] == []


# ==============================================================================
# INTEGRATION TESTS: HTTP REST API & ENDPOINTS
# ==============================================================================

class DummySocket:
    """Simulates socket read/write streams for TicketRequestHandler without requiring raw OS sockets."""
    def __init__(self, req_bytes: bytes):
        self._rfile = io.BytesIO(req_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self._rfile
        return self.wfile

    def sendall(self, b: bytes):
        self.wfile.write(b)


class DummyServer:
    pass


@pytest.fixture
def fresh_service():
    """Provides a fresh TicketService with sample tickets populated."""
    srv = TicketService()
    populate_sample_tickets(srv)
    return srv


def send_http_request(
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    service: Optional[TicketService] = None,
) -> Tuple[int, Any]:
    """
    Executes an HTTP request directly through TicketRequestHandler.
    Tests full HTTP request/response parsing, headers, body serialization, and status codes.
    """
    if service is None:
        service = TicketService()
        populate_sample_tickets(service)
    TicketRequestHandler.service = service

    body_bytes = b""
    req_headers = headers.copy() if headers else {}
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        if "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
        req_headers["Content-Length"] = str(len(body_bytes))

    header_lines = [f"{k}: {v}" for k, v in req_headers.items()]
    headers_str = "\r\n".join(header_lines)
    if headers_str:
        headers_str = "\r\n" + headers_str

    raw_req = f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1{headers_str}\r\n\r\n".encode("utf-8") + body_bytes
    sock = DummySocket(raw_req)
    TicketRequestHandler(sock, ("127.0.0.1", 12345), DummyServer())

    res_bytes = sock.wfile.getvalue()
    head, _, body = res_bytes.partition(b"\r\n\r\n")
    status_line = head.decode("utf-8", errors="replace").split("\r\n")[0]
    status_code = int(status_line.split(" ")[1])

    try:
        parsed_body = json.loads(body.decode("utf-8"))
    except Exception:
        parsed_body = body.decode("utf-8", errors="replace")

    return status_code, parsed_body


def test_sample_tickets_no_duplicates():
    """Verify that calling populate_sample_tickets repeatedly does not create duplicate entries."""
    srv = TicketService()
    populate_sample_tickets(srv)
    assert len(srv.tickets) == 5
    # Call a second time
    populate_sample_tickets(srv)
    assert len(srv.tickets) == 5


def test_web_serves_index_html():
    """Test that GET / serves index.html with 200 OK and expected HTML content."""
    status, body = send_http_request("/")
    assert status == 200
    assert "Support Desk Portal" in body
    assert "Raise Support Ticket" in body


def test_web_missing_auth_headers_returns_401():
    """Test that API requests missing user identification receive 401 Unauthorized."""
    status, body = send_http_request("/api/tickets", method="GET")
    assert status == 401
    assert "Authentication required" in body.get("error", "")


def test_web_employee_tickets_isolation_rule_2(fresh_service):
    """Rule 2 via API: Employee receives only their own tickets."""
    headers = {"X-User-Name": "Ravi", "X-User-Role": "employee"}
    status, tickets = send_http_request("/api/tickets", method="GET", headers=headers, service=fresh_service)
    assert status == 200
    assert len(tickets) == 2
    assert all(t["created_by"] == "Ravi" for t in tickets)


def test_web_support_sees_all_tickets_rule_2(fresh_service):
    """Rule 2 via API: Support staff receives all tickets across all employees."""
    headers = {"X-User-Name": "Kiran", "X-User-Role": "support"}
    status, tickets = send_http_request("/api/tickets", method="GET", headers=headers, service=fresh_service)
    assert status == 200
    assert len(tickets) == 5


def test_web_employee_cannot_view_other_ticket_rule_2(fresh_service):
    """Rule 2 via API: Employee requesting an ID belonging to another user gets 403 Forbidden."""
    headers = {"X-User-Name": "Ravi", "X-User-Role": "employee"}
    # Ticket #2 belongs to Priya
    status, res = send_http_request("/api/tickets/2", method="GET", headers=headers, service=fresh_service)
    assert status == 403
    assert "Forbidden" in res.get("error", "")


def test_web_employee_creates_ticket_rule_4(fresh_service):
    """Rule 4 via API: Employee creates a valid ticket."""
    headers = {"X-User-Name": "Ravi", "X-User-Role": "employee"}
    payload = {
        "title": "Dual monitor HDMI cable broken",
        "description": "HDMI cable is damaged and screen is flickering constantly",
        "category": "Hardware",
        "priority": "High"
    }
    status, ticket = send_http_request("/api/tickets", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 201
    assert ticket["title"] == "Dual monitor HDMI cable broken"
    assert ticket["status"] == "Open"
    assert ticket["created_by"] == "Ravi"
    assert ticket["id"] == 6


def test_web_create_ticket_validation_errors_rule_4(fresh_service):
    """Rule 4 via API: Empty title or description triggers 400 Bad Request."""
    headers = {"X-User-Name": "Ravi", "X-User-Role": "employee"}
    # Empty title
    status, res = send_http_request("/api/tickets", method="POST", data={"title": "  ", "description": "desc", "category": "Hardware", "priority": "Low"}, headers=headers, service=fresh_service)
    assert status == 400
    assert "Title is required" in res.get("error", "")

    # Title exceeding 100 characters
    status, res = send_http_request("/api/tickets", method="POST", data={"title": "A" * 105, "description": "desc", "category": "Hardware", "priority": "Low"}, headers=headers, service=fresh_service)
    assert status == 400
    assert "Title cannot exceed 100 characters" in res.get("error", "")

    # Invalid category
    status, res = send_http_request("/api/tickets", method="POST", data={"title": "Valid title", "description": "desc", "category": "NonExistent", "priority": "Low"}, headers=headers, service=fresh_service)
    assert status == 400
    assert "Invalid category" in res.get("error", "")


def test_web_non_employee_cannot_create_ticket(fresh_service):
    """Rule 1 / RBAC via API: Support staff cannot create tickets."""
    headers = {"X-User-Name": "Kiran", "X-User-Role": "support"}
    payload = {
        "title": "Support created ticket",
        "description": "Attempting creation as support role",
        "category": "Software",
        "priority": "Low"
    }
    status, res = send_http_request("/api/tickets", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 403
    assert "Only employees can submit tickets" in res.get("error", "")


def test_web_support_updates_status_rule_1(fresh_service):
    """Rule 1 via API: Support staff updates status successfully."""
    headers = {"X-User-Name": "Kiran", "X-User-Role": "support"}
    payload = {"status": "In Progress"}
    status, res = send_http_request("/api/tickets/1/status", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 200
    assert res["status"] == "In Progress"


def test_web_employee_cannot_update_status_rule_1(fresh_service):
    """Rule 1 via API: Employee attempting status update receives 403 Forbidden."""
    headers = {"X-User-Name": "Ravi", "X-User-Role": "employee"}
    payload = {"status": "Resolved"}
    status, res = send_http_request("/api/tickets/1/status", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 403
    assert "Only support staff can change ticket status" in res.get("error", "")


def test_web_comments_allowed_on_closed_ticket_rule_3(fresh_service):
    """Rule 3 via API: Adding a comment to a Closed ticket succeeds."""
    headers = {"X-User-Name": "Sneha", "X-User-Role": "employee"}
    payload = {"text": "Following up to confirm the monitor is working properly."}
    # Ticket #5 is Closed
    status, comment = send_http_request("/api/tickets/5/comments", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 201
    assert comment["author"] == "Sneha"
    assert comment["text"] == "Following up to confirm the monitor is working properly."


def test_web_empty_comment_validation(fresh_service):
    """Comment validation via API: Empty comment returns 400 Bad Request."""
    headers = {"X-User-Name": "Sneha", "X-User-Role": "employee"}
    payload = {"text": "   "}
    status, res = send_http_request("/api/tickets/5/comments", method="POST", data=payload, headers=headers, service=fresh_service)
    assert status == 400
    assert "Comment cannot be empty" in res.get("error", "")


def test_web_nonexistent_ticket_returns_404(fresh_service):
    """Not found check via API: Non-existent ticket returns 404."""
    headers = {"X-User-Name": "Kiran", "X-User-Role": "support"}
    status, res = send_http_request("/api/tickets/9999", method="GET", headers=headers, service=fresh_service)
    assert status == 404
    assert "not found" in res.get("error", "").lower()


def test_web_cors_options():
    """Verify that preflight OPTIONS request returns 204 with CORS headers."""
    status, _ = send_http_request("/api/tickets", method="OPTIONS")
    assert status == 204
