import os
import datetime

# from datetime import datetime as dt
import pytest
from unittest import mock
from Logger.Logger import Logger
from constants import LOG_DIR, LOG_FILE_SIZE, APP_PATH


@pytest.fixture
def logger():
    return Logger(min_severity=3, log_dir=LOG_DIR, max_size_mb=LOG_FILE_SIZE)


FAKE_TIME = datetime.datetime(2023, 6, 1, 12, 0, 0)


@pytest.fixture
def patch_datetime_now(monkeypatch):
    class mydatetime(datetime.datetime):
        @classmethod
        def now(cls):
            return FAKE_TIME

    monkeypatch.setattr(datetime, "datetime", mydatetime)


def test_log(logger, mocker, patch_datetime_now):
    mocker.patch("os.path.exists", return_value=True)
    mock_size = mocker.patch(
        "os.stat", return_value=mock.Mock(st_size=logger._max_size + 1)
    )
    mocker.patch("os.remove")
    mocker.patch("os.rename")
    mock_open = mocker.patch("builtins.open", mock.mock_open())
    mock_now = mocker.patch(
        "datetime.datetime.now", return_value=datetime.datetime(2023, 6, 1, 12, 0, 0)
    )
    logger.log(3, "Test message")

    mock_open.assert_called_once_with(logger._log_file2, "a")
    # mock_open().write.assert_called_once_with("3 2023-06-01 12:00:00 Test message\n")


def test_log_severity_threshold(logger, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.stat", return_value=mock.Mock(st_size=0))
    mock_open = mocker.patch("builtins.open", mock.mock_open())

    logger.log(4, "Low severity message")

    mock_open.assert_not_called()


def test_check_dir_creation(logger, mocker):
    mocker.patch("os.path.exists", return_value=False)
    mock_mkdir = mocker.patch("os.mkdir")

    logger._check_dir()
    mock_mkdir.assert_called_once_with(os.path.join(APP_PATH, LOG_DIR))


def test_select_file_rotation(logger, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.stat",
        side_effect=[
            mock.Mock(st_size=logger._max_size + 1),
            mock.Mock(st_size=logger._max_size + 1),
        ],
    )
    mock_remove = mocker.patch("os.remove")
    mock_rename = mocker.patch("os.rename")
    selected_file = logger._select_file()
    assert selected_file == logger._log_file2
    mock_remove.assert_called_once_with(logger._log_file1)
    mock_rename.assert_called_once_with(logger._log_file2, logger._log_file1)
