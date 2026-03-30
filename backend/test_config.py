#!/usr/bin/env python3
"""Test ALLOWED_ORIGINS parsing"""
import os

test_value = "https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app,https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app,http://localhost:5173"

# Simulate the validator
if isinstance(test_value, str):
    trimmed = test_value.strip()
    if trimmed.startswith("["):
        result = trimmed
    else:
        result = [item.strip() for item in trimmed.split(",") if item.strip()]
else:
    result = test_value

print("✅ Parsing successful!")
print(f"Result type: {type(result)}")
print(f"Result value: {result}")
print(f"Number of origins: {len(result)}")
for i, origin in enumerate(result, 1):
    print(f"  {i}. {origin}")
