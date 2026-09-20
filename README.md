# Service Management System

A Flask-based web application for managing service-center operations, employee records, inventory, purchase orders, and repair tickets. This README is based on a review of the supplied source-code archive; update any workflow details as the application changes.

> **Status:** In development  
> **Version:** [Add version]  
> **Maintainer:** [Add name/team]  
> **Last updated:** [YYYY-MM-DD]

## Contents

- [Overview](#overview)
- [Technology](#technology)
- [Features](#features)
- [Application structure](#application-structure)
- [Data model](#data-model)
- [Routes](#routes)
- [Setup](#setup)
- [Run locally](#run-locally)
- [Configuration and security](#configuration-and-security)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Known limitations](#known-limitations)

## Overview

The Service Management System (SMS) centralizes employee and service-center information and provides workflows for inventory, purchase orders, and repair tickets. Users sign in with a staff ID and password. The Flask application uses server-rendered HTML templates, JavaScript-driven interactions, and a SQLite database.

## Technology

| Layer | Technology found in source |
|---|---|
| Backend | Python, Flask |
| Templates | HTML, Jinja templates |
| Frontend | CSS, JavaScript |
| Database | SQLite (`ServiceManagementSystem.db`) |
| Database access | CS50 SQL library |
| Sessions | Flask-Session (filesystem session storage) |
| Password hashing | Werkzeug security helpers |
| Other dependencies | `hashids`, `pytz`, `requests` |

## Features

### 1. Employee

- Employee listing with active-employee counts grouped by position.
- Create and edit employee records.
- View additional employee details.
- Search employees.
- Staff ID, name, position, department, service-center assignment, and optional contact/details fields are handled in the application.
- Passwords are stored as hashes using Werkzeug password-hashing functions.

### 2. Service Center

- Create service-center records.
- View service-center information and details.
- Search service centers.
- Associate employees and inventory with centers.

### 3. Store and Inventory

- Create inventory/spare-part records.
- View and search inventory.
- Display inventory details and center-related stock information.
- The database/source references center inventory and inventory transaction concepts.
- Purchase-order screens and endpoints support creating/saving, updating, cancelling, searching, and viewing purchase-order details.

### 4. Repair Tickets

- Create repair tickets.
- Search and view repair tickets and their details.
- Update ticket information/status through the ticket update endpoint.
- Repair/inventory-related database references are present in the source.

> **Workflow note:** Approval rules, inventory posting timing, and exact ticket status transitions should be documented here after confirming the desired business process and validating each path in the running application.

## Application structure

The supplied archive contains the following main files and directories:

```text
Service_Management_System/
├── app.py                         # Flask routes and application logic
├── helpers.py                     # Login decorator, mapping and ID helpers
├── requirements.txt               # Python dependencies
├── ServiceManagementSystem.db     # SQLite database
├── static/
│   ├── styles.css
│   └── img/                       # Logo and role images
└── templates/
    ├── layout.html
    ├── index.html
    ├── login.html
    ├── account.html
    ├── employee*.html
    ├── service_center*.html
    ├── inventory*.html
    ├── purchase_order*.html
    └── repair_ticket*.html
```

The archive also includes a `flask_session/` directory with session files. Treat these as runtime data rather than source files; do not commit active session contents.

## Data model

The SQLite database file is `ServiceManagementSystem.db`. Table names referenced by the application include:

| Table | Purpose (inferred from usage/name) |
|---|---|
| `employee` | Employee accounts and profile data |
| `service_centers` | Service-center records |
| `spare_parts` | Inventory item definitions |
| `branch_inventory` | Inventory/stock associated with a center |
| `purchase_orders` | Purchase-order records |
| `purchase_items` | Items included in purchase orders |
| `inventory_transactions` | Inventory transaction records |
| `repair_inventory` | Repair-related inventory records |
| `repair_table` | Repair/ticket records |

This list is based on SQL references in the application and is not a complete schema specification. Add columns, primary/foreign keys, constraints, and relationships after documenting the database schema.

## Routes

The following routes were found in `app.py`. Methods are included where explicitly declared; routes without a method declaration use Flask's default `GET` method.

| Area | Route | Endpoint |
|---|---|---|
| General | `/` | `index` |
| Authentication | `/login` (GET, POST) | `login` |
| Authentication | `/logout` | `logout` |
| Account | `/account` | `account` |
| Employee | `/employee` | `employee` |
| Employee | `/employee_create` (GET, POST) | `employee_create` |
| Employee | `/employee_edit/` (GET, POST) | `employee_edit` |
| Employee | `/more_detail/` | `more_detail` |
| Employee | `/search_employees/` | `search_employees` |
| Employee | `/verify_old_password` (POST) | `verify_old_password` |
| Service center | `/service_center` | `service_center` |
| Service center | `/service_center_create` (GET, POST) | `service_center_create` |
| Service center | `/service_center_details/` (GET, POST) | `service_center_details` |
| Service center | `/search_centers/` | `search_centers` |
| Inventory | `/inventory_management` | `inventory_management` |
| Inventory | `/inventory_details` (GET, POST) | `inventory_details` |
| Inventory | `/create_inventory` (POST) | `create_inventory` |
| Inventory | `/search_inventory/` | `search_inventory` |
| Purchase order | `/purchase_order` | `purchase_order` |
| Purchase order | `/purchaser_order_create` | `purchase_order_create` |
| Purchase order | `/create_POID` (GET) | `create_poid` |
| Purchase order | `/save_POID` (POST) | `save_poid` |
| Purchase order | `/update_POID` (POST) | `update_poid` |
| Purchase order | `/cancel_POID` (POST) | `cancel_poid` |
| Purchase order | `/search_purchase_order/` | `search_purchase_order` |
| Purchase order | `/purchase_order_details/` (GET, POST) | `purchase_order_details` |
| Purchase order | `/search_po_items/` | `search_po_items` |
| Repair ticket | `/repair_ticket` | `repair_tickets` |
| Repair ticket | `/repair_ticket_create` (GET, POST) | `repair_ticket_create` |
| Repair ticket | `/search_repair_tickets/` | `search_repair_tickets` |
| Repair ticket | `/repair_tickets_details/` (GET, POST) | `repair_ticket_details` |
| Repair ticket | `/update_ticket` (POST) | `update_ticket` |

## Setup

### Requirements

- Python 3 (use a version compatible with the installed dependencies)
- pip
- A local copy of the project

### 1. Get the source

```bash
git clone https://github.com/KaungHtetOo-Kai/Service-Management-System.git
cd Service-Management-System
```

Alternatively, extract the provided source ZIP and open the project directory.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The current `requirements.txt` lists:

```text
cs50
Flask
Flask-Session
pytz
requests
hashids
```

### 4. Database

The project is configured to connect to the SQLite database file `ServiceManagementSystem.db` using the CS50 SQL library. Ensure the database file is present in the application working directory and contains the required tables.

## Run locally

From the project directory with the virtual environment activated:

```bash
flask --app app run --debug
```

Then open the local URL printed by Flask (typically `http://127.0.0.1:5000`). The application redirects unauthenticated users to the login page.

> Debug mode is intended for local development only. Do not expose the Flask development server directly to the public internet.

## Configuration and security

Before deployment, review and improve these items:

- Replace the hard-coded Hashids salt with a secret stored in environment configuration.
- Set a strong, private Flask `SECRET_KEY` and verify session-cookie settings for the deployment environment.
- Keep database files, credentials, session data, and personal information out of public source control where appropriate.
- Review authorization checks for every route, including whether users are restricted to their assigned service center and role.
- Use HTTPS and a production-ready WSGI server in production.
- Add CSRF protection for state-changing forms and validate all incoming values server-side.
- Avoid returning raw internal exception details to users; log diagnostic details securely.
- Establish database backup, restore, and migration procedures.

## Testing

No automated test suite was identified in the supplied source archive. Suggested coverage:

- Login success/failure, inactive accounts, logout, and session behavior.
- Employee and service-center create/edit/view/search operations.
- Inventory creation, per-center stock isolation, and quantity validation.
- Purchase-order create/update/cancel and approval/receiving rules, if applicable.
- Repair-ticket creation, search, status changes, and inventory linkage.
- Authorization checks for each role and service center.
- Database consistency when validation or a multi-step operation fails.

Add the project's test command here when tests are introduced (for example, `pytest`).

## Roadmap

Edit this checklist to reflect planned work:

- [ ] Document and enforce role/center permissions for each endpoint
- [ ] Finalize purchase-order approval and receiving workflow
- [ ] Finalize repair-ticket statuses and approval/assignment workflow
- [ ] Document inventory transaction and stock update rules
- [ ] Add automated tests
- [ ] Add database schema/migration documentation
- [ ] Add reporting and export features, if needed
- [ ] Prepare production deployment configuration

## Known limitations / items to verify

- Confirm the exact approval behavior and status transitions for purchase orders and repair tickets.
- Confirm how inventory quantities are changed by purchase receipts, repairs, and transfers.
- Confirm the database schema and relationship constraints; this README lists tables referenced by application SQL but does not replace a schema diagram.
- Review the hard-coded Hashids salt and Flask secret/session configuration before deployment.
- Inventory Transaction between service centers.
- Inventory item edit
- Other admin Utilities such as repair code and error code implementation (create, view, edit), Report Modules for all aspects, phone module with IMEI search etc.
- This system is meant to both a standalone repair shop and an enterprise company level repair system. 

## License

- This project is a opensource code and Everyone are welcome to contribute the system.

## Contact

- **Maintainer:** [Kaung Htet Oo (Kai)]
- **Email:** [kasperkk996@gmail.com]
- **Repository:** https://github.com/KaungHtetOo-Kai/Service-Management-System
