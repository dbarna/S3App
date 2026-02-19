#!/usr/bin/env python3
"""macOS terminal backup/restore app for AWS S3."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = Exception

APP_DIR = Path.home() / ".s3_backup_cli"
CONFIG_FILE = APP_DIR / "config.json"


@dataclass
class BackupRoutine:
    name: str
    source_path: str
    s3_prefix: str
    frequency: str
    retention_count: int
    note: str = ""


@dataclass
class AppConfig:
    aws_profile: str = "default"
    bucket_name: str = ""
    routines: List[BackupRoutine] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "AppConfig":
        routines = [BackupRoutine(**r) for r in data.get("routines", [])]
        return AppConfig(
            aws_profile=data.get("aws_profile", "default"),
            bucket_name=data.get("bucket_name", ""),
            routines=routines,
        )


class S3BackupApp:
    def __init__(self) -> None:
        self.config = self.load_config()

    def run(self) -> None:
        if boto3 is None:
            print("Missing dependency: boto3. Run: pip install boto3")
            return

        while True:
            print("\n=== S3 Backup & Restore (macOS Terminal) ===")
            print("1) Configure AWS")
            print("2) Add backup routine")
            print("3) List routines")
            print("4) Run backup now")
            print("5) Restore backup")
            print("6) Create default strategy (Monthly/Weekly/Daily)")
            print("0) Exit")

            choice = self.prompt("Select option")
            if choice == "1":
                self.configure_aws()
            elif choice == "2":
                self.add_routine()
            elif choice == "3":
                self.list_routines()
            elif choice == "4":
                self.run_backup_now()
            elif choice == "5":
                self.restore_backup()
            elif choice == "6":
                self.create_default_strategy()
            elif choice == "0":
                self.save_config()
                print("Goodbye!")
                return
            else:
                print("Invalid option.")

    def prompt(self, label: str, default: Optional[str] = None) -> str:
        suffix = f" [{default}]" if default else ""
        return input(f"{label}{suffix}: ").strip() or (default or "")

    def prompt_path_anytime(self, action: str) -> str:
        print(f"Tip: you can paste the full path for {action} now.")
        path = self.prompt(f"Paste path for {action}")
        return os.path.expanduser(path)

    def configure_aws(self) -> None:
        self.config.aws_profile = self.prompt("AWS profile", self.config.aws_profile)
        self.config.bucket_name = self.prompt("S3 bucket name", self.config.bucket_name)
        self.save_config()
        print("AWS configuration saved.")

    def add_routine(self) -> None:
        print("\n--- New Backup Routine ---")
        name = self.prompt("Routine name (e.g., Daily)")
        source_path = self.prompt_path_anytime("backup source")
        s3_prefix = self.prompt("S3 prefix/folder (e.g., backups/my-mac)")
        frequency = self.prompt(
            "Frequency (e.g., every 2 hours, daily, weekly, monthly)"
        )
        retention_count = int(self.prompt("How many backups to keep", "7"))
        note = self.prompt("Optional note")

        routine = BackupRoutine(
            name=name,
            source_path=source_path,
            s3_prefix=s3_prefix,
            frequency=frequency,
            retention_count=retention_count,
            note=note,
        )
        self.config.routines.append(routine)
        self.save_config()
        print(f"Routine '{name}' added.")

    def list_routines(self) -> None:
        if not self.config.routines:
            print("No routines configured.")
            return

        print("\nConfigured routines:")
        for i, r in enumerate(self.config.routines, start=1):
            print(
                f"{i}) {r.name} | source={r.source_path} | prefix={r.s3_prefix} | "
                f"frequency={r.frequency} | keep={r.retention_count}"
            )

    def run_backup_now(self) -> None:
        if not self.ensure_aws_ready():
            return
        if not self.config.routines:
            print("No routines configured.")
            return

        self.list_routines()
        idx = int(self.prompt("Select routine number")) - 1
        if idx < 0 or idx >= len(self.config.routines):
            print("Invalid routine.")
            return

        routine = self.config.routines[idx]
        source_path = Path(self.prompt_path_anytime("backup source") or routine.source_path)
        if not source_path.exists():
            print("Source path does not exist.")
            return

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        prefix = f"{routine.s3_prefix}/{routine.name}/{stamp}"
        s3 = self.get_s3_client()
        print(f"Starting backup of '{source_path}' to s3://{self.config.bucket_name}/{prefix}")

        uploaded = 0
        if source_path.is_file():
            key = f"{prefix}/{source_path.name}"
            self.upload_file(s3, source_path, key)
            uploaded += 1
        else:
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(source_path)
                    key = f"{prefix}/{rel.as_posix()}"
                    self.upload_file(s3, file_path, key)
                    uploaded += 1

        print(f"Backup completed. Files uploaded: {uploaded}")
        self.apply_retention(s3, routine)

    def restore_backup(self) -> None:
        if not self.ensure_aws_ready():
            return

        s3 = self.get_s3_client()
        prefix = self.prompt("Enter backup prefix to restore (or paste it)")
        target_path = Path(self.prompt_path_anytime("restore destination"))
        target_path.mkdir(parents=True, exist_ok=True)

        try:
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix)
            restored = 0
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue
                    relative = key[len(prefix) :].lstrip("/")
                    local_file = target_path / relative
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    s3.download_file(self.config.bucket_name, key, str(local_file))
                    restored += 1
            print(f"Restore finished. Files restored: {restored}")
        except (BotoCoreError, ClientError) as err:
            print(f"Restore failed: {err}")

    def create_default_strategy(self) -> None:
        print("Creating default strategy:")
        print("- Monthly: keep last 12")
        print("- Weekly: keep last 4")
        print("- Daily every 2 hours: keep previous day (12)")

        source_path = self.prompt_path_anytime("backup source")
        base_prefix = self.prompt("Base S3 prefix", "backups/default")

        templates = [
            ("Monthly", "monthly", "monthly", 12, "Keep last 12 months"),
            ("Weekly", "weekly", "weekly", 4, "Keep last 4 weeks"),
            (
                "Daily_2h",
                "daily-2h",
                "every 2 hours",
                12,
                "Keep previous day with 2-hour snapshots",
            ),
        ]

        for name, folder, freq, keep, note in templates:
            self.config.routines.append(
                BackupRoutine(
                    name=name,
                    source_path=source_path,
                    s3_prefix=f"{base_prefix}/{folder}",
                    frequency=freq,
                    retention_count=keep,
                    note=note,
                )
            )
        self.save_config()
        print("Default strategy routines created.")

    def apply_retention(self, s3, routine: BackupRoutine) -> None:
        base = f"{routine.s3_prefix}/{routine.name}/"
        try:
            response = s3.list_objects_v2(Bucket=self.config.bucket_name, Prefix=base, Delimiter="/")
            prefixes = [p["Prefix"].rstrip("/") for p in response.get("CommonPrefixes", [])]
            prefixes.sort(reverse=True)
            to_delete = prefixes[routine.retention_count :]

            for old_prefix in to_delete:
                self.delete_prefix(s3, old_prefix + "/")
                print(f"Removed old backup: {old_prefix}")
        except (BotoCoreError, ClientError) as err:
            print(f"Retention cleanup warning: {err}")

    def delete_prefix(self, s3, prefix: str) -> None:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix)
        for page in pages:
            objs = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objs:
                s3.delete_objects(Bucket=self.config.bucket_name, Delete={"Objects": objs})

    def upload_file(self, s3, local_file: Path, key: str) -> None:
        try:
            s3.upload_file(str(local_file), self.config.bucket_name, key)
        except (BotoCoreError, ClientError) as err:
            print(f"Upload failed for {local_file}: {err}")

    def get_s3_client(self):
        session = boto3.Session(profile_name=self.config.aws_profile)
        return session.client("s3")

    def ensure_aws_ready(self) -> bool:
        if not self.config.bucket_name:
            print("Please configure AWS first (bucket is missing).")
            return False
        return True

    def load_config(self) -> AppConfig:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return AppConfig.from_dict(json.load(f))
        return AppConfig()

    def save_config(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "aws_profile": self.config.aws_profile,
            "bucket_name": self.config.bucket_name,
            "routines": [asdict(r) for r in self.config.routines],
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)


if __name__ == "__main__":
    try:
        S3BackupApp().run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
