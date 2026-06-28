# Runbook: Connection Pool Exhaustion

This runbook describes the procedure for diagnosing and resolving database connection pool exhaustion issues.

## Symptoms
* Application logs show connection acquisition timeout errors, such as:
  `TimeoutError: Could not acquire a connection from the pool within 5 seconds`.
* API endpoints return HTTP 500 (Internal Server Error) with database pool-related stack traces.
* Database pool utilization alerts are triggered (e.g., pool usage > 80%).
* Sudden spike in API latency across services that interact with the database.

## Diagnosis Steps
1. **Inspect Application Logs:** Run log queries to check the frequency and service location of connection timeout errors. Locate the exact class and method causing the failure (e.g., `PaymentProcessor.process_payment`).
2. **Monitor Pool Metrics:** Check the database dashboard to inspect the current active vs. max connections count.
3. **Check Database Server Status:** Verify if the database server CPU/memory is saturated, or if the database itself is rejecting new connections.
4. **Identify Traffic Spikes:** Correlate database connections with inbound traffic requests. If traffic has spiked significantly (e.g., sales event), the pool configuration may simply be undersized.

## Common Causes
* **Low Pool Configuration:** The `MAX_CONNECTIONS` configuration is too low for the load (e.g., set to 10 during peak events).
* **Connection Leaks:** Connections are acquired but not released back to the pool due to exceptions or missing `finally` blocks in code.
* **Slow DB Queries:** Long-running database operations keep connections checked out for too long, starvng other requests.

## Fix Steps
1. **Scale Pool Size (Immediate):** Increase `MAX_CONNECTIONS` (e.g., 10 -> 100) in the configuration module (such as `utils/db_client.py`) and redeploy the service.
2. **Increase Timeout (Immediate):** Increase the `CONNECTION_TIMEOUT` (e.g., 5s -> 30s) to give threads more buffer time to obtain connections during transient spikes.
3. **Verify Code Connection Management (Short-term):** Wrap database connection requests in context managers or `try...finally` blocks to guarantee `release()` is called.
4. **Tune Queries (Long-term):** Optimize database schemas, add missing indexes, or implement read replicas to reduce query holding time.

## Escalation Guidance
* Escalate to the Database Administration (DBA) team if the database server CPU exceeds 90% or shows replication lag.
* Escalate to the SRE On-call team if scaling the pool size causes downstream database instability.
