from datetime import datetime, timedelta

# Define the functions that the agent can use
# Note: These functions are just placeholders and don't actually interact
# with any external services


def get_delivery_date(order_id: str) -> datetime:
    return f"Will arrive on {(datetime.now() + timedelta(days=2)).date()}."


def get_order_status(order_id: str) -> str:
    return "Dispatched"


def get_order_shipping_address(order_id: str) -> str:
    return "38 avenue John F. Kennedy, L-1855 Luxembourg."
