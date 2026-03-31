#!autonomous_engineer/api/routes/users.py
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

# Assuming api.auth is available from the previous modules
from autonomous_engineer.api.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Data Models (Pydantic V1 & Dataclasses) ---

@dataclass
class InternalUserRecord:
    """Internal representation of a user in the database."""
    user_id: str
    email: str
    full_name: str
    is_active: bool
    subscription_tier: str

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr = Field(..., description="Valid email address of the user.")
    full_name: str = Field(..., min_length=2, max_length=100)

class UserResponse(BaseModel):
    """Schema for outgoing user data."""
    user_id: str
    email: EmailStr
    full_name: str
    is_active: bool
    subscription_tier: str

# --- Mock Database and Store Pattern ---

class UserStore:
    """
    Object-oriented wrapper for user data persistence operations.
    In production, this interfaces with PostgreSQL.
    """

    def __init__(self) -> None:
        """Initializes the mock database store."""
        self._db: Dict[str, InternalUserRecord] = {}

    @property
    def total_active_users(self) -> int:
        """
        Calculates the total number of currently active users.

        Returns:
            int: The count of active users.
        """
        return sum(1 for user in self._db.values() if user.is_active)

    def create(self, user_data: UserCreate) -> InternalUserRecord:
        """
        Creates and stores a new user record.

        Args:
            user_data: Validated incoming user data.

        Returns:
            InternalUserRecord: The newly created database record.
        
        Raises:
            ValueError: If the email is already registered.
        """
        existing_emails = {u.email for u in self._db.values()}
        if user_data.email in existing_emails:
            logger.warning(f"Registration failed. Email {user_data.email} exists.")
            raise ValueError(f"Email {user_data.email} is already registered.")

        new_id = f"usr_{uuid.uuid4().hex[:12]}"
        record = InternalUserRecord(
            user_id=new_id,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=True,
            subscription_tier="free"
        )
        self._db[new_id] = record
        logger.info(f"Created new user: {new_id}")
        return record

    def get_by_id(self, user_id: str) -> Optional[InternalUserRecord]:
        """Retrieves a user by their unique ID."""
        return self._db.get(user_id)

    def get_all_active(self) -> List[InternalUserRecord]:
        """Retrieves all active users using list comprehensions."""
        return [user for user in self._db.values() if user.is_active]

# Instantiate singleton store for the router
user_store = UserStore()

# --- API Endpoints ---

# To secure these endpoints, add: api_key: str = Depends(verify_api_key)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate) -> UserResponse:
    """
    Registers a new user in the platform.

    Args:
        user_in: The validated creation schema payload.

    Returns:
        UserResponse: The generated user object.
        
    Raises:
        HTTPException: If the creation logic fails.
    """
    try:
        record = user_store.create(user_in)
        return UserResponse(**record.__dict__)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error during user creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """
    Fetches a single user by ID.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        UserResponse: The user's details.
        
    Raises:
        HTTPException: If the user is not found.
    """
    record = user_store.get_by_id(user_id)
    if not record:
        logger.info(f"User lookup failed for ID: {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    return UserResponse(**record.__dict__)

@router.get("/", response_model=List[UserResponse])
async def list_active_users() -> List[UserResponse]:
    """
    Lists all active users in the system.

    Returns:
        List[UserResponse]: A list of user response objects.
    """
    active_records = user_store.get_all_active()
    return [UserResponse(**record.__dict__) for record in active_records]

if __name__ == "__main__":
    import asyncio
    
    async def run_example() -> None:
        """Runs a localized test of the user store functionality."""
        logging.basicConfig(level=logging.INFO)
        mock_user = UserCreate(email="founder@agent.ai", full_name="AI Founder")
        
        try:
            created = await register_user(mock_user)
            logger.info(f"Test creation successful: {created.user_id} - {created.subscription_tier}")
        except Exception as e:
            logger.error(f"Test failed: {e}")

    asyncio.run(run_example())