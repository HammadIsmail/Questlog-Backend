"""
Vercel Serverless Function entry point for FastAPI.
Exposes the FastAPI 'app' instance for @vercel/python.
"""
import os
import sys

# Ensure repository root is on sys.path so 'from app.main import app' resolves properly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app  # noqa: E402, F401
