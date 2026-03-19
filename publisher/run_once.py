#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def load_config() -> dict:
    config_path = os.environ.get("REDBOOKAUTO_CONFIG", str(ROOT / "config.json"))
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("publisher")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_dir / "publisher.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.handlers = [file_handler, stream_handler]
    return logger


def acquire_lock(lock_path: Path, logger: logging.Logger) -> Optional[object]:
    lock_file = lock_path.open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.info("Another run is in progress; exiting.")
        return None
    return lock_file


def find_next_item(pending_dir: Path) -> Optional[Path]:
    if not pending_dir.exists():
        return None
    candidates = [p for p in pending_dir.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[0]


def read_meta(item_dir: Path) -> dict:
    meta_path = item_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.json missing in {item_dir}")
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_images(item_dir: Path, meta: dict) -> List[str]:
    images = meta.get("images")
    if images:
        resolved: List[str] = []
        for img in images:
            img_path = Path(img)
            if not img_path.is_absolute():
                img_path = item_dir / img_path
            resolved.append(str(img_path.expanduser().resolve()))
        return resolved

    found = []
    for path in item_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            found.append(path)
    return [str(p.resolve()) for p in sorted(found)]


def build_command(template: Iterable[str], context: dict) -> List[str]:
    expanded: List[str] = []

    for token in template:
        if token == "{images}":
            expanded.extend(context["images"])
            continue

        if "{images_csv}" in token:
            token = token.replace("{images_csv}", context["images_csv"])

        # Conditional placeholders: {tags?}
        for key in ("tags",):
            conditional = f"{{{key}?}}"
            if conditional in token:
                if not context[key]:
                    token = None
                else:
                    token = token.replace(conditional, context[key])
        if token is None:
            continue

        for key in ("title", "content", "tags"):
            placeholder = f"{{{key}}}"
            if placeholder in token:
                token = token.replace(placeholder, context[key])

        expanded.append(token)

    return expanded


def run_command(cmd: List[str], cwd: Path, logger: logging.Logger) -> subprocess.CompletedProcess:
    logger.info("Running command: %s", " ".join(shlex.quote(c) for c in cmd))
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Do not publish.")
    args = parser.parse_args()

    config = load_config()
    log_dir = ROOT / config.get("log_dir", "logs")
    logger = setup_logging(log_dir)

    lock = acquire_lock(ROOT / ".publish.lock", logger)
    if not lock:
        return 0

    queue_dir = ROOT / config.get("queue_dir", "queue")
    pending_dir = queue_dir / "pending"
    published_dir = queue_dir / "published"
    failed_dir = queue_dir / "failed"
    published_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    item_dir = find_next_item(pending_dir)
    if not item_dir:
        logger.info("No pending items found.")
        return 0

    try:
        meta = read_meta(item_dir)
        title = str(meta.get("title", "")).strip()
        content = str(meta.get("content", "")).strip()
        tags_list = meta.get("tags") or []
        tags = ",".join([str(t).strip() for t in tags_list if str(t).strip()])
        images = collect_images(item_dir, meta)
        if not title or not content:
            raise ValueError("title/content required")
        if not images:
            raise ValueError("no images found")

        context = {
            "title": title,
            "content": content,
            "tags": tags,
            "images": images,
            "images_csv": ",".join(images),
        }

        status = config.get("status", {})
        if status.get("enabled"):
            cmd = build_command(status["command"], context)
            result = run_command(cmd, ROOT, logger)
            if result.returncode != 0:
                raise RuntimeError(
                    f"status check failed: {result.stderr.strip() or result.stdout.strip()}"
                )

        publish_cfg = config.get("publish", {})
        template = publish_cfg.get("command")
        if not template:
            raise ValueError("publish.command is required in config.json")
        if isinstance(template, str):
            template = shlex.split(template)
        cmd = build_command(template, context)

        if args.dry_run:
            logger.info("Dry run: would publish %s", item_dir.name)
            return 0

        result = run_command(cmd, ROOT, logger)
        if result.returncode != 0:
            raise RuntimeError(
                f"publish failed: {result.stderr.strip() or result.stdout.strip()}"
            )

        target = published_dir / item_dir.name
        shutil.move(str(item_dir), str(target))
        write_json(
            target / "published.json",
            {
                "published_at": datetime.now().isoformat(timespec="seconds"),
                "command": cmd,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            },
        )
        logger.info("Published: %s", target.name)
        return 0
    except Exception as exc:
        logger.error("Failed: %s", exc)
        target = failed_dir / item_dir.name
        if item_dir.exists():
            shutil.move(str(item_dir), str(target))
        write_json(
            target / "error.json",
            {
                "failed_at": datetime.now().isoformat(timespec="seconds"),
                "error": str(exc),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
