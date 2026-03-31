#!api/auth.py
import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Configure the API key header scheme
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates the incoming API key against the environment configuration.

    Args:
        api_key: The key extracted from the X-API-Key header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    # In a real startup environment, this would verify against a DB of user tokens or Stripe subscriptions.
    expected_api_key = os.getenv("AGENT_API_KEY", "dev-secret-key")
    
    if not api_key:
        logger.warning("Attempted access with missing API key.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Please provide X-API-Key header.",
        )
        
    if api_key != expected_api_key:
        logger.warning("Attempted access with invalid API key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key provided.",
        )
        
    return api_key