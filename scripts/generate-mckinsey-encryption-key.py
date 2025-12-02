#!/usr/bin/env python3
"""
Generate McKinsey SSO Token Encryption Key

This script generates a 32-byte Fernet encryption key for encrypting
McKinsey refresh tokens at rest in Redis.

Usage:
    python scripts/generate-mckinsey-encryption-key.py

The generated key should be stored securely in Kubernetes secrets:
    kubectl create secret generic mckinsey-sso-secrets \
      --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='<generated-key>' \
      --namespace=your-namespace

Security Notes:
- Generate a unique key for each environment (dev, staging, prod)
- Store keys in a secure password manager or secrets vault
- Never commit keys to git
- Rotate keys regularly (requires re-encryption of stored tokens)
"""

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Error: cryptography package not installed")
    print("Install with: pip install cryptography")
    exit(1)

def generate_key():
    """Generate a new Fernet encryption key."""
    key = Fernet.generate_key()
    return key.decode()

def main():
    print("=" * 70)
    print("McKinsey SSO Token Encryption Key Generator")
    print("=" * 70)
    print()
    
    key = generate_key()
    
    print("Generated Encryption Key:")
    print("-" * 70)
    print(key)
    print("-" * 70)
    print()
    
    print("Usage Instructions:")
    print("-" * 70)
    print("1. Copy the key above")
    print("2. Store it securely (password manager, secrets vault)")
    print("3. Add to Kubernetes secret:")
    print()
    print("   kubectl create secret generic mckinsey-sso-secrets \\")
    print("     --from-literal=MCKINSEY_CLIENT_ID='your-client-id' \\")
    print("     --from-literal=MCKINSEY_CLIENT_SECRET='your-client-secret' \\")
    print("     --from-literal=MCKINSEY_REDIRECT_URI='https://your-domain.com/api/auth/mckinsey/callback' \\")
    print(f"     --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='{key}' \\")
    print("     --namespace=your-namespace")
    print()
    print("4. Or add to .env file (for local development):")
    print()
    print(f"   MCKINSEY_TOKEN_ENCRYPTION_KEY={key}")
    print()
    print("-" * 70)
    print()
    
    print("Security Reminders:")
    print("-" * 70)
    print("✓ Generate unique keys for each environment")
    print("✓ Never commit keys to git")
    print("✓ Store keys in secure password manager")
    print("✓ Rotate keys regularly")
    print("✓ Use Kubernetes secrets in production")
    print("=" * 70)

if __name__ == "__main__":
    main()
