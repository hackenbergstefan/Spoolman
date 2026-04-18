"""Integration tests for the Printer API endpoint."""

import httpx

from ..conftest import URL, assert_httpx_success


def test_delete_printer(random_printer):
    """Test deleting a printer from the database."""
    result = httpx.delete(f"{URL}/api/v1/printer/{random_printer['id']}")
    assert_httpx_success(result)

    # Verify it's gone
    result = httpx.get(f"{URL}/api/v1/printer/{random_printer['id']}")
    assert result.status_code == 404


def test_delete_printer_not_found():
    """Test deleting a printer that does not exist."""
    result = httpx.delete(f"{URL}/api/v1/printer/999999")
    assert result.status_code == 404
