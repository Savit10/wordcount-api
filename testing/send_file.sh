#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./testing/send_file.sh <filename> [api_base_url]"
  echo "Example: ./testing/send_file.sh sample.pdf https://pzgitkr7wr.us-east-1.awsapprunner.com"
  exit 1
fi

FILE_NAME="$1"
API_BASE_URL="${2:-${API_BASE_URL:-http://localhost:8000}}"

LOCAL_FILE_PATH="testing/files/$FILE_NAME"
if [[ ! -f "$LOCAL_FILE_PATH" ]]; then
  echo "File not found: $LOCAL_FILE_PATH"
  echo "Put your file under testing/files and pass only the filename."
  exit 1
fi

curl -sS -X POST "${API_BASE_URL%/}/api/v1/word-count" \
  -F "file=@${LOCAL_FILE_PATH}"

echo
