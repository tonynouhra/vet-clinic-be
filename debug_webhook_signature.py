#!/usr/bin/env python3
"""
Debug webhook signature creation and verification.
"""
import hmac
import hashlib
import json
from datetime import datetime

def create_webhook_signature(payload: str, timestamp: str, secret: str) -> str:
    """Create webhook signature for testing."""
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"v1={signature}"

def verify_webhook_signature_debug(payload: str, timestamp: str, signature: str, secret: str) -> bool:
    """Debug webhook signature verification."""
    print(f"Payload: {payload}")
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {signature}")
    print(f"Secret: {secret}")
    
    # Create the signed payload
    signed_payload = f"{timestamp}.{payload}"
    print(f"Signed payload: {signed_payload}")
    
    # Extract signature components
    signatures = {}
    for sig_part in signature.split(","):
        if "=" in sig_part:
            version, sig_value = sig_part.split("=", 1)
            signatures[version] = sig_value
    
    print(f"Parsed signatures: {signatures}")
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Expected signature: {expected_signature}")
    print(f"Received signature: {signatures.get('v1', 'NOT_FOUND')}")
    
    # Compare signatures
    if "v1" not in signatures:
        print("ERROR: Missing v1 signature")
        return False
    
    match = hmac.compare_digest(signatures["v1"], expected_signature)
    print(f"Signatures match: {match}")
    return match

if __name__ == "__main__":
    # Test data
    webhook_secret = "test_webhook_secret_key_for_testing"
    user_data = {
        "id": "user_webhook_123",
        "email_addresses": [
            {
                "id": "email_123",
                "email_address": "webhook@example.com",
                "verification": {"status": "verified"}
            }
        ],
        "first_name": "Webhook",
        "last_name": "User",
        "public_metadata": {"role": "pet_owner"},
        "private_metadata": {},
        "created_at": int(datetime.utcnow().timestamp() * 1000),
        "updated_at": int(datetime.utcnow().timestamp() * 1000),
        "banned": False,
        "locked": False
    }
    
    webhook_payload = {
        "type": "user.created",
        "object": "event",
        "data": user_data,
        "timestamp": int(datetime.utcnow().timestamp() * 1000)
    }

    payload_str = json.dumps(webhook_payload)
    timestamp = str(int(datetime.utcnow().timestamp()))
    signature = create_webhook_signature(payload_str, timestamp, webhook_secret)
    
    print("=== Webhook Signature Debug ===")
    result = verify_webhook_signature_debug(payload_str, timestamp, signature, webhook_secret)
    print(f"Final result: {result}")