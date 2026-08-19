from pathlib import Path

from vinted_assistant.browser import PrefillReport
from vinted_assistant.launcher import build_launch_args


def test_prefill_report_anything_done():
    report = PrefillReport()
    assert report.anything_done is False
    report.title_filled = True
    assert report.anything_done is True


def test_prefill_report_counts_photos():
    report = PrefillReport(photos_uploaded=3)
    assert report.anything_done is True
    assert report.photos_uploaded == 3


def test_build_launch_args_contains_flags():
    args = build_launch_args(Path("/tmp/profile"), 9222, "https://www.vinted.fr")
    assert "--remote-debugging-port=9222" in args
    assert "--user-data-dir=/tmp/profile" in args
    assert args[-1] == "https://www.vinted.fr"


def test_build_launch_args_without_url():
    args = build_launch_args(Path("/tmp/profile"), 9333, None)
    assert "--remote-debugging-port=9333" in args
    assert all(not a.startswith("http") for a in args)
