function check_pipenv {
  command -v pipenv > /dev/null 2>&1 || { echo "[ERROR][check_pipenv]: pipenv not installed."; return 1; }
  echo "[OK]   pipenv found ($(pipenv --version 2>&1))"
}

function check_venv {
  pipenv --venv > /dev/null 2>&1 || { echo "[WARN][check_venv]: venv not ready -- run make install"; return 0; }
  echo "[OK]   venv ready ($(pipenv --venv 2>&1))"
}

function check_cairo {
  brew list cairo > /dev/null 2>&1 || { echo "[ERROR][check_cairo]: cairo not installed -- run: brew install cairo"; return 1; }
  echo "[OK]   cairo installed (required by weasyprint)"
}

function check_pango {
  brew list pango > /dev/null 2>&1 || { echo "[ERROR][check_pango]: pango not installed -- run: brew install pango"; return 1; }
  echo "[OK]   pango installed (required by weasyprint)"
}

function check_lp {
  command -v lp > /dev/null 2>&1 || { echo "[ERROR][check_lp]: lp not found -- CUPS not available"; return 1; }
  echo "[OK]   lp found ($(which lp))"
}

function check_printer {
  local printer="${PRINTER:-}"
  if [ -z "$printer" ]; then
    echo "[WARN][check_printer]: PRINTER not set"
    return 0
  fi
  lpstat -p "$printer" > /dev/null 2>&1 \
    && echo "[OK]   printer $printer is available" \
    || echo "[ERROR][check_printer]: printer $printer not found -- run lpstat -p to list available printers"
}

function show_status {
  echo ""
  echo "=== Status ==="
  check_pipenv || true
  check_venv   || true
  check_cairo  || true
  check_pango  || true
  check_lp     || true
  check_printer || true
  echo "=============="
  echo ""
}
