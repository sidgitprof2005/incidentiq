import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Manages user notifications via email and SMS channels.
    """
    def __init__(self, provider_name: str = "MockNotify") -> None:
        self.provider_name = provider_name
        logger.info(f"Initialized NotificationService using provider: {self.provider_name}")

    def send(self, recipient_id: str, message: str, channels: List[str]) -> Dict[str, Any]:
        """
        Dispatches notification message over the specified channels.

        Args:
            recipient_id (str): Destination user identifier.
            message (str): Body text to deliver.
            channels (List[str]): List of channels to use, e.g., ["email", "sms"].

        Returns:
            Dict[str, Any]: Results dictionary mapping channel to dispatch status.
        """
        results = {}
        for channel in channels:
            if channel.lower() == "email":
                results["email"] = self.send_email(recipient_id, message)
            elif channel.lower() == "sms":
                results["sms"] = self.send_sms(recipient_id, message)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                results[channel] = "FAILED: Unsupported Channel"
        return {"recipient_id": recipient_id, "results": results}

    def send_email(self, recipient_id: str, message: str) -> str:
        """
        Sends an email notification.

        Args:
            recipient_id (str): Target user identifier.
            message (str): Body content.

        Returns:
            str: Email status message (e.g., "SENT").
        """
        logger.info(f"Sending email to {recipient_id} via {self.provider_name}: {message[:30]}...")
        return "SENT"

    def send_sms(self, recipient_id: str, message: str) -> str:
        """
        Sends an SMS notification.

        Args:
            recipient_id (str): Target user identifier or phone.
            message (str): Body content.

        Returns:
            str: SMS status message (e.g., "DELIVERED").
        """
        logger.info(f"Sending SMS to {recipient_id} via {self.provider_name}: {message[:30]}...")
        return "DELIVERED"
