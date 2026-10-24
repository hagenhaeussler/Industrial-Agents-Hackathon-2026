"""Public views never carry the private session bearer credential."""


def public_payload(value):
    """Copy JSON-shaped data without session IDs; keep durable records intact."""
    if isinstance(value, dict):
        return {key: public_payload(item) for key, item in value.items()
                if key != 'session_id'}
    if isinstance(value, (list, tuple)):
        return [public_payload(item) for item in value]
    return value
