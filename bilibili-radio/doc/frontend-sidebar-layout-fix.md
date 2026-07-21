# Frontend Sidebar Layout Fix

## Problem

The sidebar disappeared after adding the playlist creation modal.

## Root Cause

`Sidebar.vue` became a multi-root component:

- root 1: `<aside class="sidebar">`
- root 2: `<Teleport to="body">`

`AppShell.vue` passes `class="shell-sidebar"` to the `Sidebar` component so it can occupy the CSS grid `sidebar` area. Vue cannot automatically inherit that class for multi-root components, so the real grid item lost `grid-area: sidebar`.

## Fix

- Wrapped the sidebar and Teleport in a single `<div class="sidebar-root">`.
- Kept the modal Teleport behavior unchanged.
- Set `.sidebar-root` and `.sidebar` to fill the grid area.

## Impact

- Sidebar appears in the left grid column again.
- Playlist creation modal still renders at document body level.
