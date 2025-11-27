#!/bin/sh
# Docker entrypoint script for frontend
# Injects runtime configuration (API URL) into the HTML before starting nginx

set -e

# Get configuration from environment variables (set via ConfigMap)
API_URL="${VITE_API_URL:-}"
JOB_POLL_INTERVAL_MS="${JOB_POLL_INTERVAL_MS:-5000}"
JOB_MAX_POLL_ATTEMPTS="${JOB_MAX_POLL_ATTEMPTS:-120}"
JOB_TIMEOUT_MS="${JOB_TIMEOUT_MS:-600000}"

# Path to index.html
INDEX_HTML="/usr/share/nginx/html/index.html"

# Create the injection script with all configuration
INJECT_SCRIPT="<script>window.__API_URL__='${API_URL}';window.__JOB_POLL_INTERVAL_MS__='${JOB_POLL_INTERVAL_MS}';window.__JOB_MAX_POLL_ATTEMPTS__='${JOB_MAX_POLL_ATTEMPTS}';window.__JOB_TIMEOUT_MS__='${JOB_TIMEOUT_MS}';</script>"

# Check if index.html exists
if [ ! -f "$INDEX_HTML" ]; then
  echo "Warning: $INDEX_HTML not found, skipping API URL injection"
else
  # Inject the script before the closing </head> tag
  # If </head> doesn't exist, inject before </body>
  if grep -q "</head>" "$INDEX_HTML"; then
    sed -i "s|</head>|${INJECT_SCRIPT}</head>|" "$INDEX_HTML"
    echo "Injected API URL into </head>: ${API_URL}"
  elif grep -q "</body>" "$INDEX_HTML"; then
    sed -i "s|</body>|${INJECT_SCRIPT}</body>|" "$INDEX_HTML"
    echo "Injected API URL into </body>: ${API_URL}"
  else
    # Append to the end of the file
    echo "$INJECT_SCRIPT" >> "$INDEX_HTML"
    echo "Appended API URL to end of file: ${API_URL}"
  fi
fi

# Start nginx
exec nginx -g "daemon off;"

