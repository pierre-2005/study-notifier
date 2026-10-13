# MLO Studio v3.3.0 release notes

## Implemented

- Restore the v3.1 **blue greeting artwork**, refined into the v3.2 boxed dashboard.
- Restore dynamic theme colors across the boxed UI, no forced mint/green colors. Existing v3.1 palette/theme/settings controls are retained.
- Fix browser drag handles: desktop HTML drag, keyboard arrow, editor up/down buttons for touch.
- Reconcile saved order with visible order by disabling CSS dense grid packing.
- Save layout as **per-user** order, hidden sections, custom sidebar labels and now card widths (4/6/8/12-column options), with automatic safe schema upgrade.
- Layout save feedback with debounced, sequential writes and error reporting.
- Quick-add a task into Today and update task count locally instead of waiting for refresh; inline completion also updates counters.
- More consistent buttons, touch targets, borders, hover/press feedback, dark/independent/full palette surfaces and mobile toolbars.
- Retain consolidated v3.1 modules and v3.2 calendar account connectors, project cascade deletion and permission boundaries.
- Update the GHCR workflow and Compose image to `ghcr.io/pierre-2005/study-notifier:v3.3-polished`.

## Deliberate constraints

- Dashboard edits are **ordered and width-adjustable cards**, not arbitrary overlapping free-position canvas elements. This is intentional for responsive and accessible layouts.
- Mobile resizing collapses to one column. Use editor arrows on mobile rather than desktop drag.
- Standard route navigation remains server-rendered; common task interactions are asynchronous. There is no claim that every action works without a full-page navigation.
- Existing project and calendar capabilities are preserved. Google/Microsoft OAuth depends on the external credentials and provider-side configuration; Apple calendar subscription is read-only.
- No live Raspberry Pi, GitHub Actions or Portainer deployment was executed here; no objective real-device speedup can be claimed without benchmarking your environment.
- The older v2 data format remains an unverified direct migration source.

## Upgrade notes

Version 3.3 extends the existing `life_layouts` table with a `widget_sizes` JSON column. Existing saved v3.2 layouts retain their orders and hidden flags. No projects, finance records or tasks are deleted by this layout migration.
