import logging
import uuid
from typing import Dict, Any, Optional

from data.sample_codebase.services.payment_service import PaymentProcessor
from data.sample_codebase.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class OrderService:
    """
    Manages client order workflows, coordinating with PaymentProcessor and NotificationService.
    """
    def __init__(self, payment_processor: PaymentProcessor, notification_service: NotificationService) -> None:
        self.payment_processor = payment_processor
        self.notification_service = notification_service
        self.orders_db: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized OrderService.")

    def create_order(self, user_id: str, item_id: str, amount: float, card_number: str) -> Dict[str, Any]:
        """
        Creates and processes a new customer order.
        Verifies payment and dispatches order confirmation notifications.

        Args:
            user_id (str): Customer identifier.
            item_id (str): Selected item identifier.
            amount (float): Transaction cost.
            card_number (str): Card details for transaction check.

        Returns:
            Dict[str, Any]: Detailed output structure of the created order.

        Raises:
            ValueError: If transaction processing fails.
        """
        logger.info(f"Received order request from user {user_id} for item {item_id}")
        order_id = str(uuid.uuid4())
        
        # Process the payment
        payment_info = {
            "amount": amount,
            "card_number": card_number,
            "user_id": user_id
        }
        
        payment_result = self.payment_processor.process_payment(order_id, payment_info)
        
        if payment_result.get("status") != "SUCCESS":
            logger.error(f"Order creation aborted. Payment failed for order {order_id}")
            raise ValueError("Payment transaction was unsuccessful.")

        # Save order record
        order_record = {
            "order_id": order_id,
            "user_id": user_id,
            "item_id": item_id,
            "amount": amount,
            "status": "CREATED",
            "payment_ref": payment_result.get("transaction_ref")
        }
        self.orders_db[order_id] = order_record
        logger.info(f"Order {order_id} recorded successfully in database.")

        # Send notifications
        notification_message = f"Your order {order_id} has been placed successfully!"
        self.notification_service.send(user_id, notification_message, ["email", "sms"])

        return order_record

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves order details from the record system.

        Args:
            order_id (str): Target order key.

        Returns:
            Optional[Dict[str, Any]]: Order record if exists, otherwise None.
        """
        logger.info(f"Retrieving order data for ID: {order_id}")
        return self.orders_db.get(order_id)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancels an active order and issues a refund through PaymentProcessor.

        Args:
            order_id (str): Order target for cancellation.

        Returns:
            Dict[str, Any]: Status of cancellation and refund execution.

        Raises:
            KeyError: If order_id does not exist.
        """
        logger.info(f"Cancelling order: {order_id}")
        order = self.get_order(order_id)
        if not order:
            raise KeyError(f"Order with ID {order_id} not found.")

        if order["status"] == "CANCELLED":
            return {"order_id": order_id, "status": "ALREADY_CANCELLED"}

        # Refund transaction
        refund_result = self.payment_processor.refund(order_id, order["amount"])
        
        # Update order record
        order["status"] = "CANCELLED"
        self.orders_db[order_id] = order
        
        # Notify user of cancellation
        cancellation_message = f"Your order {order_id} has been successfully cancelled and refunded."
        self.notification_service.send(order["user_id"], cancellation_message, ["email"])

        return {
            "order_id": order_id,
            "status": "CANCELLED",
            "refund_details": refund_result
        }
