Title: Payment Service Outage. Date: 2024-11-15, Severity: P0, Duration: 2h 14m, MTTR: 134 min.
Summary: Payment processing failed for 40% of users between 02:13 and 04:27 UTC.
Root Cause: Connection pool exhaustion in PaymentService. DatabasePool max_connections was set to 10, insufficient for Black Friday traffic spike (8x normal load).
Timeline: 02:13 alerts fired (payment_success_rate < 60%); 02:31 on-call paged; 02:45 connection timeout errors found in logs; 03:10 root cause identified (pool exhausted); 03:45 fix tested in staging; 04:27 fix deployed, recovery confirmed.
Root Cause Analysis: File services/payment_service.py, class PaymentProcessor, method process_payment() calls db_client.get_connection() which hit MAX_CONNECTIONS=10.
Fix Applied: utils/db_client.py line 47 MAX_CONNECTIONS 10→100, line 52 CONNECTION_TIMEOUT 5→30.
Action Items: add connection pool utilization alert at 80%; load test before major traffic events; implement pool auto-scaling.
Tags: payment, database, connection-pool, black-friday, p0
