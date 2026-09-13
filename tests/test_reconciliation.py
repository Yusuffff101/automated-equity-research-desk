"""
tests/test_reconciliation.py — Unit test verifying memo reconciliation against live database.
"""

from sql.reconcile_memo import run_reconciliation


def test_memo_database_reconciliation():
    """Verify that all figures in UPST investment memo match financials.db exactly."""
    status = run_reconciliation()
    assert status == 0, f"Memo reconciliation failed with {status} mismatch warnings."
