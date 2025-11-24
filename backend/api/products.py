"""Product management, sharing, and portfolio API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/products", tags=["products"])


class CreateProductRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ShareProductRequest(BaseModel):
    shared_with_user_id: str
    permission: str = "view"  # view, edit, admin


@router.get("")
async def list_products(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all products accessible to current user (own + shared)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT p.id, p.name, p.description, p.status, p.user_id, 
                   up.email as owner_email, up.full_name as owner_name,
                   p.created_at, p.updated_at,
                   CASE 
                     WHEN p.user_id = :user_id THEN 'owner'
                     WHEN ps.id IS NOT NULL THEN ps.permission
                     ELSE 'view'
                   END as access_level
            FROM products p
            JOIN user_profiles up ON p.user_id = up.id
            LEFT JOIN product_shares ps ON p.id = ps.product_id AND ps.shared_with_user_id = :user_id
            WHERE p.tenant_id = :tenant_id
            AND (
              p.user_id = :user_id
              OR ps.id IS NOT NULL
            )
            ORDER BY p.updated_at DESC
        """)
        
        result = await db.execute(query, {
            "user_id": current_user["id"],
            "tenant_id": current_user["tenant_id"]
        })
        rows = result.fetchall()
        
        products = [
            {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "user_id": str(row[4]),
                "owner_email": row[5],
                "owner_name": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
                "access_level": row[9],
            }
            for row in rows
        ]
        
        return {"products": products}
    except Exception as e:
        logger.error("list_products_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list products")


@router.get("/portfolio")
async def get_portfolio(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio of all products in the tenant."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT 
              p.id, p.name, p.description, p.status, p.user_id,
              up.email as owner_email, up.full_name as owner_name,
              p.created_at, p.updated_at,
              COUNT(DISTINCT ps.id) as share_count,
              COUNT(DISTINCT ps2.id) as shared_with_me
            FROM products p
            JOIN user_profiles up ON p.user_id = up.id
            LEFT JOIN product_shares ps ON p.id = ps.product_id
            LEFT JOIN product_shares ps2 ON p.id = ps2.product_id AND ps2.shared_with_user_id = :user_id
            WHERE p.tenant_id = :tenant_id
            GROUP BY p.id, p.name, p.description, p.status, p.user_id, 
                     up.email, up.full_name, p.created_at, p.updated_at
            ORDER BY p.updated_at DESC
        """)
        
        result = await db.execute(query, {
            "user_id": current_user["id"],
            "tenant_id": current_user["tenant_id"]
        })
        rows = result.fetchall()
        
        portfolio = [
            {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "user_id": str(row[4]),
                "owner_email": row[5],
                "owner_name": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
                "share_count": row[9],
                "shared_with_me": row[10] > 0,
            }
            for row in rows
        ]
        
        return {"portfolio": portfolio, "tenant_id": current_user["tenant_id"]}
    except Exception as e:
        logger.error("get_portfolio_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get portfolio")


@router.post("")
async def create_product(
    request: CreateProductRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new product."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            INSERT INTO products (name, description, user_id, tenant_id, status)
            VALUES (:name, :description, :user_id, :tenant_id, 'ideation')
            RETURNING id, name, description, status, user_id, created_at, updated_at
        """)
        
        result = await db.execute(query, {
            "name": request.name,
            "description": request.description,
            "user_id": current_user["id"],
            "tenant_id": current_user["tenant_id"]
        })
        await db.commit()
        row = result.fetchone()
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "user_id": str(row[4]),
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }
    except Exception as e:
        await db.rollback()
        logger.error("create_product_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create product")


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific product (must be owner or shared with user)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT p.id, p.name, p.description, p.status, p.user_id, p.tenant_id,
                   up.email as owner_email, up.full_name as owner_name,
                   p.created_at, p.updated_at, p.metadata
            FROM products p
            JOIN user_profiles up ON p.user_id = up.id
            LEFT JOIN product_shares ps ON p.id = ps.product_id AND ps.shared_with_user_id = :user_id
            WHERE p.id = :product_id
            AND p.tenant_id = :tenant_id
            AND (
              p.user_id = :user_id
              OR ps.id IS NOT NULL
            )
        """)
        
        result = await db.execute(query, {
            "product_id": product_id,
            "user_id": current_user["id"],
            "tenant_id": current_user["tenant_id"]
        })
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Product not found or access denied")
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "user_id": str(row[4]),
            "tenant_id": str(row[5]),
            "owner_email": row[6],
            "owner_name": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
            "metadata": row[10] if row[10] else {},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_product_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get product")


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    request: UpdateProductRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a product (must be owner or have edit permission)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Check access
        access_query = text("""
            SELECT p.user_id, ps.permission
            FROM products p
            LEFT JOIN product_shares ps ON p.id = ps.product_id AND ps.shared_with_user_id = :user_id
            WHERE p.id = :product_id
            AND p.tenant_id = :tenant_id
            AND (
              p.user_id = :user_id
              OR (ps.id IS NOT NULL AND ps.permission IN ('edit', 'admin'))
            )
        """)
        
        access_result = await db.execute(access_query, {
            "product_id": product_id,
            "user_id": current_user["id"],
            "tenant_id": current_user["tenant_id"]
        })
        access_row = access_result.fetchone()
        
        if not access_row:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update query
        update_fields = []
        params = {"product_id": product_id}
        
        if request.name is not None:
            update_fields.append("name = :name")
            params["name"] = request.name
        
        if request.description is not None:
            update_fields.append("description = :description")
            params["description"] = request.description
        
        if request.status is not None:
            if request.status not in ['ideation', 'build', 'operate', 'learn', 'govern', 'sunset']:
                raise HTTPException(status_code=400, detail="Invalid status")
            update_fields.append("status = :status")
            params["status"] = request.status
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = now()")
        
        query = text(f"""
            UPDATE products
            SET {', '.join(update_fields)}
            WHERE id = :product_id
            RETURNING id, name, description, status, user_id, updated_at
        """)
        
        result = await db.execute(query, params)
        await db.commit()
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "user_id": str(row[4]),
            "updated_at": row[5].isoformat() if row[5] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_product_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update product")


@router.post("/{product_id}/share")
async def share_product(
    product_id: str,
    request: ShareProductRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Share a product with another user in the same tenant."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify product ownership
        owner_query = text("""
            SELECT user_id, tenant_id FROM products
            WHERE id = :product_id
        """)
        owner_result = await db.execute(owner_query, {"product_id": product_id})
        owner_row = owner_result.fetchone()
        
        if not owner_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if str(owner_row[0]) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only product owner can share")
        
        if str(owner_row[1]) != current_user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Cannot share across tenants")
        
        # Verify shared_with_user is in same tenant
        user_query = text("""
            SELECT id, tenant_id FROM user_profiles
            WHERE id = :user_id AND is_active = true
        """)
        user_result = await db.execute(user_query, {"user_id": request.shared_with_user_id})
        user_row = user_result.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        if str(user_row[1]) != current_user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Cannot share with users from other tenants")
        
        if str(user_row[0]) == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot share with yourself")
        
        # Verify permission value
        if request.permission not in ['view', 'edit', 'admin']:
            raise HTTPException(status_code=400, detail="Invalid permission")
        
        # Create or update share
        share_query = text("""
            INSERT INTO product_shares (product_id, shared_with_user_id, shared_by_user_id, permission)
            VALUES (:product_id, :shared_with_user_id, :shared_by_user_id, :permission)
            ON CONFLICT (product_id, shared_with_user_id)
            DO UPDATE SET permission = :permission, updated_at = now()
            RETURNING id, permission, created_at
        """)
        
        result = await db.execute(share_query, {
            "product_id": product_id,
            "shared_with_user_id": request.shared_with_user_id,
            "shared_by_user_id": current_user["id"],
            "permission": request.permission
        })
        await db.commit()
        row = result.fetchone()
        
        return {
            "id": str(row[0]),
            "permission": row[1],
            "created_at": row[2].isoformat() if row[2] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("share_product_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to share product")


@router.get("/{product_id}/shares")
async def get_product_shares(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users a product is shared with."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify product ownership
        owner_query = text("""
            SELECT user_id FROM products WHERE id = :product_id
        """)
        owner_result = await db.execute(owner_query, {"product_id": product_id})
        owner_row = owner_result.fetchone()
        
        if not owner_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if str(owner_row[0]) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only product owner can view shares")
        
        query = text("""
            SELECT ps.id, ps.shared_with_user_id, ps.permission, ps.created_at,
                   up.email, up.full_name
            FROM product_shares ps
            JOIN user_profiles up ON ps.shared_with_user_id = up.id
            WHERE ps.product_id = :product_id
            ORDER BY ps.created_at DESC
        """)
        
        result = await db.execute(query, {"product_id": product_id})
        rows = result.fetchall()
        
        shares = [
            {
                "id": str(row[0]),
                "shared_with_user_id": str(row[1]),
                "permission": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "user_email": row[4],
                "user_name": row[5],
            }
            for row in rows
        ]
        
        return {"shares": shares}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_product_shares_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get product shares")


@router.delete("/{product_id}/shares/{share_id}")
async def remove_product_share(
    product_id: str,
    share_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a product share."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify product ownership
        owner_query = text("""
            SELECT user_id FROM products WHERE id = :product_id
        """)
        owner_result = await db.execute(owner_query, {"product_id": product_id})
        owner_row = owner_result.fetchone()
        
        if not owner_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if str(owner_row[0]) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only product owner can remove shares")
        
        delete_query = text("""
            DELETE FROM product_shares
            WHERE id = :share_id AND product_id = :product_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {
            "share_id": share_id,
            "product_id": product_id
        })
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Share not found")
        
        return {"message": "Share removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("remove_product_share_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove share")


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a product (must be owner)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify product ownership
        owner_query = text("""
            SELECT user_id, tenant_id FROM products WHERE id = :product_id
        """)
        owner_result = await db.execute(owner_query, {"product_id": product_id})
        owner_row = owner_result.fetchone()
        
        if not owner_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if str(owner_row[0]) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only product owner can delete")
        
        if str(owner_row[1]) != current_user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Cannot delete products from other tenants")
        
        delete_query = text("""
            DELETE FROM products
            WHERE id = :product_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {"product_id": product_id})
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {"message": "Product deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("delete_product_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete product")

