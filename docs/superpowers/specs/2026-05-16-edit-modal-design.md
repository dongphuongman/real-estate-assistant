# Edit Data Source Modal — Design Spec

## Summary

Replace the placeholder `alert()` edit handler in the data-sources admin page with a functional edit modal dialog.

## Approach

Single-form dialog following the existing `DeleteConfirmDialog` component pattern.

## Component: `EditDataSourceDialog`

**Location:** `apps/web/src/components/admin/data-sources/edit-data-source-dialog.tsx`

**Props:**
- `source: DataSource | null` — source to edit (null = closed)
- `isOpen: boolean` — dialog visibility
- `onClose: () => void` — close callback
- `onSave: (id: string, data: DataSourceUpdate) => void` — save callback
- `isSaving?: boolean` — loading state during save

**Editable fields (mapped to `DataSourceUpdate` type):**

| Field | Input Type | Backend field |
|-------|-----------|---------------|
| Name | Text input | `name` |
| Status | Select (pending/active/disabled) | `status` |
| Auto Sync | Toggle/checkbox | `auto_sync_enabled` |
| Sync Schedule | Text input (cron) | `sync_schedule` |
| Config.city | Text input | `config.city` |
| Config.min_price | Number input | `config.min_price` |
| Config.max_price | Number input | `config.max_price` |
| Config.min_rooms | Number input | `config.min_rooms` |
| Config.max_rooms | Number input | `config.max_rooms` |
| Config.property_type | Select | `config.property_type` |
| Config.listing_type | Select | `config.listing_type` |
| Config.limit | Number input | `config.limit` |

Config fields are grouped under a "Filters" section. Only fields present in the source's existing config are shown (config is a dynamic record).

**Behavior:**
- Pre-populate all fields from `source` on open
- Validate required fields (name non-empty)
- Build `DataSourceUpdate` object from changed fields only
- Call `onSave(source.id, data)` on submit
- Close on cancel/backdrop click
- Show loading spinner during save

## Page Integration

In `page.tsx`:
- Add `editSource` / `setEditSource` state (mirrors `deleteSource` pattern)
- Replace placeholder `handleEdit` to set `editSource`
- Add `handleSaveEdit` that calls `updateDataSource` API, then refreshes list
- Render `<EditDataSourceDialog>` alongside existing `<DeleteConfirmDialog>`

## Files Changed

| File | Change |
|------|--------|
| `components/admin/data-sources/edit-data-source-dialog.tsx` | New component |
| `components/admin/data-sources/index.ts` | Add export |
| `app/[locale]/admin/data-sources/page.tsx` | Replace placeholder handler, wire dialog |
