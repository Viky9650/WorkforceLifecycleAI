# Employee Offboarding Guide

## Purpose

The offboarding process ensures:

- Secure revocation of all system access
- Knowledge transfer to relevant teams
- Compliance with security policies
- Proper documentation and audit logging

---

## Offboarding Workflow

### Step 1 – HR Initiates Offboarding

Input:
- Employee name
- Role
- Last working day
- Exit interview notes

---

### Step 2 – Knowledge Transfer Capture

The system captures:

- Project ownership
- System knowledge
- Runbooks
- Dashboard links
- Incident history
- Deployment procedures

KT is stored as JSON and indexed into the RAG system.

---

### Step 3 – Access Revocation

Systems revoked:

- IAM account
- Jira project access
- GitHub organization membership
- Confluence space access
- ServiceNow account
- Outlook mailbox access
- Microsoft Teams workspace
- DevOps Deploy App access

All actions generate:

- audit_id
- timestamp
- revocation summary

---

## Compliance Benefits

- Prevents access leakage
- Reduces insider risk
- Ensures audit readiness
- Maintains operational continuity

---

## Audit Trail

All offboarding events are stored under:

store/runs/

Each record includes:

- Employee name
- Role
- Systems revoked
- Knowledge captured
- Audit ID
- Timestamp
