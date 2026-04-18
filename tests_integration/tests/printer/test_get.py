"""Integration tests for the Printer API endpoint."""

import httpx

from ..conftest import URL, assert_dicts_compatible, assert_httpx_success


def test_get_printer(random_printer):
    """Test getting a printer from the database."""
    result = httpx.get(f"{URL}/api/v1/printer/{random_printer['id']}")
    assert_httpx_success(result)

    printer = result.json()
    assert_dicts_compatible(
        printer,
        {
            "id": random_printer["id"],
            "name": random_printer["name"],
            "comment": random_printer["comment"],
        },
    )


def test_get_printer_not_found():
    """Test getting a printer that does not exist."""
    result = httpx.get(f"{URL}/api/v1/printer/999999")
    assert result.status_code == 404
