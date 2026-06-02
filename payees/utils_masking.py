def mask_last_four(value):
    if not value:
        return ""

    value = str(value)
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def mask_if_present(value):
    return "****" if value else ""
