def transform_contact_message(data: dict) -> dict:
    # Example transformation logic for "contact-message-schema"
    return {
        "full_name": data.get("name"),
        "email_address": data.get("email"),
        "msg_body": data.get("message")
    }


def transform_feedback(data: dict) -> dict:
    # Transform logic for another schema
    return {
        "userId": data.get("user_id"),
        "score": data.get("rating"),
        "comments": data.get("text")
    }