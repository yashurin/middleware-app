from app.config import get_settings
from app.transforms import transform_contact_message, transform_feedback

settings = get_settings()

SCHEMA_REGISTRY = {
    "contact-message-schema": {
        "schema_name": "contact-message-schema",
        "transform": transform_contact_message,
        "source_url": settings.CONTACT_MESSAGE_SOURCE_URL,
        "destination_url": settings.CONTACT_MESSAGE_DESTINATION_URL,
    },
    "user-feedback-schema": {
        "schema_name": "user-feedback",
        "transform": transform_feedback,
        "source_url": "",
        "destination_url": "https://external.api/feedback",
    },
}
