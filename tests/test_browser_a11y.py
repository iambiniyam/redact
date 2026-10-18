"""Browser-level accessibility checks for redact."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

import redact.server as server_module

AXE = Path(__file__).with_name("axe.min.js")
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pii_form.png"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    folder = tmp_path_factory.mktemp("redact-out")
    server_module.OUTPUT_DIR = folder
    server_module.JOBS_DIR = folder / "jobs"
    server_module.JOBS_DIR.mkdir()
    port = free_port()
    config = uvicorn.Config(server_module.app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def axe_violations(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    report = page.evaluate(
        """async () => await axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] }
        })"""
    )
    return [item for item in report["violations"] if item["impact"] in {"serious", "critical"}]


def test_initial_and_findings_states(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        tab = browser.new_page(viewport={"width": 1182, "height": 900})
        tab.goto(live_server, wait_until="networkidle")
        assert axe_violations(tab) == []

        tab.set_input_files("#file", str(FIXTURE))
        tab.click("#go")
        tab.wait_for_selector(".finding-check", timeout=60000)
        assert axe_violations(tab) == []
        browser.close()
