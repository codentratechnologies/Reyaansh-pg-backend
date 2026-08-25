import os
# Triggering server reload
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initializes the Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        else:
            logger.warning(f"Firebase credentials file not found at: {cred_path}")

# Initialize at module import
initialize_firebase()

def send_push_notification(fcm_token, title, body, data=None, url=None, icon_url=None):
    """
    Sends a push notification to a specific device using its FCM token.
    
    Args:
        fcm_token (str): The FCM token of the target device.
        title (str): The title of the notification.
        body (str): The body content of the notification.
        data (dict, optional): Custom data payload to send with the notification.
        url (str, optional): The URL to redirect to when the notification is clicked.
        icon_url (str, optional): The URL of the custom logo/icon to display.
        
    Returns:
        tuple: (bool success, str result)
    """
    if not firebase_admin._apps:
        logger.error("Cannot send push notification: Firebase app is not initialized.")
        return False, "Firebase app is not initialized. Check firebase_credentials.json"

    if not fcm_token:
        logger.error("Cannot send push notification: Missing fcm_token.")
        return False, "Missing fcm_token."

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
                image=icon_url  # For some platforms, this acts as the large image
            ),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    icon=icon_url
                ) if icon_url else None,
                fcm_options=messaging.WebpushFCMOptions(
                    link=url
                ) if url else None
            ),
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    click_action=url
                ) if url else None
            ),
            token=fcm_token,
        )

        # Send the message
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True, response
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False, str(e)
