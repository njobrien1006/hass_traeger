"""Bump version"""

import datetime
import re
from pathlib import Path

# Load file
file_path = Path("custom_components/traeger/manifest.json")
content = file_path.read_text(encoding="utf-8")

# Find version
pattern = r'(\"version\"\s*:\s*")(\d+)\.(\d+)\.(\d+)(")'


def bump_version(match):
    """Version Value"""
    year, month, patch = match.group(2), match.group(3), match.group(4)
    dtnow = datetime.datetime.now()
    if str(dtnow.year) == year and str(dtnow.month) == month:
        return (
            f"{match.group(1)}{year}.{int(month) + 0}.{int(patch) + 1}{match.group(5)}"
        )
    return f"{match.group(1)}{dtnow.year}.{dtnow.month}.{0}{match.group(5)}"


new_content = re.sub(pattern, bump_version, content, count=1)

# Save file
file_path.write_text(new_content, encoding="utf-8")
print("Minor version incremented successfully!")

# Load file
file_path = Path("custom_components/traeger/const.py")
content = file_path.read_text(encoding="utf-8")

# Find version
pattern = r'(VERSION\s*=\s*")(\d+)\.(\d+)\.(\d+)(")'

new_content = re.sub(pattern, bump_version, content, count=1)

# Save file
file_path.write_text(new_content, encoding="utf-8")
print("Minor version incremented successfully!")
