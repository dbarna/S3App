# S3App

## Review: S3 bucket existence handling and daemonized backup routine

This review focuses on two product behaviors:

1. **Do not quit the application if the S3 bucket does not exist**.
2. **Provide an option to run backup routines continuously as a daemon**.

---

### 1) Graceful handling when bucket does not exist

Current desired behavior:

- If the configured bucket is missing, the application should **stay running**.
- The application should return a clear status and provide a direct URL so the user can create the bucket.

Recommended behavior:

- At startup, validate bucket existence using `HeadBucket`.
- If the bucket exists, continue normal processing.
- If the bucket does not exist:
  - Keep process alive.
  - Mark health state as `degraded` (not `down`).
  - Return a message with the create URL and region hint.
  - Retry validation on a configurable interval.

Create-bucket URL pattern:

```text
https://s3.console.aws.amazon.com/s3/bucket/create?region=<AWS_REGION>
```

User-facing message example:

```text
Configured bucket "<BUCKET_NAME>" was not found in region "<AWS_REGION>".
The application will keep running and retry every 60s.
Create bucket: https://s3.console.aws.amazon.com/s3/bucket/create?region=<AWS_REGION>
```

Operational notes:

- Treat only `NotFound` / `NoSuchBucket` as recoverable missing-resource states.
- For credential/network errors, also keep process alive but return a distinct `error` state.
- Add metrics:
  - `bucket_check_total`
  - `bucket_missing_total`
  - `bucket_available` (gauge)

---

### 2) Option to run backup routine as a daemon

Current desired behavior:

- Backups should be reviewable and optionally run continuously in the background.

Recommended interface:

- Add execution mode option:
  - `--backup-mode=once` (single run)
  - `--backup-mode=daemon` (continuous schedule loop)
- Add scheduling option:
  - `--backup-interval=60s` (or cron expression if needed)

Daemon loop expectations:

- Process starts and logs selected mode.
- In daemon mode:
  - Perform preflight checks.
  - Run backup.
  - Persist result (success/failure, timestamp, size, duration).
  - Sleep until next interval.
  - Continue after non-fatal errors.

Review visibility:

- Add a local/state file or endpoint for latest runs:
  - `last_run_at`
  - `last_status`
  - `last_error`
  - `objects_uploaded`
  - `bytes_uploaded`
- Keep a rolling history (for example, last 50 runs).

Reliability recommendations:

- Add jitter to interval to avoid thundering herd.
- Add lockfile or distributed lock to prevent overlapping runs.
- Add max runtime guard so stuck jobs are marked failed.
- Expose `SIGTERM` handling for graceful shutdown.

---

## Proposed acceptance criteria

- Missing bucket no longer exits process.
- Missing bucket response includes AWS create-bucket URL.
- Backup routine supports both one-shot and daemon modes.
- Daemon mode continues after recoverable failures.
- Run history is available for operator review.

## Suggested next implementation step

Implement a `BucketStatusService` and `BackupScheduler` abstraction so bucket validation and daemonized backup orchestration are testable independently from CLI and transport layers.
