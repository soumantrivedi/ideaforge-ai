"""Load API keys from database for provider registry."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.utils.encryption import get_encryption
import structlog

logger = structlog.get_logger()


async def load_user_api_keys_from_db(
    db: AsyncSession,
    user_id: str
) -> dict[str, Optional[str]]:
    """Load and decrypt API keys from database for a user."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
        
        query = text("""
            SELECT provider, api_key_encrypted
            FROM user_api_keys
            WHERE user_id = :user_id AND is_active = true
        """)
        
        result = await db.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        encryption = get_encryption()
        keys = {}
        
        for row in rows:
            provider = row[0]
            encrypted_key = row[1]
            try:
                decrypted_key = encryption.decrypt(encrypted_key)
                # Map database provider names to registry names
                if provider == 'openai':
                    keys['openai'] = decrypted_key
                elif provider == 'anthropic':
                    keys['claude'] = decrypted_key
                elif provider == 'google':
                    keys['gemini'] = decrypted_key
                elif provider == 'v0':
                    keys['v0'] = decrypted_key
                elif provider == 'lovable':
                    keys['lovable'] = decrypted_key
            except Exception as e:
                logger.error("decrypt_key_failed", provider=provider, error=str(e))
                # Continue with other keys even if one fails
        
        return keys
    except Exception as e:
        logger.error("load_api_keys_error", error=str(e))
        return {}

