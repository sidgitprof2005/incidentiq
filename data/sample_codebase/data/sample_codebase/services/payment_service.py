import logging
from typing import Dict, Any

from data.sample_codebase.utils.db_client import DatabasePool
from data.sample_codebase.utils.cache_client import CacheClient

logger = logging.getLogger(__name__)

class PaymentProcessor:
    """
    Handles payment transaction operations, incorporating validation, execution, and refunding.
    Integrates with DatabasePool for ledger persistence and CacheClient for fast status lookup.
    """
    def __init__(self, db_pool: DatabasePool, cache_client: CacheClient) -> None:
        self.db_pool = db_pool
        self.cache_client = cache_client

    def validate_payment(self, payment_info: Dict[str, Any]) -> bool:
        """
        Validates payment payload parameters.

        Args:
            payment_info (Dict[str, Any]): Details of the payment target.

        Returns:
            bool: True if transaction details are valid, False otherwise.
        """
        amount = payment_info.get("amount", 0.0)
        card_number = payment_info.get("card_number", "")
        if amount <= 0.0:
            logger.warning("Invalid payment amount.")
            return False
        if len(card_number) < 13:
            logger.warning("Invalid card number format.")
            return False
        return True

    def process_payment(self, payment_id: str, payment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a charge transaction. Uses cache checking and persists ledger changes to DB.

        Args:
            payment_id (str): Unique transaction identifier.
            payment_info (Dict[str, Any]): Metadata for payment processing.

        Returns:
            Dict[str, Any]: Transaction output status.
        
        Raises:
            ValueError: If validation fails.
        """
        logger.info(f"Initiating payment processing for transaction: {payment_id}")
        
        if not self.validate_payment(payment_info):
            raise ValueError("Payment validation failed.")

        # Check cache
        cached_status = self.cache_client.get(f"payment_status:{payment_id}")
        if cached_status:
            logger.info(f"Found cached status for payment {payment_id}: {cached_status}")
            return {"payment_id": payment_id, "status": cached_status, "cached": True}

        # Acquire database connection
        connection = self.db_pool.get_connection()
        try:
            # Simulate processing time and DB write
            logger.info(f"Saving payment {payment_id} transaction record using connection {connection['id']}")
            result = {
                "payment_id": payment_id,
                "amount": payment_info["amount"],
                "status": "SUCCESS",
                "transaction_ref": f"tx_{payment_id}",
                "cached": False
            }
            self.cache_client.set(f"payment_status:{payment_id}", "SUCCESS")
            return result
        finally:
            self.db_pool.release(connection)

    def refund(self, payment_id: str, amount: float) -> Dict[str, Any]:
        """
        Refunds a previously settled payment transaction.

        Args:
            payment_id (str): Original payment reference.
            amount (float): Value to be refunded.

        Returns:
            Dict[str, Any]: Refund request status.
        """
        logger.info(f"Processing refund for payment: {payment_id} of amount: {amount}")
        connection = self.db_pool.get_connection()
        try:
            # Simulate DB update
            self.cache_client.invalidate(f"payment_status:{payment_id}")
            return {
                "refund_id": f"ref_{payment_id}",
                "payment_id": payment_id,
                "amount_refunded": amount,
                "status": "REFUNDED"
            }
        finally:
            self.db_pool.release(connection)
