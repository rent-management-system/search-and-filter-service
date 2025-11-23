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
        # Try the /users/{id} endpoint first
        url = f"{settings.USER_MANAGEMENT_URL}/users/{user_id}"
        logger.info("Fetching user contact info", user_id=user_id, url=url)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(
                "User service response",
                user_id=user_id,
                status_code=response.status_code,
                response_text=response.text[:200] if response.text else None
            )
            
            if response.status_code == 200:
                user_data = response.json()
                contact_info = {
                    "name": user_data.get("name") or user_data.get("full_name") or user_data.get("username"),
                    "email": user_data.get("email"),
                    "phone": user_data.get("phone") or user_data.get("phone_number")
                }
                logger.info("Successfully fetched user contact", user_id=user_id, contact_info=contact_info)
                return contact_info
            else:
                logger.warning(
                    "Failed to fetch user contact info",
                    user_id=user_id,
                    status_code=response.status_code,
                    response_body=response.text[:500] if response.text else None
                )
                return None
    except httpx.TimeoutException as e:
        logger.error(
            "Timeout fetching user contact info",
            user_id=user_id,
            error=str(e)
        )
        return None
    except Exception as e:
        logger.error(
            "Error fetching user contact info",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        )
        return None
