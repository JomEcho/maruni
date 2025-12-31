#!/bin/bash
# Create a macOS .app bundle for JomCollege

APP_NAME="JomCollege"
APP_DIR="$HOME/Desktop/${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Creating macOS app: ${APP_DIR}"

# Create app structure
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Create Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>JomCollege</string>
    <key>CFBundleDisplayName</key>
    <string>JomCollege</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.jomcollege</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create launcher script
cat > "${APP_DIR}/Contents/MacOS/launch" << EOF
#!/bin/bash
cd "${SCRIPT_DIR}"

# Open browser na 2 seconden
(sleep 2 && open "http://localhost:8501") &

# Start streamlit
/opt/homebrew/bin/streamlit run app.py --server.headless true --server.port 8501
EOF

chmod +x "${APP_DIR}/Contents/MacOS/launch"

echo "Done! App created at: ${APP_DIR}"
echo ""
echo "Je kunt de app nu dubbelklikken op je bureaublad!"
