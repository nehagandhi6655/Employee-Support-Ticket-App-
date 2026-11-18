"""
Employee Support Ticket Application
Day 4 Spec-Driven Development Lab
Author: Neha Tothadi (ID: 1899)
Date: 18 Nov 2026

SECURITY NOTICE (Training/Demo Implementation):
Active user identification is passed via X-User-Name and X-User-Role HTTP headers
(or query parameters) for local simulation and educational demonstration purposes only.
These headers are client-controlled and DO NOT constitute production-ready authentication
or authorization. In production, use cryptographic session tokens, JWTs, or an OAuth2/SSO provider.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
import http.server
import json
import os
import re
import urllib.parse

VALID_CATEGORIES = {"Hardware", "Software", "Network", "Access", "Other"}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_STATUSES = {"Open", "In Progress", "Resolved", "Closed"}

class TicketValidationError(Exception):
    pass

class TicketPermissionError(Exception):
    pass

class TicketNotFoundError(Exception):
    pass

class TicketService:
    def __init__(self):
        self.tickets: Dict[int, Dict[str, Any]] = {}
        self.next_id: int = 1

    def create_ticket(self, title: str, description: str, category: str, priority: str, user: Dict[str, str]) -> Dict[str, Any]:
        """Employee submits a new ticket."""
        if not user or user.get("role") != "employee":
            raise TicketPermissionError("Only employees can submit tickets.")
        
        # Validation
        clean_title = (title or "").strip()
        if not clean_title:
            raise TicketValidationError("Title is required and cannot be empty or whitespace.")
        if len(clean_title) > 100:
            raise TicketValidationError("Title cannot exceed 100 characters.")
        
        clean_desc = (description or "").strip()
        if not clean_desc:
            raise TicketValidationError("Description is required and cannot be empty or whitespace.")
        
        if category not in VALID_CATEGORIES:
            raise TicketValidationError(f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}")
        
        if priority not in VALID_PRIORITIES:
            raise TicketValidationError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")

        today_str = datetime.now().strftime("%d %b %Y")
        ticket_id = self.next_id
        self.next_id += 1

        ticket = {
            "id": ticket_id,
            "title": clean_title,
            "description": clean_desc,
            "category": category,
            "priority": priority,
            "status": "Open",
            "created_by": user["username"],
            "created_date": today_str,
            "last_updated_date": today_str,
            "comments": []
        }
        self.tickets[ticket_id] = ticket
        return ticket

    def list_tickets(self, user: Dict[str, str]) -> List[Dict[str, Any]]:
        """Support staff see all tickets; employees see only their own tickets."""
        if not user:
            raise TicketPermissionError("Authentication required.")
        
        if user.get("role") == "support":
            return list(self.tickets.values())
        elif user.get("role") == "employee":
            return [t for t in self.tickets.values() if t["created_by"] == user["username"]]
        else:
            raise TicketPermissionError("Unknown user role.")

    def get_ticket(self, ticket_id: int, user: Dict[str, str]) -> Dict[str, Any]:
        """Fetch ticket by ID respecting role visibility."""
        if ticket_id not in self.tickets:
            raise TicketNotFoundError(f"Ticket #{ticket_id} not found.")
        
        ticket = self.tickets[ticket_id]
        if user.get("role") == "employee" and ticket["created_by"] != user["username"]:
            raise TicketPermissionError("Forbidden: Employees can only view their own tickets.")
        return ticket

    def update_status(self, ticket_id: int, new_status: str, user: Dict[str, str]) -> Dict[str, Any]:
        """Only support staff can change ticket status."""
        if not user or user.get("role") != "support":
            raise TicketPermissionError("Only support staff can change ticket status.")
        
        if ticket_id not in self.tickets:
            raise TicketNotFoundError(f"Ticket #{ticket_id} not found.")
        
        if new_status not in VALID_STATUSES:
            raise TicketValidationError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")
        
        ticket = self.tickets[ticket_id]
        ticket["status"] = new_status
        ticket["last_updated_date"] = datetime.now().strftime("%d %b %Y")
        return ticket

    def edit_ticket(self, ticket_id: int, title: Optional[str], description: Optional[str], 
                    category: Optional[str], priority: Optional[str], user: Dict[str, str]) -> Dict[str, Any]:
        """Employee can update their ticket details; Closed tickets cannot be edited."""
        ticket = self.get_ticket(ticket_id, user)
        
        if ticket["status"] == "Closed":
            raise TicketValidationError("A Closed ticket cannot be edited.")
        
        if user.get("role") != "employee" or ticket["created_by"] != user["username"]:
            raise TicketPermissionError("Only the ticket creator can edit ticket details.")

        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise TicketValidationError("Title cannot be empty.")
            if len(clean_title) > 100:
                raise TicketValidationError("Title cannot exceed 100 characters.")
            ticket["title"] = clean_title

        if description is not None:
            clean_desc = description.strip()
            if not clean_desc:
                raise TicketValidationError("Description cannot be empty.")
            ticket["description"] = clean_desc

        if category is not None:
            if category not in VALID_CATEGORIES:
                raise TicketValidationError("Invalid category.")
            ticket["category"] = category

        if priority is not None:
            if priority not in VALID_PRIORITIES:
                raise TicketValidationError("Invalid priority.")
            ticket["priority"] = priority

        ticket["last_updated_date"] = datetime.now().strftime("%d %b %Y")
        return ticket

    def add_comment(self, ticket_id: int, comment_text: str, user: Dict[str, str]) -> Dict[str, Any]:
        """Add comment. Allowed even on Closed tickets."""
        ticket = self.get_ticket(ticket_id, user)
        clean_text = (comment_text or "").strip()
        if not clean_text:
            raise TicketValidationError("Comment cannot be empty.")
        
        comment = {
            "id": len(ticket["comments"]) + 1,
            "author": user["username"],
            "role": user.get("role", "employee"),
            "text": clean_text,
            "created_date": datetime.now().strftime("%d %b %Y, %H:%M")
        }
        ticket["comments"].append(comment)
        ticket["last_updated_date"] = datetime.now().strftime("%d %b %Y")
        return comment


def populate_sample_tickets(srv: TicketService) -> None:
    """Pre-seed the 5 specification tickets if service is empty (avoids duplicates on restart)."""
    if srv.tickets:
        return
    u_ravi = {"username": "Ravi", "role": "employee"}
    u_priya = {"username": "Priya", "role": "employee"}
    u_amit = {"username": "Amit", "role": "employee"}
    u_sneha = {"username": "Sneha", "role": "employee"}
    u_support = {"username": "Kiran", "role": "support"}

    srv.create_ticket("Laptop not charging", "My laptop shows 0% even when plugged in", "Hardware", "High", u_ravi)
    t2 = srv.create_ticket("Cannot log in to VPN", "Cisco VPN client throwing error 403", "Network", "High", u_priya)
    srv.update_status(t2["id"], "In Progress", u_support)
    srv.create_ticket("Need access to the shared project folder", "Require read/write access to Q4-Deliverables", "Access", "Medium", u_ravi)
    t4 = srv.create_ticket("Excel keeps crashing on startup", "Excel crashes with runtime error 0x80004005", "Software", "Medium", u_amit)
    srv.update_status(t4["id"], "Resolved", u_support)
    t5 = srv.create_ticket("Request a second monitor", "Need external 24-inch monitor for data analysis", "Hardware", "Low", u_sneha)
    srv.update_status(t5["id"], "Closed", u_support)


class TicketRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Lightweight HTTP Request Handler serving index.html and REST API endpoints.
    Uses standard library http.server (no external dependencies).
    """
    service: TicketService = None

    def get_request_user(self) -> Dict[str, str]:
        """Extract active user identity from request headers or query parameters."""
        username = self.headers.get("X-User-Name", "").strip()
        role = self.headers.get("X-User-Role", "").strip()
        if not username or not role:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if "username" in query and query["username"]:
                username = query["username"][0].strip()
            if "role" in query and query["role"]:
                role = query["role"][0].strip()
        return {"username": username, "role": role}

    def send_json(self, status_code: int, data: Any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-Name, X-User-Role")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code: int, message: str) -> None:
        self.send_json(status_code, {"error": message})

    def read_json_body(self) -> Optional[Dict[str, Any]]:
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            return {}
        try:
            content_length = int(content_length_header)
            raw_data = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_data) if raw_data.strip() else {}
        except Exception:
            return None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-Name, X-User-Role")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Serve static frontend
        if path in ("/", "/index.html"):
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error_json(404, "index.html not found.")
            return

        # API: List tickets
        if path == "/api/tickets":
            user = self.get_request_user()
            if not user["username"] or not user["role"]:
                self.send_error_json(401, "Authentication required: missing X-User-Name or X-User-Role header.")
                return
            try:
                tickets = self.service.list_tickets(user)
                self.send_json(200, tickets)
            except TicketPermissionError as e:
                self.send_error_json(403, str(e))
            return

        # API: Get single ticket by ID
        match = re.match(r"^/api/tickets/(\d+)$", path)
        if match:
            ticket_id = int(match.group(1))
            user = self.get_request_user()
            if not user["username"] or not user["role"]:
                self.send_error_json(401, "Authentication required: missing X-User-Name or X-User-Role header.")
                return
            try:
                ticket = self.service.get_ticket(ticket_id, user)
                self.send_json(200, ticket)
            except TicketNotFoundError as e:
                self.send_error_json(404, str(e))
            except TicketPermissionError as e:
                self.send_error_json(403, str(e))
            return

        self.send_error_json(404, f"Path '{path}' not found.")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API: Create new ticket
        if path == "/api/tickets":
            body = self.read_json_body()
            if body is None:
                self.send_error_json(400, "Invalid JSON in request body.")
                return
            user = self.get_request_user()
            if not user["username"] or not user["role"]:
                self.send_error_json(401, "Authentication required: missing X-User-Name or X-User-Role header.")
                return
            try:
                ticket = self.service.create_ticket(
                    title=body.get("title", ""),
                    description=body.get("description", ""),
                    category=body.get("category", ""),
                    priority=body.get("priority", ""),
                    user=user
                )
                self.send_json(201, ticket)
            except TicketValidationError as e:
                self.send_error_json(400, str(e))
            except TicketPermissionError as e:
                self.send_error_json(403, str(e))
            return

        # API: Update ticket status
        match_status = re.match(r"^/api/tickets/(\d+)/status$", path)
        if match_status:
            ticket_id = int(match_status.group(1))
            body = self.read_json_body()
            if body is None or "status" not in body:
                self.send_error_json(400, "Missing 'status' in request body.")
                return
            user = self.get_request_user()
            if not user["username"] or not user["role"]:
                self.send_error_json(401, "Authentication required: missing X-User-Name or X-User-Role header.")
                return
            try:
                ticket = self.service.update_status(ticket_id, body["status"], user)
                self.send_json(200, ticket)
            except TicketNotFoundError as e:
                self.send_error_json(404, str(e))
            except TicketValidationError as e:
                self.send_error_json(400, str(e))
            except TicketPermissionError as e:
                self.send_error_json(403, str(e))
            return

        # API: Add comment to ticket
        match_comment = re.match(r"^/api/tickets/(\d+)/comments$", path)
        if match_comment:
            ticket_id = int(match_comment.group(1))
            body = self.read_json_body()
            if body is None:
                self.send_error_json(400, "Invalid JSON in request body.")
                return
            comment_text = body.get("text") or body.get("comment", "")
            user = self.get_request_user()
            if not user["username"] or not user["role"]:
                self.send_error_json(401, "Authentication required: missing X-User-Name or X-User-Role header.")
                return
            try:
                comment = self.service.add_comment(ticket_id, comment_text, user)
                self.send_json(201, comment)
            except TicketNotFoundError as e:
                self.send_error_json(404, str(e))
            except TicketValidationError as e:
                self.send_error_json(400, str(e))
            except TicketPermissionError as e:
                self.send_error_json(403, str(e))
            return

        self.send_error_json(404, f"Path '{path}' not found.")

    def do_PATCH(self) -> None:
        """Allow PATCH method for partial updates (e.g. status updates)."""
        self.do_POST()


def run_server(host: str = "127.0.0.1", port: int = 8000, service: Optional[TicketService] = None) -> http.server.ThreadingHTTPServer:
    """Initialize TicketService with sample tickets and start the HTTP server on host:port."""
    if service is None:
        service = TicketService()
        populate_sample_tickets(service)
    TicketRequestHandler.service = service
    server = http.server.ThreadingHTTPServer((host, port), TicketRequestHandler)
    return server


if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = 8000
    server = run_server(HOST, PORT)
    print("=" * 65)
    print("  Employee Support Ticket Application (Day 4 Spec-Driven Lab)")
    print(f"  Server running locally at: http://{HOST}:{PORT}/")
    print("  Bound to: 127.0.0.1 (Loopback only)")
    print("  Press Ctrl+C to stop.")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
        server.server_close()
