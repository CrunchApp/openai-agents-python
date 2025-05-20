import logging

import pytest

import project_agents.scheduling_agent as sched_module
from project_agents.scheduling_agent import SchedulingAgent


def test_schedule_successful(mocker, caplog):
    """
    Test that schedule_mention_processing successfully schedules a job with the default interval.
    """
    # Arrange
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)

    # Act
    caplog.set_level(logging.INFO)
    scheduling_agent.schedule_mention_processing()

    # Ensure a job was scheduled with the wrapper function
    assert mock_scheduler.add_job.call_count == 1
    args, kwargs = mock_scheduler.add_job.call_args
    scheduled_func = args[0]
    assert callable(scheduled_func)
    assert scheduled_func.__name__ == "_run_orchestrator_workflow"
    assert kwargs == {
        "trigger": "interval",
        "minutes": 5,
        "id": "process_mentions_job",
        "replace_existing": True,
    }
    # Assert logging
    assert "Scheduled job 'process_mentions_job' to run every 5 minutes." in caplog.text


def test_schedule_failure(mocker, caplog):
    """
    Test that schedule_mention_processing logs an error and re-raises when add_job fails.
    """
    # Arrange
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    mock_scheduler.add_job.side_effect = Exception("APScheduler error")
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)

    # Act & Assert
    caplog.set_level(logging.ERROR)
    with pytest.raises(Exception) as excinfo:
        scheduling_agent.schedule_mention_processing()

    # Exception contains the original message
    assert "APScheduler error" in str(excinfo.value)
    # Error log contains formatted message
    assert "Failed to schedule job: APScheduler error" in caplog.text


def test_run_orchestrator_workflow_invokes_runner_and_asyncio_run(mocker):
    """Test that the scheduled wrapper calls Runner.run and asyncio.run."""
    # Arrange: use mocks for orchestrator and scheduler
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)
    # Act: schedule to capture the wrapper
    scheduling_agent.schedule_mention_processing()
    # Extract the scheduled wrapper
    call_args = mock_scheduler.add_job.call_args
    scheduled_func = call_args[0][0]
    # Patch Runner.run to return a dummy coroutine
    dummy_coro = object()
    mocker.patch.object(sched_module.Runner, "run", return_value=dummy_coro)
    # Patch asyncio.run in the scheduling_agent module
    mock_asyncio_run = mocker.patch.object(sched_module.asyncio, "run")
    # Act: invoke the wrapper
    scheduled_func()
    # Assert that Runner.run was called with the orchestrator and correct input
    sched_module.Runner.run.assert_called_once_with(
        mock_orchestrator, input="Process new X mentions."
    )
    # Assert that asyncio.run was called with the dummy coroutine
    mock_asyncio_run.assert_called_once_with(dummy_coro)


# Tests for schedule_approved_reply_processing and its wrapper
def test_schedule_approved_reply_successful(mocker, caplog):
    """Test that schedule_approved_reply_processing successfully schedules the job."""
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)

    caplog.set_level(logging.INFO)
    scheduling_agent.schedule_approved_reply_processing(interval_minutes=2)

    assert mock_scheduler.add_job.call_count == 1
    args, kwargs = mock_scheduler.add_job.call_args
    scheduled_func = args[0]
    assert callable(scheduled_func)
    assert scheduled_func.__name__ == "_run_orchestrator_approved_replies_workflow"
    assert kwargs == {
        "trigger": "interval",
        "minutes": 2,
        "id": "process_approved_replies_job",
        "replace_existing": True,
    }
    assert "Scheduled job 'process_approved_replies_job' to run every 2 minutes." in caplog.text


def test_schedule_approved_reply_failure(mocker, caplog):
    """Test that schedule_approved_reply_processing logs error and re-raises."""
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    mock_scheduler.add_job.side_effect = Exception("Approved job scheduling error")
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)

    caplog.set_level(logging.ERROR)
    with pytest.raises(Exception) as excinfo:
        scheduling_agent.schedule_approved_reply_processing()

    assert "Approved job scheduling error" in str(excinfo.value)
    assert "Failed to schedule approved replies job: Approved job scheduling error" in caplog.text


def test_run_orchestrator_approved_replies_workflow_invokes_runner_and_asyncio_run(mocker):
    """Test that the approved replies wrapper calls Runner.run and asyncio.run."""
    mock_orchestrator = mocker.Mock()
    mock_scheduler = mocker.Mock()
    scheduling_agent = SchedulingAgent(mock_orchestrator, mock_scheduler)
    scheduling_agent.schedule_approved_reply_processing()

    call_args = mock_scheduler.add_job.call_args
    scheduled_func = call_args[0][0]

    dummy_coro = object()
    mocker.patch.object(sched_module.Runner, "run", return_value=dummy_coro)
    mock_asyncio_run = mocker.patch.object(sched_module.asyncio, "run")

    scheduled_func()

    sched_module.Runner.run.assert_called_once_with(
        mock_orchestrator, input="Process approved X replies."
    )
    mock_asyncio_run.assert_called_once_with(dummy_coro)
