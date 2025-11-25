"""
Helper functions for product permission checks
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import Optional


async def check_product_permission(
    db: AsyncSession,
    product_id: UUID,
    user_id: str,
    required_permission: str = "view"  # view, edit, admin
) -> bool:
    """
    Check if user has required permission on a product.
    
    Returns:
        True if user has required permission, False otherwise
    """
    try:
        query = text("""
            SELECT 
                p.user_id as owner_id,
                ps.permission as share_permission
            FROM products p
            LEFT JOIN product_shares ps ON p.id = ps.product_id 
                AND ps.shared_with_user_id = :user_id
            WHERE p.id = :product_id
        """)
        
        result = await db.execute(query, {
            "product_id": str(product_id),
            "user_id": user_id
        })
        row = result.fetchone()
        
        if not row:
            return False
        
        owner_id = str(row[0]) if row[0] else None
        share_permission = row[1] if row[1] else None
        
        # Owner has all permissions
        if owner_id == user_id:
            return True
        
        # Check share permission
        if share_permission:
            permission_levels = {"view": 1, "edit": 2, "admin": 3}
            required_level = permission_levels.get(required_permission, 1)
            user_level = permission_levels.get(share_permission, 0)
            return user_level >= required_level
        
        return False
        
    except Exception:
        return False


async def get_product_permission(
    db: AsyncSession,
    product_id: UUID,
    user_id: str
) -> Optional[str]:
    """
    Get user's permission level on a product.
    
    Returns:
        'owner', 'admin', 'edit', 'view', or None
    """
    try:
        query = text("""
            SELECT 
                p.user_id as owner_id,
                ps.permission as share_permission
            FROM products p
            LEFT JOIN product_shares ps ON p.id = ps.product_id 
                AND ps.shared_with_user_id = :user_id
            WHERE p.id = :product_id
        """)
        
        result = await db.execute(query, {
            "product_id": str(product_id),
            "user_id": user_id
        })
        row = result.fetchone()
        
        if not row:
            return None
        
        owner_id = str(row[0]) if row[0] else None
        share_permission = row[1] if row[1] else None
        
        if owner_id == user_id:
            return "owner"
        
        return share_permission
        
    except Exception:
        return None

