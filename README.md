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
