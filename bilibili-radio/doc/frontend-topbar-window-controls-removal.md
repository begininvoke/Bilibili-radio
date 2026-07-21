# Frontend Topbar Window Controls Removal

## Change

- Removed the decorative yellow/green/red macOS-style window control dots from the top-right app bar.
- Removed the unused `.win-buttons` and `.win-dot` styles from `TopBar.vue`.

## Reason

The app already runs inside a browser or desktop shell that owns real window controls. Keeping decorative controls in the app chrome creates a false affordance because the dots do not minimize, maximize, or close the window.

## Impact

- Topbar actions now end at the login/profile button.
- No routing, player, auth, or library behavior changed.
