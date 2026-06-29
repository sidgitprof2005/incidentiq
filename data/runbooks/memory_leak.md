---
type: Runbook
title: "Out of Memory (OOM) and Memory Leaks"
tags: [memory, cache, oom, runbook]
resource: incident_002.md
---
# Runbook: Out of Memory (OOM) and Memory Leaks

This runbook describes the procedure for diagnosing and resolving memory leaks and OOM crashes.

## Symptoms
* Containers/services restart unexpectedly, with logs showing `Exit Code 137` (OOM Killed).
* Memory metrics show a steady linear increase (monotonically increasing) over time without returning to the baseline.
* Logs contain `MemoryError` exceptions.
* Degradation in response times (latency spikes) due to high garbage collection overhead (GC thrashing) before the service crashes.

## Diagnosis Steps
1. **Analyze APM Memory Charts:** Check container/process memory consumption over the last 6 to 24 hours. A steady growth slope indicates a memory leak.
2. **Identify Recently Deployed Features:** Check recent Git commits for cache modifications, new global collections, or large object allocations.
3. **Profile Heap Memory:** Use memory profiling tools (such as Python's `tracemalloc` or `memory_profiler`) in staging to track down the source of memory growth.
4. **Inspect Cache Client Configurations:** Check cache initializations. Look for unbounded structures (e.g., `@lru_cache(maxsize=None)` or dictionary structures acting as caches without expiration/eviction).

## Common Causes
* **Unbounded Caching:** Caches that grow indefinitely without eviction rules (e.g. `maxsize=None`).
* **Global Variables & Collections:** Objects appended to class-level lists or global dicts that are never cleared.
* **Unreleased System Resources:** Files, sockets, or db connections left open.

## Fix Steps
1. **Rolling Restart (Immediate mitigation):** Restart the affected instances to clear memory and buy time for code-level investigation.
2. **Limit Cache Capacity (Code Fix):** Replace unbounded caches with bounded ones (e.g., change `@lru_cache(maxsize=None)` to `@lru_cache(maxsize=1000)`).
3. **Increase Memory Allocations (Short-term):** Increase Kubernetes/Container memory limits to slow down crash frequency if immediate code fix deployment is not possible.
4. **Implement Garbage Collection Hooks:** Force manual collection or profile cycles in staging to ensure objects are freed.

## Escalation Guidance
* Escalate to the Infrastructure/SRE team if container configuration scaling fails.
* Escalate to the Lead Developer or Architect if profiling does not reveal the leak origin.
