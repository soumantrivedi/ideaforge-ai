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
                if not encrypted_key:
                    logger.warning("empty_encrypted_key", provider=provider, user_id=user_id)
                    continue
                decrypted_key = encryption.decrypt(encrypted_key)
                if not decrypted_key:
                    logger.warning("empty_decrypted_key", provider=provider, user_id=user_id)
                    continue
                # Trim the decrypted key to remove any whitespace
                decrypted_key = decrypted_key.strip()
                # Map database provider names to registry names
                if provider == 'openai':
                    keys['openai'] = decrypted_key
                elif provider == 'anthropic':
                    keys['claude'] = decrypted_key
                elif provider == 'google':
                    keys['gemini'] = decrypted_key
                elif provider == 'v0':
                    keys['v0'] = decrypted_key
                    logger.info("v0_key_loaded_from_db",
                               user_id=user_id,
                               key_length=len(decrypted_key),
                               key_prefix=decrypted_key[:8] + "..." if len(decrypted_key) > 8 else "N/A")
                elif provider == 'lovable':
                    keys['lovable'] = decrypted_key
                logger.debug("key_decrypted_successfully", provider=provider, user_id=user_id, key_length=len(decrypted_key))
            except ValueError as e:
                error_msg = str(e) if str(e) else "Unknown decryption error"
                logger.error("decrypt_key_failed", provider=provider, error=error_msg, user_id=user_id, encrypted_key_length=len(encrypted_key) if encrypted_key else 0)
                # Continue with other keys even if one fails
            except Exception as e:
                error_msg = str(e) if str(e) else f"Exception type: {type(e).__name__}"
                logger.error("decrypt_key_failed_unexpected", provider=provider, error=error_msg, user_id=user_id, exception_type=type(e).__name__)
                # Continue with other keys even if one fails
        
        return keys
    except Exception as e:
        logger.error("load_api_keys_error", error=str(e))
        return {}

