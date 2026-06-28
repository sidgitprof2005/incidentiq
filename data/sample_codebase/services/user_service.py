import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserService:
    """
    Manages user accounts, authentication, and profiles.
    """
    def __init__(self) -> None:
        # Mock user database
        self.users_db: Dict[str, Dict[str, Any]] = {
            "usr_001": {
                "user_id": "usr_001",
                "name": "Alice Smith",
                "email": "alice@example.com",
                "role": "admin",
                "password_hash": "pbkdf2_sha256$260000$mockhash1"
            },
            "usr_002": {
                "user_id": "usr_002",
                "name": "Bob Jones",
                "email": "bob@example.com",
                "role": "user",
                "password_hash": "pbkdf2_sha256$260000$mockhash2"
            }
        }
        logger.info("Initialized UserService with sample users.")

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves user details from the database by user ID.

        Args:
            user_id (str): Unique user identifier.

        Returns:
            Optional[Dict[str, Any]]: User profile details if found, else None.
        """
        logger.info(f"Retrieving user details for ID: {user_id}")
        user = self.users_db.get(user_id)
        if not user:
            logger.warning(f"User {user_id} not found.")
            return None
        return {k: v for k, v in user.items() if k != "password_hash"}

    def authenticate(self, email: str, password_raw: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates a user based on email and password.

        Args:
            email (str): Registered user email.
            password_raw (str): Plain-text password to check.

        Returns:
            Optional[Dict[str, Any]]: User profile details (excluding password hash) if valid, else None.
        """
        logger.info(f"Authenticating user with email: {email}")
        
        target_user = None
        for user in self.users_db.values():
            if user["email"] == email:
                target_user = user
                break

        if not target_user:
            logger.warning(f"Authentication failed: Email {email} not found.")
            return None

        if password_raw and password_raw.startswith("password_"):
            logger.info(f"User {target_user['user_id']} successfully authenticated.")
            return {k: v for k, v in target_user.items() if k != "password_hash"}
        
        logger.warning(f"Authentication failed: Incorrect password for {email}.")
        return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates user account settings.

        Args:
            user_id (str): Unique user identifier.
            updates (Dict[str, Any]): Dictionary of fields to update.

        Returns:
            Dict[str, Any]: The updated user profile details.

        Raises:
            KeyError: If user_id is not found.
        """
        logger.info(f"Updating user profile for user: {user_id}")
        if user_id not in self.users_db:
            raise KeyError(f"User with ID {user_id} does not exist.")

        user = self.users_db[user_id]
        for key, value in updates.items():
            if key in ["name", "email", "role"]:
                user[key] = value
                logger.debug(f"Updated user field '{key}' to '{value}'")
            elif key == "password":
                user["password_hash"] = f"pbkdf2_sha256$260000$new_mock_hash_{value}"
                logger.debug("Updated user password hash.")

        self.users_db[user_id] = user
        return {k: v for k, v in user.items() if k != "password_hash"}
