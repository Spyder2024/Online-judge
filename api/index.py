import sys
import os

# Add root directory to python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export app for Vercel Serverless Function runtime
__all__ = ["app"]
