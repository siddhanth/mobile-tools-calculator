#!/usr/bin/env python3
"""
Utility script to generate bcrypt password hashes for streamlit-authenticator.

Usage:
    python scripts/generate_password_hash.py <password>
    
Example:
    python scripts/generate_password_hash.py mySecurePassword123
    
Then copy the generated hash to config/auth_config.yaml
"""

import sys

try:
    from streamlit_authenticator.utilities import Hasher
except ImportError:
    print("Error: streamlit-authenticator not installed.")
    print("Run: pip install streamlit-authenticator")
    sys.exit(1)


def generate_hash(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    hasher = Hasher()
    return hasher.hash(password)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_password_hash.py <password>")
        print("\nExample:")
        print("  python scripts/generate_password_hash.py mySecurePassword123")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = generate_hash(password)
    
    print("\n" + "=" * 60)
    print("Password Hash Generator")
    print("=" * 60)
    print(f"\nOriginal password: {password}")
    print(f"\nGenerated hash:\n{hashed}")
    print("\n" + "-" * 60)
    print("Copy this hash to config/auth_config.yaml")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

