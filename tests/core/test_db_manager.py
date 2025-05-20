import sqlite3

import pytest

from core.config import settings
from core.db_manager import (
    get_agent_state,
    get_approved_reply_tasks,
    get_db_connection,
    initialize_database,
    save_agent_state,
    save_human_review_item,
    update_human_review_status,
)


def setup_database(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(settings, "sqlite_db_path", str(db_file))
    conn = get_db_connection()
    initialize_database(conn)
    conn.close()


def test_save_and_get_agent_state(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    save_agent_state("my_key", "my_value")
    assert get_agent_state("my_key") == "my_value"


def test_get_agent_state_nonexistent(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    assert get_agent_state("no_key") is None


def test_update_agent_state(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    save_agent_state("k", "v1")
    first_val = get_agent_state("k")
    save_agent_state("k", "v2")
    second_val = get_agent_state("k")
    assert first_val == "v1"
    assert second_val == "v2"
    assert first_val != second_val


def test_save_human_review_item_success(tmp_path, monkeypatch):
    """Test that save_human_review_item inserts the correct row and returns review_id."""
    setup_database(tmp_path, monkeypatch)
    from core.db_manager import get_db_connection as _get_db_connection

    data_json = '{"foo":"bar"}'
    reason = "Need review"
    status = "pending_review"
    review_id = save_human_review_item("mention", data_json, reason, status)
    assert isinstance(review_id, int)

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        (
            "SELECT review_id, task_queue_id, task_type, reason_for_review, "
            "data_for_review, status FROM human_review_queue WHERE review_id = ?"
        ),
        (review_id,),
    )
    row = cursor.fetchone()
    conn.close()

    assert row["review_id"] == review_id
    assert row["task_queue_id"] is None
    assert row["task_type"] == "mention"
    assert row["reason_for_review"] == reason
    assert row["data_for_review"] == data_json
    assert row["status"] == status


def test_save_human_review_item_error(monkeypatch):
    """Test that save_human_review_item raises sqlite3.Error when DB operation fails."""
    import core.db_manager as db_manager

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def execute(self, *args, **kwargs):
            raise sqlite3.Error("db failure")

        def close(self):
            pass

    monkeypatch.setattr(db_manager, "get_db_connection", lambda: DummyConn())
    with pytest.raises(sqlite3.Error):
        db_manager.save_human_review_item("type", "{}", "reason")


def test_get_approved_reply_tasks_empty(tmp_path, monkeypatch):
    """Test that get_approved_reply_tasks returns an empty list when no approved tasks exist."""
    setup_database(tmp_path, monkeypatch)

    tasks = get_approved_reply_tasks()
    assert tasks == []


def test_get_approved_reply_tasks_with_various(tmp_path, monkeypatch):
    """Test that get_approved_reply_tasks returns only approved reply_to_mention tasks."""
    setup_database(tmp_path, monkeypatch)
    from core.db_manager import save_human_review_item

    # Insert approved reply_to_mention
    data1 = '{"draft_reply_text":"reply1","original_mention_id":"1"}'
    id1 = save_human_review_item("reply_to_mention", data1, "reason1", initial_status="approved")
    # Insert approved but different task_type
    data2 = '{"foo":"bar"}'
    save_human_review_item("other_type", data2, "reason2", initial_status="approved")
    # Insert pending reply_to_mention
    data3 = '{"draft_reply_text":"reply3","original_mention_id":"3"}'
    save_human_review_item("reply_to_mention", data3, "reason3", initial_status="pending_review")

    tasks = get_approved_reply_tasks()
    assert len(tasks) == 1
    assert tasks[0]["review_id"] == id1
    assert tasks[0]["data_for_review"] == data1


def test_update_human_review_status_updates_status_and_timestamp(tmp_path, monkeypatch):
    """Test that update_human_review_status correctly updates the status and reviewed_at timestamp."""
    setup_database(tmp_path, monkeypatch)
    from core.db_manager import (
        get_db_connection,
        save_human_review_item,
    )

    data = '{"draft_reply_text":"reply","original_mention_id":"42"}'
    review_id = save_human_review_item(
        "reply_to_mention", data, "reason", initial_status="approved"
    )
    update_human_review_status(review_id, "posted_successfully")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status, reviewed_at FROM human_review_queue WHERE review_id = ?", (review_id,)
    )
    row = cursor.fetchone()
    conn.close()

    assert row["status"] == "posted_successfully"
    assert row["reviewed_at"] is not None
