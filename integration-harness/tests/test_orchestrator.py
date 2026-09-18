import pytest
import hashlib
import json
from datetime import datetime, timezone

from integration_harness.orchestrator import (
    Orchestrator,
    _NoUnfinishedLearning,
)


class _DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


def test_heartbeat_needs_restart_when_status_message_is_not_success():
    response = {
        "status": {"code": 0, "message": "学习过程中不允许打开多个窗口"},
        "data": {},
    }

    assert Orchestrator._heartbeat_needs_restart(response) is True


def test_heartbeat_needs_restart_when_new_course_will_close_page():
    response = {
        "status": {
            "code": 0,
            "message": "您正在学习新课程《会计人员职业道德规范》，当前视频页面将要关闭。",
        },
        "data": {},
    }

    assert Orchestrator._heartbeat_needs_restart(response) is True


def test_heartbeat_does_not_restart_on_success():
    response = {
        "status": {"code": 0, "message": "SUCCESS"},
        "data": {"code": 1},
    }

    assert Orchestrator._heartbeat_needs_restart(response) is False


def test_heartbeat_does_not_restart_when_status_message_is_missing():
    response = {"data": {"code": -20, "message": "心跳间隔过短"}}

    assert Orchestrator._heartbeat_needs_restart(response) is False


def test_select_course_and_doc_skips_when_all_docs_are_finished():
    course_list = {
        "data": {
            "list": [
                {
                    "courseInfo": {
                        "body": [
                            {
                                "child": [
                                    {"docId": "first-doc"},
                                ]
                            }
                        ]
                    },
                    "mycourseInfo": {
                        "learned": {"first-doc": {"status": "finish"}},
                        "lastDocId": "last-doc",
                    },
                }
            ]
        }
    }

    with pytest.raises(_NoUnfinishedLearning, match="课程小节已全部完成"):
        Orchestrator._select_course_and_doc(None, course_list)


def test_select_course_and_doc_returns_first_unfinished_doc():
    course_list = {
        "data": {
            "list": [
                {
                    "courseInfo": {
                        "body": [
                            {
                                "child": [
                                    {"docId": "finished-doc"},
                                    {"docId": "unfinished-doc"},
                                ]
                            }
                        ]
                    },
                    "mycourseInfo": {
                        "learned": {"finished-doc": {"status": "finish"}},
                    },
                }
            ]
        }
    }

    course_info, doc_id = Orchestrator._select_course_and_doc(None, course_list)

    assert doc_id == "unfinished-doc"


def test_select_course_and_doc_allows_finished_doc_when_replay_true():
    course_list = {
        "data": {
            "list": [
                {
                    "courseInfo": {
                        "body": [{"child": [{"docId": "finished-doc"}]}]
                    },
                    "mycourseInfo": {
                        "learnedStatus": 2,
                        "learnedProgress": 100,
                        "learned": {"finished-doc": {"status": "finish"}},
                    },
                }
            ]
        }
    }
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.replay = True

    course_info, doc_id = orchestrator._select_course_and_doc(course_list)

    assert doc_id == "finished-doc"


def test_select_course_and_doc_skips_finished_course_marker():
    course_list = {
        "data": {
            "list": [
                {
                    "courseInfo": {
                        "body": [{"child": [{"docId": "doc-1"}]}]
                    },
                    "mycourseInfo": {
                        "learnedStatus": 2,
                        "learnedProgress": 100,
                        "learned": {},
                    },
                },
                {
                    "courseInfo": {
                        "body": [{"child": [{"docId": "doc-2"}]}]
                    },
                    "mycourseInfo": {
                        "learnedStatus": 1,
                        "learnedProgress": 20,
                        "learned": {},
                    },
                },
            ]
        }
    }

    course_info, doc_id = Orchestrator._select_course_and_doc(None, course_list)

    assert doc_id == "doc-2"


def test_course_is_finished_recognizes_status_and_progress():
    assert Orchestrator._course_is_finished({"learnedStatus": 2}) is True
    assert Orchestrator._course_is_finished({"learnedProgress": 100}) is True
    assert Orchestrator._course_is_finished({"learnedStatus": 1}) is False


def test_next_unfinished_course_id_uses_learned_progress():
    detail = {
        "data": {
            "mytaskInfo": {
                "learned": {
                    "finished-course": {"lp": 100},
                    "unfinished-course": {"lp": 27},
                }
            }
        }
    }

    assert (
        Orchestrator._next_unfinished_course_id(None, detail)
        == "unfinished-course"
    )


def test_next_unfinished_course_id_excludes_skipped_courses():
    detail = {
        "data": {
            "mytaskInfo": {
                "learned": {
                    "course-a": {"lp": 20},
                    "course-b": {"lp": 30},
                }
            }
        }
    }

    assert (
        Orchestrator._next_unfinished_course_id(
            None,
            detail,
            exclude={"course-a"},
        )
        == "course-b"
    )


def test_find_course_group_returns_matching_group():
    detail = {
        "data": {
            "taskInfo": {
                "courseConfig": [
                    {
                        "id": "config-1",
                        "courseGroup": [
                            {
                                "id": "group-1",
                                "courseIds": ["course-a", "course-b"],
                            }
                        ],
                    }
                ]
            }
        }
    }

    assert Orchestrator._find_course_group(None, detail, "course-b") == (
        "config-1",
        ["course-b"],
    )


def test_find_target_seconds_prefers_learned_total_time():
    course_detail = {
        "data": {
            "docInfo": {"duration": 999},
            "mycourseInfo": {
                "learned": {
                    "doc-id": {"totalTime": 1234},
                }
            },
        }
    }

    assert Orchestrator._find_target_seconds(None, course_detail, "doc-id") == 1234


def test_find_target_seconds_falls_back_to_doc_duration():
    course_detail = {
        "data": {
            "docInfo": {"duration": 888},
            "mycourseInfo": {"learned": {}},
        }
    }

    assert Orchestrator._find_target_seconds(None, course_detail, "doc-id") == 888


def test_resolve_current_doc_id_prefers_doc_info():
    course_detail = {
        "data": {
            "docInfo": {"id": "actual-doc"},
            "mycourseInfo": {"lastDocId": "fallback-doc"},
        }
    }

    assert Orchestrator._resolve_current_doc_id(None, course_detail) == "actual-doc"


def test_resolve_current_doc_id_falls_back_to_last_doc_id():
    course_detail = {
        "data": {
            "mycourseInfo": {"lastDocId": "fallback-doc"},
        }
    }

    assert Orchestrator._resolve_current_doc_id(None, course_detail) == "fallback-doc"


def test_qr_expires_at_uses_check_end_time():
    created_at = datetime(2026, 9, 17, 1, 0, 0, tzinfo=timezone.utc)
    orchestrator = Orchestrator.__new__(Orchestrator)

    expires_at = orchestrator._qr_expires_at(
        {"checkEndTime": 1789454606189},
        created_at,
    )

    assert expires_at.timestamp() == 1789454606.189


class _FakeOssUploader:
    def __init__(self) -> None:
        self.bytes = []
        self.texts = []

    def upload_bytes(self, key, content):
        self.bytes.append((key, content))
        return type("Result", (), {"key": key, "success": True, "error": None})()

    def upload_text(self, key, content):
        self.texts.append((key, content))
        return type("Result", (), {"key": key, "success": True, "error": None})()


def test_upload_qr_artifacts_writes_png_and_required_json():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.id_card = "id-1"
    orchestrator.logger = _DummyLogger()
    orchestrator.oss_uploader = _FakeOssUploader()

    orchestrator._upload_qr_artifacts(
        point_code="point-1",
        qrcode_url="https://example.com/verify",
        trigger_data={},
    )

    assert len(orchestrator.oss_uploader.bytes) == 1
    png_key, png_bytes = orchestrator.oss_uploader.bytes[0]
    assert png_key == "hxacc/account/id-1/point-1.png"
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    assert len(orchestrator.oss_uploader.texts) == 1
    json_key, json_text = orchestrator.oss_uploader.texts[0]
    assert json_key == "hxacc/account/id-1/point-1.json"
    payload = json.loads(json_text)
    assert payload["task_id"] == "point-1"
    assert payload["created_at"].endswith("+08:00")
    assert payload["expires_at"].endswith("+08:00")
    assert payload["sha256"] == hashlib.sha256(png_bytes).hexdigest()


def test_select_course_and_doc_filters_by_course_id():
    course_list = {
        "data": {
            "list": [
                {
                    "courseInfo": {
                        "id": "course-a",
                        "body": [{"child": [{"docId": "doc-a"}]}],
                    },
                    "mycourseInfo": {"learnedStatus": 1, "learned": {}},
                },
                {
                    "courseInfo": {
                        "id": "course-b",
                        "body": [{"child": [{"docId": "doc-b"}]}],
                    },
                    "mycourseInfo": {"learnedStatus": 1, "learned": {}},
                },
            ]
        }
    }

    course_info, doc_id = Orchestrator._select_course_and_doc(
        None,
        course_list,
        course_id="course-b",
    )

    assert course_info["id"] == "course-b"
    assert doc_id == "doc-b"


def test_find_random_prefers_doc_info_over_learned_state():
    course_detail = {
        "data": {
            "docInfo": {"random": "doc-info-random"},
            "mycourseInfo": {
                "learned": {
                    "doc-id": {"random": "learned-random"},
                }
            },
        }
    }

    assert Orchestrator._find_random(None, course_detail, "doc-id") == "doc-info-random"


def test_select_tasks_returns_every_item_returned_by_api():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.config = type("Config", (), {"app_id": "app-id"})()
    orchestrator._post_json = lambda *args, **kwargs: {
        "data": {
            "list": [
                {"taskInfo": {"id": "task-1", "title": "公需课", "status": 1}},
                {"taskInfo": {"id": "task-2", "title": "专业课", "status": 1}},
            ]
        }
    }

    tasks = orchestrator._select_tasks()

    assert [item["taskInfo"]["id"] for item in tasks] == ["task-1", "task-2"]


def test_select_tasks_raises_when_api_returns_empty_list():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.config = type("Config", (), {"app_id": "app-id"})()
    orchestrator._post_json = lambda *args, **kwargs: {"data": {"list": []}}

    with pytest.raises(RuntimeError, match="接口未返回任何任务"):
        orchestrator._select_tasks()


def test_run_processes_all_tasks_sequentially():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.logger = _DummyLogger()
    orchestrator._set_state = lambda *args, **kwargs: None
    orchestrator._select_tasks = lambda: [
        {"taskInfo": {"id": "task-1", "title": "公需课"}},
        {"taskInfo": {"id": "task-2", "title": "专业课"}},
    ]

    processed = []

    def fake_run_task_with_restarts(task, *, index, total):
        processed.append(task["taskInfo"]["id"])
        return True

    orchestrator._run_task_with_restarts = fake_run_task_with_restarts

    orchestrator.run()

    assert processed == ["task-1", "task-2"]
