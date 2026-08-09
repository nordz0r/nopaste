#!/usr/bin/env python3
"""Check current logo and extract original from git main branch."""

import subprocess
from PIL import Image

# Extract original logo from main branch
subprocess.run(
    ["git", "show", "main:src/static/images/goldfinches_logo.png"],
    stdout=open("/tmp/orig_logo.png", "wb"),
    cwd="/mnt/c/Users/Legion/OneDrive/Projects/nopaste",
)

orig = Image.open("/tmp/orig_logo.png")
print(f"Original logo: Size={orig.size}, Mode={orig.mode}")

# Check current logo
current = Image.open(
    "/mnt/c/Users/Legion/OneDrive/Projects/nopaste/src/static/images/goldfinches_logo.png"
)
print(f"Current logo: Size={current.size}, Mode={current.mode}")

# Copy original to artifacts for viewing
orig.save(
    "/mnt/c/Users/Legion/.gemini/antigravity/brain/fbbcfcd0-1ac0-411a-90c1-538dd9183086/original_logo.png"
)
print("Saved original_logo.png to artifacts")
