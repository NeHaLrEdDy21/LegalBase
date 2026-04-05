"""
Root conftest.py — adds the backend directory to sys.path so that
`import app.*` works for all pytest test files without installation.
"""
import sys
from pathlib import Path

# Insert backend/ at the front of sys.path
sys.path.insert(0, str(Path(__file__).parent))
