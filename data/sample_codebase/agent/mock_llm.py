"""
Mock LLM and Embeddings implementation for IncidentIQ.
Provides offline simulation of OpenAIEmbeddings and ChatAnthropic (claude-sonnet-4-6).
Allows complete testing and execution without paid API keys.
"""

import os
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

logger = logging.getLogger(__name__)


class MockEmbeddings(Embeddings):
    """
    Simulated embeddings provider.
    Generates deterministic vectors of dimension 1536 based on string hashing.
    Runs entirely locally, requires 0 API quota.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]
        
    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)
        
    def _embed(self, text: str) -> List[float]:
        # Generate a deterministic seed from the text hash
        h = hashlib.sha256(text.encode('utf-8')).digest()
        # Initialize a simple pseudo-random sequence of floats of size 1536
        seed = int.from_bytes(h[:4], byteorder='big')
        
        # Linear Congruential Generator (LCG) to construct deterministic floats
        a = 1103515245
        c = 12345
        m = 2**31
        
        vector = []
        val = seed
        for _ in range(1536):
            val = (a * val + c) % m
            vector.append((val / m) - 0.5)  # Normalise between -0.5 and 0.5
            
        return vector


class MockChatAnthropic(BaseChatModel):
    """
    Simulated ChatAnthropic chat model (claude-sonnet-4-6).
    Analyzes messages and returns highly realistic responses for the 3 SRE incident examples.
    """
    model_name: str = "mock-claude-sonnet-4-6"
    model: Optional[str] = None

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        # Concatenate all messages (system, human, etc.) to get full context
        prompt = ""
        for m in messages:
            prompt += m.content + "\n"
            
        response_text = self._get_response(prompt)
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "mock-chat-anthropic"

    def _get_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        # 1. Verification Check
        if "verification assistant" in prompt_lower or "sufficient information" in prompt_lower:
            return '{"is_grounded": true, "confidence_score": 0.98, "ungrounded_claims": []}'

        # 2. Planning Check
        if "planning an incident investigation" in prompt_lower or "investigation steps" in prompt_lower:
            # Extract user query
            user_query = prompt_lower.split("user incident query:")[-1] if "user incident query:" in prompt_lower else prompt_lower
            if "payment" in user_query or "servicea" in user_query:
                return (
                    '[\n'
                    '  "Step 1: Check code chunks for DatabasePool and db_client settings.",\n'
                    '  "Step 2: Search similar incidents for connection pool exhaustion or P0 outages.",\n'
                    '  "Step 3: Analyze the call graph around PaymentProcessor and DatabasePool to find callers.",\n'
                    '  "Step 4: Check if db_client connection limits were recently edited in db_client.py."\n'
                    ']'
                )
            elif "oom" in user_query or "serviceb" in user_query or "cache" in user_query:
                return (
                    '[\n'
                    '  "Step 1: Check memory usage stats and container OOM exit code details.",\n'
                    '  "Step 2: Check cache client class and decorators in cache_client.py.",\n'
                    '  "Step 3: Search similar past incidents for memory leaks or CacheClient failures.",\n'
                    '  "Step 4: Formulate LRU cache limit fix."\n'
                    ']'
                )
            elif "user" in user_query or "latency" in user_query or "timeout" in user_query or "servicec" in user_query:
                return (
                    '[\n'
                    '  "Step 1: Scan services/user_service.py for authenticate implementation.",\n'
                    '  "Step 2: Search similar incidents for cascade timeouts or database latency.",\n'
                    '  "Step 3: Analyze the call graph around UserService to find callers.",\n'
                    '  "Step 4: Check index settings on the users table in database client."\n'
                    ']'
                )
            else:
                return (
                    '[\n'
                    '  "Step 1: Scan services/order_service.py for duplicate checks.",\n'
                    '  "Step 2: Search similar incidents for order race conditions.",\n'
                    '  "Step 3: Analyze call graph dependencies for callers."\n'
                    ']'
                )

        # 3. Replanning Check
        if "replanning assistant" in prompt_lower or "alternative queries" in prompt_lower:
            return '["Step 1: Audit connections in db_client.py", "Step 2: Check PaymentService.process_payment connection checkout"]'

        # 4. Anonymization Check
        if "anonymization utility" in prompt_lower or "anonymize this query" in prompt_lower:
            # Extract target query
            target_query = prompt_lower.split("anonymize this query:")[-1] if "anonymize this query:" in prompt_lower else prompt_lower
            if "payment" in target_query:
                return (
                    '{"anonymized_query": "ServiceA 503 errors, 40% failure rate, connection timeouts in logs", '
                    '"entity_map": {"ServiceA": "PaymentService"}}'
                )
            elif "oom" in target_query or "memory" in target_query or "cache" in target_query:
                return (
                    '{"anonymized_query": "ServiceB OOM crash, memory grew from 512MB to 4GB overnight", '
                    '"entity_map": {"ServiceB": "OrderService"}}'
                )
            elif "user" in target_query or "latency" in target_query or "timeout" in target_query:
                return (
                    '{"anonymized_query": "ServiceC latency timeouts, user service authentication slowdown", '
                    '"entity_map": {"ServiceC": "UserService"}}'
                )
            elif "duplicate" in target_query or "race" in target_query:
                return (
                    '{"anonymized_query": "Duplicate orders being created for some users in ServiceB, race condition suspected", '
                    '"entity_map": {"ServiceB": "OrderService"}}'
                )
            else:
                return '{"anonymized_query": "ServiceA failed with error code 500", "entity_map": {"ServiceA": "PaymentService"}}'

        # 5. Summarization Check (during build_stores.py)
        if "purpose, key components, and dependencies" in prompt_lower:
            if "payment_service.py" in prompt_lower:
                return "This file implements PaymentProcessor to coordinate payment operations. It verifies client balances and logs transactions using DatabasePool. It depends on utils/db_client and utils/cache_client."
            elif "order_service.py" in prompt_lower:
                return "This file contains OrderService managing creation and cancellation of client orders. It collaborates with PaymentProcessor and NotificationService to process payments and send receipts. It stores orders in a dictionary database."
            elif "user_service.py" in prompt_lower:
                return "This file defines UserService containing user account validation and profile updates. It handles password hashes and updates fields like name and email. It acts as the identity verification provider."
            elif "notification_service.py" in prompt_lower:
                return "This file defines NotificationService sending notifications via email or SMS. It logs dispatch details and formats outgoing messages. It operates as a communication microservice."
            elif "db_client.py" in prompt_lower:
                return "This file sets up DatabasePool managing database connection objects. It allocates database sessions and releases them to avoid connection leaks. It controls max connection limits."
            elif "cache_client.py" in prompt_lower:
                return "This file contains CacheClient implementing cache settings using an LRU cache. It handles retrieval and invalidation of in-memory keys. It has maxsize limits."
            return "This module contains helper utilities and model classes supporting application flow and databases connections."

        # 6. Synthesis Check
        if "synthesizing" in prompt_lower or "synthesize" in prompt_lower or "incident investigation report" in prompt_lower or "root_cause" in prompt_lower:
            # Extract user query
            user_query = prompt_lower.split("anonymized query:")[-1].split("retrieved context documents:")[0] if "anonymized query:" in prompt_lower else prompt_lower
            if "payment" in user_query or "servicea" in user_query:
                return """{
  "root_cause": "The incident was caused by connection pool exhaustion in PaymentService. The database pool max_connections limit was set to 10, which was insufficient for the traffic spike, leading to connection timeouts.",
  "similar_incidents": [
    {
      "title": "Payment Service Outage",
      "summary": "Connection pool exhaustion in PaymentService due to traffic spike.",
      "mttr": "134",
      "date": "2024-11-15"
    }
  ],
  "suggested_fix": "In utils/db_client.py, increase MAX_CONNECTIONS from 10 to 100 and CONNECTION_TIMEOUT from 5 to 30.",
  "final_report": "# SRE Incident Report - Payment Service Outage\\n\\n## Executive Summary\\nPayment processing failed for 40% of users due to connection timeouts. Service recovered after database pool capacity was increased.\\n\\n## Root Cause\\nConnection pool exhaustion in PaymentService. DatabasePool max_connections was set to 10, which was insufficient under heavy concurrent load.\\n\\n## Suggested Fix\\nModify `utils/db_client.py` to increase connection limits:\\n```python\\nMAX_CONNECTIONS = 100\\nCONNECTION_TIMEOUT = 30\\n```\\n\\n## Blast Radius\\nOutage impacted PaymentService, cascading to OrderService calls."
}"""
            elif "oom" in user_query or "serviceb" in user_query or "cache" in user_query:
                return """{
  "root_cause": "The OrderService crashed due to Out of Memory (OOM) caused by a memory leak in CacheClient. The LRU cache was configured with maxsize=None, allowing unbounded growth.",
  "similar_incidents": [
    {
      "title": "Memory Leak in Cache Layer",
      "summary": "OrderService OOM crash due to unbounded LRU cache growth in CacheClient.",
      "mttr": "45",
      "date": "2024-09-03"
    }
  ],
  "suggested_fix": "In utils/cache_client.py, change @lru_cache(maxsize=None) to @lru_cache(maxsize=1000).",
  "final_report": "# SRE Incident Report - OrderService OOM\\n\\n## Executive Summary\\nOrderService crashed due to OOM as memory grew from 512MB to 4GB. Service restored after caching capacity limit was configured.\\n\\n## Root Cause\\nMemory leak in CacheClient due to unbounded caching. The `@lru_cache(maxsize=None)` decorator was used with no eviction policy.\\n\\n## Suggested Fix\\nModify `utils/cache_client.py` line 23:\\n```python\\n@lru_cache(maxsize=1000)\\n```\\n\\n## Blast Radius\\nOutage impacted OrderService and disabled checkout flows."
}"""
            elif "user" in user_query or "latency" in user_query or "timeout" in user_query or "servicec" in user_query:
                return """{
  "root_cause": "UserService database query missing index on email column. The authenticate function executed a full table scan on 10M rows, which exceeded the gateway timeout of 5s.",
  "similar_incidents": [
    {
      "title": "Cascade Timeout Failure",
      "summary": "UserService database query latency cascaded to PaymentService and OrderService.",
      "mttr": "80",
      "date": "2024-06-10"
    }
  ],
  "suggested_fix": "In services/user_service.py, create database index idx_users_email on users(email) and increase default connection timeouts.",
  "final_report": "# SRE Incident Report - UserService Slowdown\\n\\n## Executive Summary\\nUser verification and authentication timed out due to high database query latency, causing cascading timeouts in checkout flows.\\n\\n## Root Cause\\nUserService executed user queries without an index on the email column. Under load, this triggered full table scans taking > 8 seconds, exceeding caller gateway timeouts.\\n\\n## Suggested Fix\\nCreate database index on email column:\\n```sql\\nCREATE INDEX idx_users_email ON users(email);\\n```\\n\\n## Blast Radius\\nUserService latency cascaded to PaymentProcessor, OrderService, and NotificationService checkout endpoints."
}"""
            else:
                return """{
  "root_cause": "Duplicate orders created due to a race condition in OrderService.create_order() when concurrent requests bypassed duplicate-checks due to missing distributed locks.",
  "similar_incidents": [
    {
      "title": "Race Condition in Order Processing",
      "summary": "Duplicate orders created due to missing distributed lock in OrderService.",
      "mttr": "180",
      "date": "2024-07-20"
    }
  ],
  "suggested_fix": "In services/order_service.py, acquire a Redis distributed lock prior to database duplicate checks.",
  "final_report": "# SRE Incident Report - Order Race Condition\\n\\n## Executive Summary\\nDuplicate charges created for 0.3% of customers. Solved by implementing a distributed lock prior to order creation.\\n\\n## Root Cause\\nConcurrent requests bypassed validation due to lack of a unique constraint and missing distributed synchronization locks.\\n\\n## Suggested Fix\\nImplement Redis lock inside `OrderService.create_order()`:\\n```python\\nwith redis_client.lock(f'user_lock:{user_id}'):\\n    # duplicate check & create order\\n```\\n\\n## Blast Radius\\nImpacted OrderService, leading to duplicate transaction charges."
}"""

        return "SRE analysis completed. Verify config properties."
