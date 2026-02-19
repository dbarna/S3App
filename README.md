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
# S3App

## Review notes for requested menu behavior

I reviewed the repository and there is currently no application source code committed yet (only this README).

To facilitate your request once the menu code is available, implement the following behavior:

### 1) ESC should navigate back in menus

- Add a global key handler for `Escape` in the menu/screen container.
- When pressed:
  - If a submenu is open, close it and focus the parent menu item.
  - Else if there is navigation history, pop one level (`goBack`).
  - Else do nothing.
- Do **not** trigger browser/page-level side effects while typing in text fields.

### 2) "Hot edit" backup routine flow

If by "hot edit" you mean quick-editing a backup routine from the current menu:

- Define a keyboard shortcut (for example `E`) while a backup routine row is focused.
- Open edit mode in place without requiring full navigation.
- Save with `Enter`, cancel with `Escape` (which should return to the previous menu context).

### Suggested implementation pattern

- Keep a stack-based menu state: `menuStack: MenuState[]`.
- Centralize keyboard behavior in one handler.
- Guard against repeated keydown firing by debouncing/repeat checks.

Pseudo-flow:

```text
onKeyDown(event):
  if target is input/textarea/contenteditable:
    if event.key === 'Escape' and inInlineEdit:
      cancelInlineEdit()
    return

  if event.key === 'Escape':
    if inInlineEdit:
      cancelInlineEdit(); restoreFocus(); return
    if menuStack.length > 1:
      menuStack.pop(); restoreFocus(); return
    return

  if event.key === 'e' and focusedItem.type === 'backupRoutine':
    enterInlineEdit(focusedItem.id)
```

## Next step

Once actual app files are added, I can wire this behavior directly into the real menu/navigation components.
