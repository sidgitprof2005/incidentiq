import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DatabasePool:
    """
    A simulated database connection pool manager.
    Handles connection lifecycle and limits maximum concurrent connections.
    """
    MAX_CONNECTIONS: int = 100
    CONNECTION_TIMEOUT: int = 30

    def __init__(self, host: str = "localhost", port: int = 5432) -> None:
        self.host = host
        self.port = port
        self.active_connections: int = 0
        logger.info(f"Initialized DatabasePool for {self.host}:{self.port} with max connections {self.MAX_CONNECTIONS}")

    def get_connection(self) -> Dict[str, Any]:
        """
        Acquires a database connection from the pool.

        Returns:
            Dict[str, Any]: A dictionary simulating a database connection object.

        Raises:
            TimeoutError: If a connection cannot be acquired within CONNECTION_TIMEOUT.
        """
        start_time = time.time()
        # Simulate connection acquisition logic
        if self.active_connections >= self.MAX_CONNECTIONS:
            logger.warning("Max database connections reached. Waiting for a connection...")
            while self.active_connections >= self.MAX_CONNECTIONS:
                time.sleep(0.1)
                if time.time() - start_time > self.CONNECTION_TIMEOUT:
                    logger.error("Database connection acquisition timed out.")
                    raise TimeoutError(f"Could not acquire a connection from the pool within {self.CONNECTION_TIMEOUT} seconds.")

        self.active_connections += 1
        logger.debug(f"Connection acquired. Active connections: {self.active_connections}")
        return {
            "id": f"conn_{int(time.time() * 1000)}",
            "status": "connected",
            "host": self.host,
            "port": self.port
        }

    def release(self, connection: Dict[str, Any]) -> None:
        """
        Releases a database connection back to the pool.

        Args:
            connection (Dict[str, Any]): The connection object to be released.
        """
        if self.active_connections > 0:
            self.active_connections -= 1
            logger.debug(f"Connection {connection.get('id')} released. Active connections: {self.active_connections}")
        else:
            logger.warning("Attempted to release connection but active connections count is already 0.")
