"""McKinsey User Profile Mapper for OIDC claim mapping.

This module maps McKinsey ID token claims to IdeaForge AI user profile fields,
handling both standard OIDC claims and McKinsey-specific claims.
"""

import structlog
from typing import Dict, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = structlog.get_logger()


class McKinseyProfileMapper:
    """Maps McKinsey ID token claims to user profile fields.

    Handles claim extraction from McKinsey Keycloak tokens and maps them to
    the IdeaForge AI user_profiles table structure.

    McKinsey Token Structure (from actual Keycloak tokens):
    - Standard OIDC: sub, email, email_verified, name, given_name, family_name, preferred_username
    - Token metadata: iss, aud, exp, iat, auth_time
    - Session info: session_state, sid
    - McKinsey-specific: fmno (firm member number/employee ID), azp, acr, scope

    Note: McKinsey tokens do NOT include office_location or department claims.
    These would require separate API calls if needed.
    """

    # Default tenant ID for McKinsey users (will be fetched from database)
    DEFAULT_TENANT_SLUG = "default"

    def __init__(self, db_session: AsyncSession):
        """Initialize profile mapper with database session.

        Args:
            db_session: SQLAlchemy async session for database operations
        """
        self.db = db_session
        self._default_tenant_id: Optional[UUID] = None

        logger.info("mckinsey_profile_mapper_initialized")

    async def _get_default_tenant_id(self) -> str:
        """Get or fetch the default tenant ID for McKinsey users.

        Returns:
            String UUID of the default tenant

        Raises:
            ValueError: If default tenant doesn't exist
        """
        if self._default_tenant_id is None:
            query = text(
                """
                SELECT id FROM tenants WHERE slug = :slug LIMIT 1
            """
            )
            result = await self.db.execute(query, {"slug": self.DEFAULT_TENANT_SLUG})
            row = result.fetchone()

            if row is None:
                logger.error(
                    "default_tenant_not_found", tenant_slug=self.DEFAULT_TENANT_SLUG
                )
                raise ValueError(
                    f"Default tenant '{self.DEFAULT_TENANT_SLUG}' not found"
                )

            self._default_tenant_id = str(row[0])
            logger.info(
                "default_tenant_loaded",
                tenant_id=self._default_tenant_id,
                tenant_slug=self.DEFAULT_TENANT_SLUG,
            )

        return self._default_tenant_id

    def extract_claims(self, id_token_claims: Dict) -> Dict:
        """Extract and map claims from McKinsey ID token.

        Maps McKinsey Keycloak claims to user profile fields:
        - sub → mckinsey_subject
        - email → mckinsey_email and email
        - name → full_name
        - given_name + family_name → full_name (if name not present)
        - fmno → mckinsey_fmno
        - preferred_username → mckinsey_preferred_username
        - session_state → mckinsey_session_state

        Args:
            id_token_claims: Validated ID token claims from McKinsey

        Returns:
            Dictionary containing mapped user profile fields
        """
        # Extract standard OIDC claims
        sub = id_token_claims.get("sub")
        email = id_token_claims.get("email")
        name = id_token_claims.get("name")
        given_name = id_token_claims.get("given_name")
        family_name = id_token_claims.get("family_name")
        preferred_username = id_token_claims.get("preferred_username")
        email_verified = id_token_claims.get("email_verified", False)

        # Extract McKinsey-specific claims
        fmno = id_token_claims.get("fmno")  # Firm member number (employee ID)
        session_state = id_token_claims.get("session_state")

        # Construct full_name from available claims
        full_name = name
        if not full_name and given_name and family_name:
            full_name = f"{given_name} {family_name}"
        elif not full_name and given_name:
            full_name = given_name
        elif not full_name and family_name:
            full_name = family_name

        # Build mapped profile data
        profile_data = {
            # Core identity fields
            "mckinsey_subject": sub,
            "mckinsey_email": email,
            "email": email,  # Also set the main email field
            "full_name": full_name,
            # McKinsey-specific fields
            "mckinsey_fmno": fmno,
            "mckinsey_preferred_username": preferred_username,
            "mckinsey_session_state": session_state,
            # Metadata
            "email_verified": email_verified,
        }

        # Remove None values to avoid overwriting existing data with nulls
        profile_data = {k: v for k, v in profile_data.items() if v is not None}

        logger.info(
            "claims_extracted",
            subject=sub,
            email=email,
            has_name=bool(full_name),
            has_fmno=bool(fmno),
            has_preferred_username=bool(preferred_username),
            num_fields=len(profile_data),
        )

        return profile_data

    async def create_or_update_user(self, id_token_claims: Dict) -> Dict:
        """Create or update user profile from McKinsey ID token claims.

        If a user with the McKinsey subject already exists, updates their profile.
        If not, creates a new user profile.

        Args:
            id_token_claims: Validated ID token claims from McKinsey

        Returns:
            User object (created or updated)

        Raises:
            ValueError: If required claims are missing or default tenant not found
        """
        # Extract and map claims
        profile_data = self.extract_claims(id_token_claims)

        # Validate required fields
        mckinsey_subject = profile_data.get("mckinsey_subject")
        email = profile_data.get("email")

        if not mckinsey_subject:
            logger.error("missing_required_claim_sub")
            raise ValueError("Missing required claim: sub")

        if not email:
            logger.error("missing_required_claim_email")
            raise ValueError("Missing required claim: email")

        # Get default tenant ID
        tenant_id = await self._get_default_tenant_id()

        # Check if user already exists by McKinsey subject
        result = await self.db.execute(
            select(User).where(User.mckinsey_subject == mckinsey_subject)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Update existing user
            logger.info(
                "updating_existing_user",
                user_id=str(existing_user.id),
                mckinsey_subject=mckinsey_subject,
                email=email,
            )

            # Update fields
            for field, value in profile_data.items():
                if hasattr(existing_user, field):
                    setattr(existing_user, field, value)

            # Update timestamp
            existing_user.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing_user)

            logger.info(
                "user_updated_successfully",
                user_id=str(existing_user.id),
                mckinsey_subject=mckinsey_subject,
            )

            return existing_user

        else:
            # Create new user
            logger.info(
                "creating_new_user", mckinsey_subject=mckinsey_subject, email=email
            )

            # Create user object
            new_user = User(
                email=email,
                full_name=profile_data.get("full_name"),
                tenant_id=tenant_id,
                mckinsey_subject=mckinsey_subject,
                mckinsey_email=profile_data.get("mckinsey_email"),
                mckinsey_fmno=profile_data.get("mckinsey_fmno"),
                mckinsey_preferred_username=profile_data.get(
                    "mckinsey_preferred_username"
                ),
                mckinsey_session_state=profile_data.get("mckinsey_session_state"),
                is_active=True,
                persona="product_manager",  # Default persona
            )

            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            logger.info(
                "user_created_successfully",
                user_id=str(new_user.id),
                mckinsey_subject=mckinsey_subject,
                email=email,
            )

            return new_user

    def get_default_values(self) -> Dict:
        """Get default values for missing optional claims.

        Returns:
            Dictionary containing default values for optional fields
        """
        return {"persona": "product_manager", "is_active": True, "preferences": {}}

    async def assign_tenant(self, user: Dict) -> UUID:
        """Assign tenant to user based on McKinsey configuration.

        Since McKinsey tokens don't include department or office_location,
        all McKinsey users are assigned to the default tenant.

        Args:
            user: User object to assign tenant to

        Returns:
            UUID of the assigned tenant
        """
        tenant_id = await self._get_default_tenant_id()

        if user.tenant_id != tenant_id:
            user.tenant_id = tenant_id
            await self.db.commit()

            logger.info(
                "tenant_assigned", user_id=str(user.id), tenant_id=str(tenant_id)
            )

        return tenant_id


async def create_profile_mapper(db_session: AsyncSession) -> McKinseyProfileMapper:
    """Factory function to create a McKinsey profile mapper.

    Args:
        db_session: SQLAlchemy async session

    Returns:
        Initialized McKinseyProfileMapper instance
    """
    return McKinseyProfileMapper(db_session)
