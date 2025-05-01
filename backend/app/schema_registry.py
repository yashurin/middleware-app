from app.config import get_settings
from app.transforms import transform_contact_message, transform_feedback

settings = get_settings()

SCHEMA_REGISTRY = {
    "contact-message-schema": {
        "transform": transform_contact_message,
        "destination_url": settings.CONTACT_MESSAGE_URL,
    },
    "user-feedback-schema": {
        "transform": transform_feedback,
        "destination_url": "https://external.api/feedback",
    },
}
