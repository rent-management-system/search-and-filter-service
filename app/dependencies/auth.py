from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from app.config import settings
from structlog import get_logger

logger = get_logger()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    async with httpx.AsyncClient() as client:
        try:
            logger.info("Verifying token with user management service", url=f"{settings.USER_MANAGEMENT_URL}/auth/verify")

            response = await client.get(
                f"{settings.USER_MANAGEMENT_URL}/auth/verify",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            response.raise_for_status()
            user_data = response.json()
            logger.info("User verified", user=user_data)
            return user_data
        except httpx.HTTPStatusError as e:
            logger.error("Token verification failed", status_code=e.response.status_code, response=e.response.text)
            raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError as e:
            logger.error("User management service is unavailable", error=str(e))
            raise HTTPException(status_code=503, detail="User management service is unavailable")
