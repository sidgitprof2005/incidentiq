Title: Race Condition in Order Processing. Date: 2024-07-20, Severity: P1, Duration: 3h, MTTR: 180 min.
Summary: Duplicate orders created for ~0.3% of users; revenue impact ₹2.1L in duplicate charges.
Root Cause: Race condition in OrderService.create_order() — two concurrent requests for the same user could both pass the duplicate-check and both create orders. Missing DB-level unique constraint and no distributed lock.
Fix Applied: services/order_service.py — added Redis distributed lock before order creation, added unique constraint on (user_id, idempotency_key).
Tags: race-condition, order-service, concurrency, p1
