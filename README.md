# S3 Backup & Restore Terminal App (macOS)

Interactive terminal application (English UI) to create backup and restore routines using AWS S3.

## Features

- Menu-driven navigation for all operations.
- At any point where a path is needed, user can paste the full backup/restore path.
- Configurable backup routines:
  - source path
  - S3 destination prefix
  - frequency
  - retention count (how many versions to keep)
- Backup now and restore by prefix.
- Default strategy generator:
  - Monthly, keep 12
  - Weekly, keep 4
  - Every 2 hours, keep previous day (12 snapshots)

## Requirements

- macOS terminal
- Python 3.9+
- AWS credentials configured locally (`~/.aws/credentials`)
- Python package: `boto3`

## Install

```bash
python3 -m pip install boto3
```

## Run

```bash
python3 app.py
```

## Notes

- Data is saved in `~/.s3_backup_cli/config.json`.
- Retention cleanup runs after a successful backup execution.
