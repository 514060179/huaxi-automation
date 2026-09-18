from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .accounts import Account, AccountLoadError, load_account_file, load_accounts
from .client import ApiError, HxaccClient
from .config import Config, load_config
from .oss_upload import OssAccountUploader
from .orchestrator import Orchestrator
from .storage import RunStore
from .wechat import WeChatNotifier


DEFAULT_WECOM_WEBHOOK_URL = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    "?key=de2d8b32-ca95-4117-b349-816feb0347d2"
)

COMPENSATION_LOCK = threading.Lock()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Real-environment normal-path integration harness")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument(
        "--account-dir",
        default=os.getenv(
            "ACCOUNT_DIR",
            "/Users/liuyingying/simon/work/automation/account",
        ),
        help="Directory containing .account JSON files",
    )
    parser.add_argument(
        "--compensate",
        action="store_true",
        help="Only retry accounts recorded in the compensation queue",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=int(os.getenv("MAX_PARALLEL_ACCOUNTS", "3")),
        help="Maximum number of accounts to run in parallel",
    )
    return parser


def configure_logging(
    log_path: Path,
    logger_name: str = "integration_harness",
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def _make_session_id(index: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"{timestamp}-{index:02d}"


@dataclass
class _PreparedAccount:
    account: Account
    index: int
    session_id: str
    config: Config
    notifier: WeChatNotifier
    uploader: OssAccountUploader


def _compensation_queue_path() -> Path:
    path = Path(os.getenv("RUNS_DIR", "runs"))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path / ".compensation_queue.jsonl"


def _append_compensation(account: Account, error: str) -> None:
    path = _compensation_queue_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with COMPENSATION_LOCK:
        with path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "source_path": str(account.source_path),
                        "error": error,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def _compensation_sources() -> list[str]:
    path = _compensation_queue_path()
    if not path.exists():
        return []
    with COMPENSATION_LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
    sources: list[str] = []
    seen: set[str] = set()
    for line in lines:
        try:
            payload = json.loads(line)
            source = payload.get("source_path")
        except json.JSONDecodeError:
            continue
        if isinstance(source, str) and source and source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


def _remove_compensation(account: Account) -> None:
    source = str(account.source_path)
    path = _compensation_queue_path()
    if not path.exists():
        return
    with COMPENSATION_LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
        remaining: list[str] = []
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                remaining.append(line)
                continue
            if payload.get("source_path") != source:
                remaining.append(line)
        path.write_text(
            "\n".join(remaining) + ("\n" if remaining else ""),
            encoding="utf-8",
        )


def _is_in_run_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    return start_hour <= now.hour < end_hour


def _run_one(
    config: Config,
    session_id: str,
    notifier: WeChatNotifier,
    id_card: str,
    name: str,
    replay: bool,
    oss_uploader: OssAccountUploader,
) -> int:
    run_dir = config.runs_dir / session_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = configure_logging(
        run_dir / "run.log",
        logger_name=f"integration_harness.account.{id_card}",
    )

    store = RunStore(run_dir / "events.sqlite3")
    client = HxaccClient(config)
    store.create_session(
        session_id,
        config.token_prefix,
        datetime.now(timezone.utc).isoformat(),
    )

    orchestrator = Orchestrator(
        config=config,
        client=client,
        store=store,
        session_id=session_id,
        logger=logger,
        notifier=notifier,
        id_card=id_card,
        name=name,
        replay=replay,
        oss_uploader=oss_uploader,
    )

    try:
        orchestrator.run()
    except Exception as exc:
        logger.exception("运行失败：%s", exc)
        if not getattr(exc, "already_notified", False):
            ok = notifier.send_exception(
                app_id=config.app_id,
                token_prefix=config.token_prefix,
                device_id=config.device_id,
                session_id=session_id,
                exc=exc,
                id_card=id_card,
                name=name,
            )
            if not ok:
                logger.warning(
                    "运行异常的企业微信推送失败，已写入本地待发队列"
                )
        store.update_session_state(
            session_id,
            "failed",
            datetime.now(timezone.utc).isoformat(),
        )
        return 1
    finally:
        orchestrator.shutdown_qr_server()
        client.close()
        store.close()

    logger.info("运行完成，产物目录：%s", run_dir)
    print(f"Run directory: {run_dir}")
    return 0


def _run_prepared(task: _PreparedAccount) -> int:
    account = task.account
    config = task.config
    notifier = task.notifier
    uploader = task.uploader
    session_id = task.session_id

    try:
        oss_dir = f"hxacc/account/{account.id_card}"
        oss_key = f"{oss_dir}/{account.source_path.name}"
        upload_result = uploader.upload_file(account.source_path, oss_key)
        if not upload_result.success:
            print(
                f"OSS 上传失败 {oss_key}: {upload_result.error}",
                file=sys.stderr,
            )
            notifier.send_exception(
                app_id=config.app_id,
                token_prefix=config.token_prefix,
                device_id=config.device_id,
                session_id=session_id,
                exc=RuntimeError(f"OSS 上传失败 {oss_key}: {upload_result.error}"),
                id_card=account.id_card,
                name=account.name,
            )
            _append_compensation(
                account,
                f"OSS 上传失败 {oss_key}: {upload_result.error}",
            )
            return 1
        print(f"OSS 上传成功：{oss_key}")

        now = datetime.now()
        if not _is_in_run_window(
            now,
            config.run_start_hour,
            config.run_end_hour,
        ):
            notifier.send_time_window_blocked(
                app_id=config.app_id,
                token_prefix=config.token_prefix,
                device_id=config.device_id,
                start_hour=config.run_start_hour,
                end_hour=config.run_end_hour,
                id_card=account.id_card,
                name=account.name,
            )
            print(
                f"当前时间 {now:%H:%M:%S} 不在允许运行窗口内，跳过 appId={config.app_id}",
                file=sys.stderr,
            )
            return 0

        result = _run_one(
            config,
            session_id,
            notifier,
            account.id_card,
            account.name,
            account.replay,
            uploader,
        )
        if result != 0:
            _append_compensation(
                account,
                f"课程学习执行失败，退出码：{result}",
            )
            return result

        success_key = (
            f"{oss_dir}/{datetime.now().strftime('%Y%m%d%H%M%S')}.success"
        )
        success_result = uploader.upload_text(success_key)
        if not success_result.success:
            print(
                f"OSS success 标记上传失败 {success_key}: {success_result.error}",
                file=sys.stderr,
            )
            notifier.send_exception(
                app_id=config.app_id,
                token_prefix=config.token_prefix,
                device_id=config.device_id,
                session_id=session_id,
                exc=RuntimeError(
                    f"OSS success 标记上传失败 {success_key}: {success_result.error}"
                ),
                id_card=account.id_card,
                name=account.name,
            )
            _append_compensation(
                account,
                f"OSS success 标记上传失败 {success_key}: {success_result.error}",
            )
            return 1

        print(f"OSS success 标记上传成功：{success_key}")
        _remove_compensation(account)
        return 0
    except Exception as exc:
        print(f"{account.id_card} 执行失败：{exc}", file=sys.stderr)
        try:
            notifier.send_exception(
                app_id=config.app_id,
                token_prefix=config.token_prefix,
                device_id=config.device_id,
                session_id=session_id,
                exc=exc,
                id_card=account.id_card,
                name=account.name,
            )
        except Exception:
            pass
        _append_compensation(
            account,
            f"{type(exc).__name__}: {exc}",
        )
        return 1
    finally:
        notifier.close()


def _load_compensation_accounts() -> list[Account]:
    accounts: list[Account] = []
    for source in _compensation_sources():
        try:
            accounts.append(load_account_file(Path(source)))
        except Exception as exc:
            print(
                f"补偿账户读取失败，保留在队列中：{source}：{exc}",
                file=sys.stderr,
            )
    return accounts


def _prepare_accounts(accounts: list[Account]) -> tuple[list[_PreparedAccount], int]:
    prepared: list[_PreparedAccount] = []
    exit_code = 0
    for index, account in enumerate(accounts, 1):
        overrides = {
            "APP_ID": account.app_id,
            "HXACC_TOKEN": account.token,
            "HXACC_DEVICE_ID": account.device_id,
        }
        try:
            config = load_config(overrides)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            notifier = WeChatNotifier(DEFAULT_WECOM_WEBHOOK_URL)
            notifier.send_exception(
                app_id=account.app_id,
                token_prefix="<unknown>",
                device_id=account.device_id,
                session_id="<config-error>",
                exc=exc,
                id_card=account.id_card,
                name=account.name,
            )
            notifier.close()
            _append_compensation(account, f"{type(exc).__name__}: {exc}")
            exit_code = 2
            continue

        notifier = WeChatNotifier(
            config.wecom_webhook_url,
            outbox_path=config.runs_dir / ".wecom_outbox.jsonl",
        )
        notifier.flush_outbox()
        uploader = OssAccountUploader(
            access_key_id=config.oss_access_key_id,
            access_key_secret=config.oss_access_key_secret,
            bucket_name=config.oss_bucket,
            endpoint=config.oss_endpoint,
        )
        prepared.append(
            _PreparedAccount(
                account=account,
                index=index,
                session_id=_make_session_id(index),
                config=config,
                notifier=notifier,
                uploader=uploader,
            )
        )
    return prepared, exit_code


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.compensate:
        accounts = _load_compensation_accounts()
        if not accounts:
            print("没有需要补偿执行的账户", file=sys.stderr)
            return 0
    else:
        try:
            accounts = load_accounts(Path(args.account_dir).expanduser())
        except AccountLoadError as exc:
            print(str(exc), file=sys.stderr)
            notifier = WeChatNotifier(DEFAULT_WECOM_WEBHOOK_URL)
            notifier.send_exception(
                app_id="<unknown>",
                token_prefix="<unknown>",
                device_id="<unknown>",
                session_id="<account-load-error>",
                exc=exc,
                id_card="<unknown>",
                name="<unknown>",
            )
            notifier.close()
            return 2

    prepared, exit_code = _prepare_accounts(accounts)
    if not prepared:
        return exit_code

    max_workers = max(1, min(args.max_workers, len(prepared)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_prepared, task): task
            for task in prepared
        }
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                task = futures[future]
                _append_compensation(
                    task.account,
                    f"{type(exc).__name__}: {exc}",
                )
                result = 1
            if result != 0:
                exit_code = max(exit_code, result)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
