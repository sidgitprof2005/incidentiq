---
type: Incident
title: "Cascade Timeout Failure"
date: 2024-06-10
severity: P0
duration: "1h 20m"
mttr: 80
tags: [cascade, timeout, index, user-service, p0]
resource: services/user_service.py
---
Summary: Complete checkout flow down. UserService slowdown cascaded to PaymentService → OrderService → NotificationService.
Root Cause: UserService DB query missing index on email column — full table scan on 10M rows = 8s query time. Downstream services had a 5s timeout, so all calls failed.
Fix Applied: services/user_service.py — added CREATE INDEX idx_users_email ON users(email); changed timeout values across services to 30s with circuit breaker.
