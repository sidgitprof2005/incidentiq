Title: Cascade Timeout Failure. Date: 2024-06-10, Severity: P0, Duration: 1h 20m, MTTR: 80 min.
Summary: Complete checkout flow down. UserService slowdown cascaded to PaymentService → OrderService → NotificationService.
Root Cause: UserService DB query missing index on email column — full table scan on 10M rows = 8s query time. Downstream services had a 5s timeout, so all calls failed.
Fix Applied: services/user_service.py — added CREATE INDEX idx_users_email ON users(email); changed timeout values across services to 30s with circuit breaker.
Tags: cascade, timeout, index, user-service, p0
