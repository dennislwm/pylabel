function check_pipenv {
  command -v pipenv > /dev/null 2>&1 || { echo "[ERROR][check_pipenv]: pipenv not installed."; return 1; }
  echo "[OK]   pipenv found ($(pipenv --version 2>&1))"
}

function check_venv {
  pipenv --venv > /dev/null 2>&1 || { echo "[WARN][check_venv]: venv not ready -- run make install"; return 0; }
  echo "[OK]   venv ready ($(pipenv --venv 2>&1))"
}

function check_brew_dep {
  local dep="$1"
  brew list "$dep" > /dev/null 2>&1 || { echo "[ERROR][check_brew_dep]: $dep not installed -- run: brew install $dep"; return 1; }
  echo "[OK]   $dep installed (required by weasyprint)"
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
  check_brew_dep cairo || true
  check_brew_dep pango || true
  check_lp     || true
  check_printer || true
  echo "=============="
  echo ""
}
