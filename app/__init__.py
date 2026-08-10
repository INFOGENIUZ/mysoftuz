import os
import sys

# Ensure software_bot directory is present in sys.path for top-level app imports
software_bot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software_bot"))
if software_bot_dir not in sys.path:
    sys.path.insert(0, software_bot_dir)

# Extend package path to point to software_bot/app
__path__ = [os.path.join(software_bot_dir, "app")]

