"""Tests for mellivor_kernel.providers.health."""

from __future__ import annotations

from mellivor_kernel.providers import ProviderHealthCheck


def test_healthy_report() -> None:
    report = ProviderHealthCheck(healthy=True, provider_name="fake")

    assert report.healthy is True
    assert report.provider_name == "fake"
    assert report.detail == ""


def test_unhealthy_report_with_detail() -> None:
    report = ProviderHealthCheck(healthy=False, provider_name="fake", detail="timed out")

    assert report.healthy is False
    assert report.provider_name == "fake"
    assert report.detail == "timed out"
