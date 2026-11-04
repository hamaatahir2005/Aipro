# Pocket Option integration review — 2026-11-04

Reviewed primary sources:
- https://pocketoption.com/en/public-offer/
- https://pocketoption.com/blog/en/interesting/trading-platforms/automated-trading-systems/
- https://pocketoption.com/blog/en/interesting/trading-platforms/chatgpt-trading-bot/

The public offer describes the company's terminal and server. Educational articles discuss automation and official tools, but the reviewed material does not establish a documented third-party order API, developer credentials, scopes, sandbox, or permission for this application. This is an **unverified integration**, not proof that no private partner API exists. Written broker confirmation and current official developer documentation are required before implementing execution.

The PocketOption adapter always rejects orders. No session cookies, private endpoints, browser automation, deposits, or withdrawals are implemented. Twelve Data quotations are independent and must never be represented as Pocket Option OTC prices or executable broker quotes. No regional authorization is inferred.
