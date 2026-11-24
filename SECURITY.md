# Security Policy

## Security Architecture

ScamGuard is built with defense-in-depth for analyzing untrusted user inputs (URLs, emails, screenshots, PDFs, QR codes, and audio):

- **Authentication & Sessions**: bcrypt password hashing, short-lived JWT access tokens with refresh token rotation, and role-based access control (RBAC).
- **Input & Network Safety**: Server-side URL inspection enforces SSRF protections (blocking private/loopback/link-local ranges), strict request body limits, an 8 MB file upload cap, and per-route rate limiting.
- **Privacy**: Quick checks and Telegram bot scans do not persist submitted messages; saved scans are scoped to their owner.

## Reporting a Vulnerability

If you discover a security vulnerability in ScamGuard, please **do not** open a public GitHub issue. Instead, report it privately via GitHub Security Advisories or email `priyamthakur.cs23@bmsce.ac.in` with:

- A description of the vulnerability and potential impact
- Steps to reproduce or a minimal proof of concept

We will acknowledge receipt and work on a fix promptly.
