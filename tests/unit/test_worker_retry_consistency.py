import pytest
from unittest.mock import patch, MagicMock
from services.ingestion.worker import process_document, update_doc_status


def test_worker_db_status_update_consistency():
    """
    Ensure synchronous DB status updates work reliably and don't reuse corrupted loops.
    """
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg2.connect", return_value=mock_conn):
        # 1. Processing update
        update_doc_status("test-doc-uuid", "processing")
        mock_cursor.execute.assert_called_with(
            "UPDATE documents SET status = %s, error_message = %s WHERE id = %s",
            ("processing", None, "test-doc-uuid"),
        )
        assert mock_conn.commit.called

        # 2. Failure update with error message
        mock_conn.reset_mock()
        mock_cursor.reset_mock()
        update_doc_status("test-doc-uuid", "failed", "Ollama connection timeout")
        mock_cursor.execute.assert_called_with(
            "UPDATE documents SET status = %s, error_message = %s WHERE id = %s",
            ("failed", "Ollama connection timeout", "test-doc-uuid"),
        )
        assert mock_conn.commit.called


def test_worker_retry_failure_updates_db_consistently():
    """
    Regression test: When worker fails mid-task (e.g. MinIO download error),
    verify that update_doc_status('failed', error) is invoked and exception is re-raised
    for Celery's autoretry mechanism without leaving the DB in a stale 'processing' state.
    """
    with patch("services.ingestion.worker.update_doc_status") as mock_update, \
         patch("services.ingestion.worker._download_from_minio", return_value=False):

        with pytest.raises(Exception) as exc_info:
            process_document("tenant-1", "doc-123", "documents/doc-123/contract.pdf")

        assert "Failed to download document from MinIO" in str(exc_info.value)

        # Assert status was set to processing first, and then to failed on error
        calls = [c[0] for c in mock_update.call_args_list]
        assert calls[0] == ("doc-123", "processing")
        assert calls[1][0] == "doc-123"
        assert calls[1][1] == "failed"
        assert "Failed to download" in calls[1][2]

