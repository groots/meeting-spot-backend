#!/usr/bin/env python3
"""
Script to fix duplicate CORS headers in the routes.py file.
"""

import re

# Path to routes.py file
routes_file = "app/api/v1/routes.py"

# Read file content
with open(routes_file, "r") as file:
    content = file.read()

# Define patterns to fix
patterns = [
    # Fix duplicate Access-Control-Allow-Origin headers
    (r'response\.headers\.add\("Access-Control-Allow-Origin", "\*"\)\s+\s+response\.headers\.add\("Access-Control-Allow-Origin", "\*"\)',
     r'response.headers.add("Access-Control-Allow-Origin", "*")'),
    
    # Fix duplicate Access-Control-Max-Age headers
    (r'response\.headers\.add\("Access-Control-Max-Age", "3600"\)\s+\s+response\.headers\.add\("Access-Control-Allow-Headers", "[^"]+"\)\s+\s+response\.headers\.add\("Access-Control-Max-Age", "3600"\)',
     r'response.headers.add("Access-Control-Max-Age", "3600")\n        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")'),
    
    # Fix cases where Max-Age is before and after Headers
    (r'response\.headers\.add\("Access-Control-Max-Age", "3600"\)\s+\s+response\.headers\.add\("Access-Control-Allow-Headers", "[^"]+"\)\s+\s+response\.headers\.add\("Access-Control-Max-Age", "3600"\)',
     r'response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")\n        response.headers.add("Access-Control-Max-Age", "3600")'),
]

# Apply all patterns
fixed_content = content
for pattern, replacement in patterns:
    fixed_content = re.sub(pattern, replacement, fixed_content)

# Write back to file
with open(routes_file, "w") as file:
    file.write(fixed_content)

print(f"✅ Fixed CORS headers in {routes_file}")

# Create a simpler, more reliable implementation
standard_cors_preflight = """    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With, Origin")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response
"""

print("To avoid these issues in the future, use this standard CORS preflight handler:")
print(standard_cors_preflight) 