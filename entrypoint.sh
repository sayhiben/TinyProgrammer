#!/bin/sh
# Ensure runtime volume files exist and are writable before startup.

# Create runtime dir if it doesn't exist
mkdir -p /app/runtime

# Initialize files if they don't exist or are empty
[ -s /app/runtime/lessons.md ] || printf '# Developer Journal\n\n' > /app/runtime/lessons.md
[ -s /app/runtime/config_overrides.json ] || echo '{}' > /app/runtime/config_overrides.json
[ -s /app/runtime/liked_programs.json ] || echo '[]' > /app/runtime/liked_programs.json

# Symlink into /app so the rest of the code finds them at expected paths
ln -sf /app/runtime/lessons.md /app/lessons.md
ln -sf /app/runtime/config_overrides.json /app/config_overrides.json
ln -sf /app/runtime/liked_programs.json /app/liked_programs.json

exec python -u main.py
