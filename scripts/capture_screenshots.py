#!/usr/bin/env python3
"""Capture README screenshots from a running public-safe demo app."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    ("list", "/", "[data-testid='conclusion-list']"),
    ("detail", "/conclusions/1", "[data-testid='conclusion-detail']"),
    ("create", "/conclusions/new", "[data-testid='conclusion-form']"),
]


def capture(base_url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        try:
            for name, path, ready_selector in PAGES:
                page.goto(f"{base_url.rstrip('/')}{path}", wait_until="networkidle")
                page.locator(ready_selector).wait_for(state="visible")
                page.screenshot(path=output_dir / f"{name}.png", full_page=False)

            page.goto(f"{base_url.rstrip('/')}/conclusions/new", wait_until="networkidle")
            page.locator(".decision-workbench").screenshot(
                path=output_dir / "decision-workbench.png"
            )

            page.goto(f"{base_url.rstrip('/')}/conclusions/1", wait_until="networkidle")
            page.locator(".analysis-view").screenshot(path=output_dir / "decision-path.png")

            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{base_url.rstrip('/')}/conclusions/new", wait_until="networkidle")
            page.locator("[data-testid='conclusion-form']").wait_for(state="visible")
            dimensions = page.evaluate(
                """
                () => ({
                    viewportWidth: document.documentElement.clientWidth,
                    pageWidth: document.documentElement.scrollWidth,
                })
                """
            )
            if dimensions["pageWidth"] > dimensions["viewportWidth"]:
                raise RuntimeError(f"Mobile form overflows horizontally: {dimensions}")
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8006")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "screenshots")
    args = parser.parse_args()

    capture(args.base_url, args.output_dir)
    print(f"Captured README screenshots in {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
