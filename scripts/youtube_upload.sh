#!/usr/bin/env bash
# Upload a video to YouTube via Data API v3
# Usage: youtube_upload.sh <video_file> <title> <description> <tags> <account>
#   account: "gmail" or "ortakca"
set -euo pipefail

VIDEO_FILE="$1"
TITLE="$2"
DESCRIPTION="${3:-}"
TAGS="${4:-}"
ACCOUNT="${5:-gmail}"

# Select refresh token based on account
if [ "$ACCOUNT" = "ortakca" ]; then
  REFRESH_TOKEN="$YOUTUBE_REFRESH_TOKEN_ORTAKCA"
else
  REFRESH_TOKEN="$YOUTUBE_REFRESH_TOKEN_GMAIL"
fi

CLIENT_ID="$GOOGLE_CLIENT_ID"
CLIENT_SECRET="$GOOGLE_CLIENT_SECRET"

echo "🔑 Getting access token..."
ACCESS_TOKEN=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "refresh_token=$REFRESH_TOKEN" \
  -d "grant_type=refresh_token" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Auto-append #Shorts for vertical short videos
if [[ "$TITLE" != *"#Shorts"* ]]; then
  TITLE="${TITLE} #Shorts"
fi
if [[ "$DESCRIPTION" != *"#Shorts"* ]]; then
  DESCRIPTION="${DESCRIPTION}\n\n#Shorts #shitpost #auto-generated"
fi

echo "📤 Uploading video: $TITLE"

# Build metadata JSON
METADATA=$(python3 -c "
import json
meta = {
    'snippet': {
        'title': '''$TITLE''',
        'description': '''$DESCRIPTION''',
        'tags': [t.strip() for t in '''$TAGS'''.split(',') if t.strip()] + ['Shorts'],
        'categoryId': '22'
    },
    'status': {
        'privacyStatus': 'public',
        'selfDeclaredMadeForKids': False
    }
}
print(json.dumps(meta))
")

# Upload via resumable upload protocol
UPLOAD_URL=$(curl -s -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Upload-Content-Type: video/mp4" \
  -H "X-Upload-Content-Length: $(stat -f%z "$VIDEO_FILE" 2>/dev/null || stat -c%s "$VIDEO_FILE")" \
  -d "$METADATA" \
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status" \
  -D - -o /dev/null | grep -i "location:" | awk '{print $2}' | tr -d '\r')

if [ -z "$UPLOAD_URL" ]; then
  echo "❌ Failed to initiate upload"
  exit 1
fi

echo "⬆️  Uploading file..."
RESPONSE=$(curl -s -X PUT \
  -H "Content-Type: video/mp4" \
  --data-binary "@$VIDEO_FILE" \
  "$UPLOAD_URL")

VIDEO_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

if [ -n "$VIDEO_ID" ]; then
  echo "✅ Upload complete! https://youtube.com/watch?v=$VIDEO_ID"
else
  echo "❌ Upload failed:"
  echo "$RESPONSE"
  exit 1
fi
