# Security

HRRS is a teaching and demonstration system. It is **not** intended for production use.

- The seeded administrator account (`admin@hrrs.test` / `Admin@123`) and the card number `4111 1111 1111 1111` are public demo values. Never reuse them anywhere real.
- Payments go to an in-process gateway stub; no card data leaves the machine.
- Security behaviour that *is* tested (SQL injection, XSS, IDOR, privilege escalation, brute-force lock-out, user enumeration, idempotent payments, security headers) lives in `tests/system/test_api_system.py` under the `security` marker: `pytest -m security`.

If you find a vulnerability in the code, please open an issue using the defect-report form, or contact the author through GitHub.
