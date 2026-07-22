"""TST-035: check_printer must not call a disabled CUPS queue available."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_check_printer(lpstat_output, tmp_path):
    stub = tmp_path / "lpstat"
    stub.write_text('#!/bin/sh\necho "%s"\n' % lpstat_output)
    stub.chmod(0o755)
    env = dict(os.environ, PATH="%s:%s" % (tmp_path, os.environ["PATH"]), PRINTER="P")
    return subprocess.run(
        ["bash", "-c", "source %s/make.sh; check_printer" % ROOT],
        capture_output=True, text=True, env=env,
    ).stdout


def test_disabled_queue_reports_error(tmp_path):
    out = _run_check_printer("printer P disabled since Mon Jul 20 22:51:03 2026 -", tmp_path)
    assert "[ERROR]" in out
    assert "is available" not in out


def test_idle_queue_reports_ok(tmp_path):
    out = _run_check_printer("printer P is idle.  enabled since Mon Jul 20 22:51:03 2026", tmp_path)
    assert "[OK]" in out
