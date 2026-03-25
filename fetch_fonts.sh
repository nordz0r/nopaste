#!/usr/bin/env bash
set -euo pipefail

FONT_DIR="src/static/fonts"
mkdir -p "$FONT_DIR"

curl -fsSL -o "$FONT_DIR/inter-400.woff2" \
  "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Regular.woff2"
curl -fsSL -o "$FONT_DIR/inter-500.woff2" \
  "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Medium.woff2"
curl -fsSL -o "$FONT_DIR/inter-600.woff2" \
  "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-SemiBold.woff2"
curl -fsSL -o "$FONT_DIR/jetbrains-mono-400.woff2" \
  "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/webfonts/JetBrainsMono-Regular.woff2"

echo "Fonts downloaded to $FONT_DIR"
