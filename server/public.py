"""Remove bearer credentials at public event, tour and tool boundaries."""


def public_payload(value):
    """Keep private ownership in storage without broadcasting session authority.

    Session creation/read endpoints deliberately return the caller's own session
    ID. Shared tours, event feeds, WebSockets and model tool results must not.
    """
    if isinstance(value, dict):
        return {key: public_payload(item) for key, item in value.items()
                if key not in {"session_id", "admin_authority", "_admin_authorized"}}
    if isinstance(value, (list, tuple)):
        return [public_payload(item) for item in value]
    return value
