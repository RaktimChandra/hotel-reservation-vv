"""Simulated payment gateway with fault injection hooks (used for recovery testing)."""


class GatewayError(Exception):
    """Gateway unavailable / timed out / declined."""


FAULT = {"mode": None}  # None | "timeout" | "decline"


def charge(amount, method) -> str:
    mode = FAULT["mode"]
    if mode == "timeout":
        raise GatewayError("Payment gateway timed out")
    if mode == "decline":
        raise GatewayError("Payment declined by issuer")
    return "TXN-OK"
