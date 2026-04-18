"""Integration tests for the Printer API endpoint."""

import httpx

from ..conftest import URL, assert_httpx_success, random_printer_impl


def test_find_printers():
    """Test finding printers."""
    with random_printer_impl() as printer:
        result = httpx.get(f"{URL}/api/v1/printer")
        assert_httpx_success(result)

        printers = result.json()
        assert isinstance(printers, list)

        # Our printer should be in the results
        ids = [p["id"] for p in printers]
        assert printer["id"] in ids


def test_find_printers_by_name():
    """Test finding printers by name."""
    with random_printer_impl() as printer:
        result = httpx.get(
            f"{URL}/api/v1/printer",
            params={"name": printer["name"]},
        )
        assert_httpx_success(result)

        printers = result.json()
        assert len(printers) >= 1
        ids = [p["id"] for p in printers]
        assert printer["id"] in ids


def test_find_printers_with_sort():
    """Test finding printers with sorting."""
    with random_printer_impl():
        result = httpx.get(
            f"{URL}/api/v1/printer",
            params={"sort": "name:asc"},
        )
        assert_httpx_success(result)

        printers = result.json()
        names = [p["name"] for p in printers]
        assert names == sorted(names, key=str.lower)


def test_find_printers_with_limit():
    """Test finding printers with limit and offset."""
    with random_printer_impl():
        result = httpx.get(
            f"{URL}/api/v1/printer",
            params={"limit": 1, "offset": 0},
        )
        assert_httpx_success(result)

        printers = result.json()
        assert len(printers) <= 1

        # Check x-total-count header
        assert "x-total-count" in result.headers
