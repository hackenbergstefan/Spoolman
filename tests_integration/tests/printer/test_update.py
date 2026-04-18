"""Integration tests for the Printer API endpoint."""

import httpx

from ..conftest import URL, assert_dicts_compatible, assert_httpx_success, random_printer_impl, random_spool_impl


def test_update_printer():
    """Test updating a printer."""
    with random_printer_impl() as printer:
        new_name = "Updated Printer"
        new_comment = "Updated comment"
        result = httpx.patch(
            f"{URL}/api/v1/printer/{printer['id']}",
            json={
                "name": new_name,
                "comment": new_comment,
            },
        )
        assert_httpx_success(result)

        updated = result.json()
        assert_dicts_compatible(
            updated,
            {
                "id": printer["id"],
                "name": new_name,
                "comment": new_comment,
            },
        )


def test_update_printer_assign_spool():
    """Test assigning a spool to a printer via update."""
    with random_printer_impl() as printer, random_spool_impl() as spool:
        result = httpx.patch(
            f"{URL}/api/v1/printer/{printer['id']}",
            json={"spool_id": spool["id"]},
        )
        assert_httpx_success(result)

        updated = result.json()
        assert updated["spool"] is not None
        assert updated["spool"]["id"] == spool["id"]


def test_update_printer_remove_spool():
    """Test removing a spool from a printer via update."""
    with random_spool_impl() as spool:
        # Create printer with spool
        result = httpx.post(
            f"{URL}/api/v1/printer",
            json={
                "name": "Printer with spool",
                "spool_id": spool["id"],
            },
        )
        result.raise_for_status()
        printer = result.json()

        # Remove spool
        result = httpx.patch(
            f"{URL}/api/v1/printer/{printer['id']}",
            json={"spool_id": None},
        )
        assert_httpx_success(result)

        updated = result.json()
        assert updated.get("spool") is None

        # Clean up
        httpx.delete(f"{URL}/api/v1/printer/{printer['id']}").raise_for_status()


def test_update_printer_duplicate_spool():
    """Test that assigning the same spool to two printers via update fails."""
    with random_spool_impl() as spool:
        # Create first printer with spool
        result1 = httpx.post(
            f"{URL}/api/v1/printer",
            json={
                "name": "Printer 1",
                "spool_id": spool["id"],
            },
        )
        result1.raise_for_status()
        printer1 = result1.json()

        # Create second printer
        result2 = httpx.post(
            f"{URL}/api/v1/printer",
            json={"name": "Printer 2"},
        )
        result2.raise_for_status()
        printer2 = result2.json()

        # Assign same spool to second printer should fail
        result3 = httpx.patch(
            f"{URL}/api/v1/printer/{printer2['id']}",
            json={"spool_id": spool["id"]},
        )
        assert result3.status_code == 400

        # Clean up
        httpx.delete(f"{URL}/api/v1/printer/{printer2['id']}").raise_for_status()
        httpx.delete(f"{URL}/api/v1/printer/{printer1['id']}").raise_for_status()


def test_update_printer_not_found():
    """Test updating a printer that does not exist."""
    result = httpx.patch(
        f"{URL}/api/v1/printer/999999",
        json={"name": "Does not exist"},
    )
    assert result.status_code == 404
