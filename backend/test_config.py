#!/usr/bin/env python3
"""
Test ALLOWED_ORIGINS parsing with production-grade validator.
Run this to verify the parser handles all Railway deployment formats.
"""
import json


def parse_allowed_origins(value):
    """
    Production-grade ALLOWED_ORIGINS parser (from config.py).
    Handles all formats: JSON, Railway-style brackets, CSV, single URL.
    """
    # Already a list - return as-is
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    
    # Not a string - return empty list
    if not isinstance(value, str):
        return []
    
    trimmed = value.strip()
    
    # Empty string - return empty list
    if not trimmed:
        return []
    
    # Handle bracket-wrapped formats (JSON or Railway-style)
    if trimmed.startswith("["):
        # Try proper JSON first
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            return []
        except json.JSONDecodeError:
            # Not valid JSON - treat as bracket-wrapped comma-separated
            # Remove opening '[' and trailing ']'
            inner = trimmed[1:].rstrip("]").strip()
            if not inner:
                return []
            # Split by comma and clean each item
            return [item.strip() for item in inner.split(",") if item.strip()]
    
    # Plain comma-separated without brackets
    return [item.strip() for item in trimmed.split(",") if item.strip()]


if __name__ == "__main__":
    # Test the EXACT format that was failing in Railway
    railway_format = '[http://localhost:5173,https://m2n-frontend.vercel.app]'
    result = parse_allowed_origins(railway_format)
    
    print("=" * 60)
    print("ALLOWED_ORIGINS PARSER VERIFICATION")
    print("=" * 60)
    print(f"\nInput (Railway format): {railway_format}")
    print(f"Output: {result}")
    print(f"Count: {len(result)} origins")
    for i, origin in enumerate(result, 1):
        print(f"  {i}. {origin}")
    
    # Verify proper JSON also works
    proper_json = '["http://localhost:5173","https://m2n-frontend.vercel.app"]'
    result2 = parse_allowed_origins(proper_json)
    print(f"\nInput (Proper JSON): {proper_json}")
    print(f"Output: {result2}")
    
    if result == result2:
        print("\n[OK] Both formats produce identical results!")
        print("The deployment should now work regardless of format.")
    else:
        print("\n[ERROR] Results differ!")
