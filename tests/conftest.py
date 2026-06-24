"""Pytest configuration and shared fixtures."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests in unit/integration/e2e dirs."""
    for item in items:
        path = str(item.fspath)
        if "/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in path:
            item.add_marker(pytest.mark.e2e)
