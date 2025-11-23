import httpx
from app.config import settings
from structlog import get_logger
from typing import Optional, Dict

logger = get_logger()

async def get_user_contact_info(user_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch user contact information from the User Management service.
    Returns a dict with name, email, and phone, or None if the request fails.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.USER_MANAGEMENT_URL}/api/v1/users/{user_id}",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "name": user_data.get("name") or user_data.get("full_name"),
                    "email": user_data.get("email"),
                    "phone": user_data.get("phone") or user_data.get("phone_number")
                }
            else:
                logger.warning(
                    "Failed to fetch user contact info",
                    user_id=user_id,
                    status_code=response.status_code
                )
                return None
    except Exception as e:
        logger.error(
            "Error fetching user contact info",
            user_id=user_id,
            error=str(e)
        )
        return None
