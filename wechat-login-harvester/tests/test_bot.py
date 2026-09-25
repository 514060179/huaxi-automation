import json

from wechat_login_harvester.bot import (
    UserStore,
    clean_content,
    handle_text,
    parse_command,
    _stop_key,
)


def test_parse_add_command():
    command = parse_command("新增 姓名:张三 身份证:440682198001010011")
    assert command.action == "add"
    assert command.values == {
        "name": "张三",
        "id_card": "440682198001010011",
    }


def test_parse_add_command_with_chinese_colon():
    command = parse_command("新增 姓名：李四 身份证：440682198210063620")
    assert command.action == "add"
    assert command.values["name"] == "李四"
    assert command.values["id_card"] == "440682198210063620"


def test_parse_delete_command():
    command = parse_command("删除 身份证:440682198001010011")
    assert command.action == "delete"
    assert command.target_id == "440682198001010011"


def test_parse_update_command():
    command = parse_command(
        "修改 身份证:旧号码 姓名:新名字 身份证:新号码"
    )
    assert command.action == "update"
    assert command.target_id == "旧号码"
    assert command.values == {"id_card": "新号码", "name": "新名字"}


def test_handle_text_round_trip(tmp_path):
    store = UserStore(tmp_path / "user")
    store.write(
        [
            {"name": "梁敏仪", "id_card": "440682197801283620"},
            {"name": "梁映仪", "id_card": "440682198210063620", "skip": True},
        ]
    )

    assert "新增成功" in handle_text(
        store, "新增 姓名:陈丽梅 身份证:44142319821128074X"
    )
    users = store.read()
    assert len(users) == 3
    assert any(u["id_card"] == "44142319821128074X" for u in users)

    assert "删除成功" in handle_text(
        store, "删除 身份证:440682197801283620"
    )
    assert len(store.read()) == 2

    assert "修改成功" in handle_text(
        store, "修改 身份证:440682198210063620 姓名:梁映芬"
    )
    target = store.query("440682198210063620")[0]
    assert target["name"] == "梁映芬"

    reply = handle_text(store, "查询")
    assert "陈丽梅" in reply
    assert "梁映芬" in reply


def test_handle_text_add_duplicate(tmp_path):
    store = UserStore(tmp_path / "user")
    store.write([{"name": "张三", "id_card": "id-1"}])
    reply = handle_text(store, "新增 姓名:李四 身份证:id-1")
    assert "已存在" in reply


def test_user_store_write_is_valid_json(tmp_path):
    store = UserStore(tmp_path / "user")
    store.write([{"name": "张三", "id_card": "id-1", "skip": True}])
    payload = json.loads((tmp_path / "user").read_text(encoding="utf-8"))
    assert payload[0]["skip"] is True
    assert not (tmp_path / "user.tmp").exists()


def test_clean_content_strips_mention():
    assert clean_content("@RobotA 查询") == "查询"
    assert clean_content("查询") == "查询"
    assert clean_content("@RobotA") == ""


class FakeOss:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str]] = []
        self.deletes: list[str] = []

    def upload_text(self, key: str, content: str) -> None:
        self.uploads.append((key, content))

    def delete_object(self, key: str) -> bool:
        self.deletes.append(key)
        return True


def test_stop_and_resume_commands_write_and_delete_marker(tmp_path):
    store = UserStore(tmp_path / "user")
    store.write([{"name": "张三", "id_card": "id-1"}])
    oss = FakeOss()

    reply = handle_text(store, "停止 身份证:id-1", oss)
    assert "已发送停止指令" in reply
    assert oss.uploads == [(_stop_key("id-1"), "")]

    reply = handle_text(store, "恢复 身份证:id-1", oss)
    assert "已发送恢复指令" in reply
    assert oss.deletes == [_stop_key("id-1")]


def test_stop_command_rejects_unknown_user(tmp_path):
    store = UserStore(tmp_path / "user")
    store.write([{"name": "张三", "id_card": "id-1"}])
    reply = handle_text(store, "停止 身份证:unknown", FakeOss())
    assert "未找到身份证" in reply
