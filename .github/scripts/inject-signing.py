#!/usr/bin/env python3
"""Patch frontend/android/app/build.gradle to enable release signing.

Idempotent — safe to run on every CI build.
Reads keystore password / alias / key password from env vars.
"""
import os
import re
import sys
from pathlib import Path

BUILD_GRADLE = Path("frontend/android/app/build.gradle")

if not BUILD_GRADLE.exists():
    sys.exit(f"ERROR: {BUILD_GRADLE} not found — did `npx cap add android` run?")

src = BUILD_GRADLE.read_text()

if "signingConfigs" in src:
    print(f"Signing already configured in {BUILD_GRADLE} — nothing to do.")
    sys.exit(0)

signing_block = """
    signingConfigs {
        release {
            storeFile file('release.keystore')
            storePassword System.getenv("KEYSTORE_PASSWORD")
            keyAlias System.getenv("KEY_ALIAS")
            keyPassword System.getenv("KEY_PASSWORD")
        }
    }
"""

# Insert signingConfigs after the `android {` opening brace
src, n = re.subn(r"(android\s*\{\s*\n)", r"\1" + signing_block, src, count=1)
if n == 0:
    sys.exit("ERROR: could not find `android {` block in build.gradle")

# Bind release buildType to the signingConfig
src, n = re.subn(
    r"(buildTypes\s*\{\s*\n\s*release\s*\{\s*\n)",
    r"\1            signingConfig signingConfigs.release\n",
    src,
    count=1,
)
if n == 0:
    print("WARNING: could not bind signingConfigs.release to buildTypes.release")

BUILD_GRADLE.write_text(src)
print(f"OK — patched {BUILD_GRADLE} with release signing config.")
