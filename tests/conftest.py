import sys
import os

# Add backend directory to Python path so `from core.xxx import ...` works
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(_backend_dir))
