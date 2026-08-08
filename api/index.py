import sys
import os

# Add project root directory to Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export ASGI app instance for Vercel Serverless Functions
handler = app
