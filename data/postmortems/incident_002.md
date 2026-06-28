Title: Memory Leak in Cache Layer. Date: 2024-09-03, Severity: P1, Duration: 45m, MTTR: 45 min.
Summary: OrderService crashed due to OOM. Memory grew from 512MB to 4GB over 6 hours before crash.
Root Cause: Memory leak in cache_client.py — LRU cache never evicting entries because maxsize was set to None.
Timeline: 14:22 memory alert fired (>2GB); 14:35 investigation began; 14:50 growth traced to CacheClient; 15:07 root cause found (maxsize=None).
Fix Applied: utils/cache_client.py line 23, @lru_cache(maxsize=None) → @lru_cache(maxsize=1000).
Action Items: memory usage dashboard for all services; code review checklist requiring maxsize on all LRU caches.
Tags: memory, cache, oom, order-service, p1
