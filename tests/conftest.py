"""Test configuration — adds project root to sys.path for imports."""
import sys
import os

# Add project root to path so test modules can import skip_client, daemon, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
