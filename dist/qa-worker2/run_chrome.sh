#!/bin/bash
# Launch headless Chromium with CDP for Worker 2 QA. Usage: run_chrome.sh PORT
PORT=${1:-9223}
/opt/meta-chromium/chrome --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --allow-file-access-from-files --remote-debugging-port=$PORT --remote-allow-origins='*' \
  --window-size=390,844 --user-data-dir=/tmp/w2-chrome-$PORT \
  about:blank > /tmp/w2-chrome-$PORT.log 2>&1 &
echo "launched pid $! on port $PORT"
