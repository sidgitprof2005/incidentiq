---
type: Runbook
title: "Cascading Timeout Failures"
tags: [cascade, timeout, index, runbook]
resource: incident_004.md
---
# Runbook: Cascading Timeout Failures

This runbook describes the procedure for diagnosing and resolving cascading timeout failures across service dependencies.

## Symptoms
* Failure rate spikes and latency increases across multiple services simultaneously.
* Outage propagates from a downstream dependency (e.g., UserService) to upstream callers (e.g., OrderService, PaymentService).
* Thread pool or connection exhaustion in caller services because they are blocked waiting on slow downstream responses.
* Circuit breaker alerts are triggered, or requests fail fast due to circuit breaker opening.

## Diagnosis Steps
1. **Analyze Distributed Traces:** Trace sample requests using APM tools to construct the dependency call path. Identify the service at the bottom of the tree that is introducing the initial latency.
2. **Inspect Root Service Database Queries:** If the root service is sluggish, check database query metrics. Look for query durations exceeding SLA (e.g., full table scan query times taking > 5 seconds).
3. **Check Indexes:** Run `EXPLAIN` on slow queries to determine if they are missing index coverage (e.g. searching a large user database by email without an index on the email column).
4. **Review Client Timeout Configurations:** Check the HTTP/gRPC client configurations of upstream callers to inspect timeout limits.

## Common Causes
* **Missing Database Indexes:** Large queries executing full table scans, resulting in long execution times.
* **Absence of Circuit Breakers:** Upstream services calling slow downstream services without protection, resulting in thread starvation.
* **Improper Timeout Thresholds:** Timeout settings that are too tight or lack graceful fallbacks, causing cascade failures.
* **Retry Storms:** Services retrying failed calls rapidly without exponential backoff or jitter, overloading downstream systems.

## Fix Steps
1. **Create Index (Immediate database fix):** Generate the missing indexes (e.g., `CREATE INDEX idx_users_email ON users(email)`) on the database server to resolve query slowdown.
2. **Enable Circuit Breakers / Fail-fast (Immediate traffic mitigation):** Open circuit breakers on caller services to stop propagating requests to the degraded downstream service.
3. **Tuning Timeouts and Retries (Short-term):** Adjust timeouts (e.g. increase to 30s) and configure callers to use exponential backoff with jitter.
4. **Implement Fallback Behavior (Short-term):** Provide mock or cached responses in the calling services when downstream calls time out.

## Escalation Guidance
* Escalate to the DBA team if database performance remains degraded after index creation.
* Escalate to the SRE/Network team if service mesh routing issues or packet loss are suspected.
