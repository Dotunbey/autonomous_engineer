import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Data Models (Pydantic V1) ---

class CheckoutSessionRequest(BaseModel):
    """Schema for initializing a Stripe checkout."""
    user_id: str = Field(..., description="The ID of the user purchasing the tier.")
    plan_id: str = Field(..., description="The ID of the subscription plan (e.g., 'pro', 'team').")

class CheckoutSessionResponse(BaseModel):
    """Schema for the generated checkout URL."""
    checkout_url: str
    session_id: str

class UsageMetrics(BaseModel):
    """Schema tracking an agent's token and runtime usage."""
    user_id: str
    tasks_run: int
    tokens_consumed: int
    is_quota_exceeded: bool

# --- Billing Logic Module ---

class BillingManager:
    """
    Handles subscription state, usage quotas, and payment gateway interactions.
    """

    def __init__(self) -> None:
        """Initializes billing state and mocked configurations."""
        self._pricing_tiers = {
            "free": {"task_limit": 10, "price": 0},
            "pro": {"task_limit": 1000, "price": 4900},  # Cents
            "team": {"task_limit": 5000, "price": 19900}
        }
        self._mock_usage: Dict[str, Dict[str, int]] = {}

    @property
    def available_plans(self) -> List[str]:
        """
        Retrieves the list of supported subscription plans using list comprehensions.
        
        Returns:
            List[str]: Active pricing tiers.
        """
        return [tier for tier in self._pricing_tiers.keys()]

    def generate_checkout_link(self, user_id: str, plan_id: str) -> str:
        """
        Simulates calling Stripe to generate a hosted checkout session URL.

        Args:
            user_id: The target user's ID.
            plan_id: The requested subscription tier.

        Returns:
            str: The payment gateway URL.
            
        Raises:
            ValueError: If the requested plan is invalid.
        """
        if plan_id not in self._pricing_tiers:
            logger.error(f"Invalid plan requested: {plan_id}")
            raise ValueError(f"Plan '{plan_id}' does not exist.")
            
        logger.info(f"Generating Stripe checkout for user {user_id} on {plan_id} plan.")
        return f"https://checkout.stripe.com/pay/cs_test_{user_id}_{plan_id}"

    def get_user_usage(self, user_id: str) -> Dict[str, int]:
        """Retrieves or initializes current billing cycle usage for a user."""
        if user_id not in self._mock_usage:
            self._mock_usage[user_id] = {"tasks_run": 0, "tokens_consumed": 0}
        return self._mock_usage[user_id]

billing_manager = BillingManager()

# --- API Endpoints ---

@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(request: CheckoutSessionRequest) -> CheckoutSessionResponse:
    """
    Creates a Stripe checkout session for subscription upgrades.

    Args:
        request: The checkout configuration payload.

    Returns:
        CheckoutSessionResponse: Contains the URL to redirect the user to.
        
    Raises:
        HTTPException: For invalid plans or API failure.
    """
    try:
        url = billing_manager.generate_checkout_link(request.user_id, request.plan_id)
        return CheckoutSessionResponse(
            checkout_url=url,
            session_id=f"sess_{request.user_id}"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to generate checkout session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment gateway error.")

@router.get("/usage/{user_id}", response_model=UsageMetrics)
async def check_usage_quota(user_id: str) -> UsageMetrics:
    """
    Retrieves the billing cycle usage and checks if quotas are exceeded.

    Args:
        user_id: The user to audit.

    Returns:
        UsageMetrics: Token, task, and quota state.
    """
    usage = billing_manager.get_user_usage(user_id)
    
    # Mock lookup for user tier (assuming 'free' if not connected to user DB)
    user_tier = "free"
    limit = billing_manager._pricing_tiers[user_tier]["task_limit"]
    
    return UsageMetrics(
        user_id=user_id,
        tasks_run=usage["tasks_run"],
        tokens_consumed=usage["tokens_consumed"],
        is_quota_exceeded=(usage["tasks_run"] >= limit)
    )

if __name__ == "__main__":
    import asyncio
    
    async def run_billing_test() -> None:
        """Local test to verify billing logic."""
        logging.basicConfig(level=logging.INFO)
        req = CheckoutSessionRequest(user_id="usr_123", plan_id="pro")
        
        try:
            res = await create_checkout_session(req)
            logger.info(f"Successfully generated checkout: {res.checkout_url}")
        except Exception as e:
            logger.error(f"Billing test failed: {e}")

    asyncio.run(run_billing_test())