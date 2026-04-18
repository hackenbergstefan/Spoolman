"""Integration tests for the Printer API endpoint."""

from datetime import datetime, timezone

import httpx

from ..conftest import URL, assert_dicts_compatible, random_spool_impl


def test_add_printer():
    """Test adding a printer to the database."""
    name = "Prusa MK4"
    comment = "My main printer"
    result = httpx.post(
        f"{URL}/api/v1/printer",
        json={
            "name": name,
            "comment": comment,
        },
    )
    result.raise_for_status()

    printer = result.json()
    assert_dicts_compatible(
        printer,
        {
            "id": printer["id"],
            "registered": printer["registered"],
            "name": name,
            "comment": comment,
        },
    )

    # Verify that registered happened almost now (within 1 minute)
    diff = abs((datetime.now(tz=timezone.utc) - datetime.fromisoformat(printer["registered"])).total_seconds())
    assert diff < 60

    # Verify no spool assigned
    assert printer.get("spool") is None

    # Clean up
    httpx.delete(f"{URL}/api/v1/printer/{printer['id']}").raise_for_status()


def test_add_printer_required():
    """Test adding a printer with only the required fields to the database."""
    name = "Ender 3"
    result = httpx.post(
        f"{URL}/api/v1/printer",
        json={"name": name},
    )
    result.raise_for_status()

    printer = result.json()
    assert_dicts_compatible(
        printer,
        {
            "id": printer["id"],
            "registered": printer["registered"],
            "name": name,
        },
    )

    # Clean up
    httpx.delete(f"{URL}/api/v1/printer/{printer['id']}").raise_for_status()


def test_add_printer_with_spool():
    """Test adding a printer with a spool assigned."""
    with random_spool_impl() as spool:
        result = httpx.post(
            f"{URL}/api/v1/printer",
            json={
                "name": "Printer with spool",
                "spool_id": spool["id"],
            },
        )
        result.raise_for_status()

        printer = result.json()
        assert printer["spool"] is not None
        assert printer["spool"]["id"] == spool["id"]

        # Clean up
        httpx.delete(f"{URL}/api/v1/printer/{printer['id']}").raise_for_status()


def test_add_printer_duplicate_spool():
    """Test that assigning the same spool to two printers fails."""
    with random_spool_impl() as spool:
        # First printer with the spool
        result1 = httpx.post(
            f"{URL}/api/v1/printer",
            json={
                "name": "Printer 1",
                "spool_id": spool["id"],
            },
        )
        result1.raise_for_status()

        # Second printer with the same spool should fail
        result2 = httpx.post(
            f"{URL}/api/v1/printer",
            json={
                "name": "Printer 2",
                "spool_id": spool["id"],
            },
        )
        assert result2.status_code == 400

        # Clean up
        httpx.delete(f"{URL}/api/v1/printer/{result1.json()['id']}").raise_for_status()
