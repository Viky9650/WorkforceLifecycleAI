# Security Architecture & Compliance

## Authentication & Authorization

- OAuth 2.0
- JWT-based session management
- Role-Based Access Control (RBAC)
- Principle of least privilege

---

## Data Security

- Encryption at rest
- TLS encryption in transit
- PII compliance
- GDPR aligned
- SOC 2 aligned

---

## Access Governance

Access provisioning is:

- Policy-driven
- Role-based
- Logged with audit_id
- Automatically revoked during offboarding

---

## API Security

- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection
- CORS configuration

---

## Audit Logging

Every onboarding/offboarding run generates:

- Unique audit_id
- Timestamp
- Systems granted/revoked
- Policy source reference

Audit logs are stored under:
store/runs/
