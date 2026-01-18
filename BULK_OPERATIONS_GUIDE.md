# Bulk Operations Guide

## Overview
The admin dashboard now supports **bulk operations** on multiple QuickBooks companies simultaneously. This feature allows you to manage sync settings, enable/disable synchronization, or trigger immediate syncs for multiple companies at once.

## Endpoint
```
POST /api/v1/admin/companies/bulk
```

## Authentication
Requires Bearer token authentication (admin login required)

## Operations Available

### 1. Enable Sync for Multiple Companies
Enable synchronization for all selected companies at once.

**Request:**
```json
{
  "company_ids": ["company_1", "company_2", "company_3"],
  "operation": "sync_enable"
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "company_id": "company_1",
      "success": true,
      "message": "Sync enabled"
    },
    ...
  ]
}
```

### 2. Disable Sync for Multiple Companies
Disable synchronization for selected companies.

**Request:**
```json
{
  "company_ids": ["company_1", "company_2"],
  "operation": "sync_disable"
}
```

### 3. Trigger Immediate Sync
Execute synchronization immediately for all selected companies (real-time sync).

**Request:**
```json
{
  "company_ids": ["company_1", "company_2"],
  "operation": "sync_now"
}
```

**Response:**
```json
{
  "total": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "company_id": "company_1",
      "success": true,
      "message": "Sync completed: 16 rates synced"
    },
    {
      "company_id": "company_2",
      "success": true,
      "message": "Sync completed: 16 rates synced"
    }
  ]
}
```

### 4. Apply Same Settings to Multiple Companies
Update sync settings for all selected companies with the same configuration.

**Request:**
```json
{
  "company_ids": ["company_1", "company_2", "company_3"],
  "operation": "update_settings",
  "settings": {
    "auto_sync_enabled": true,
    "use_custom_schedule": false,
    "schedule_time": "09:00",
    "timezone": "Europe/Tirane",
    "enabled_currencies": ["USD", "EUR", "GBP"],
    "notify_on_sync": true,
    "notification_email": "admin@company.com"
  }
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "company_id": "company_1",
      "success": true,
      "message": "Settings updated"
    },
    ...
  ]
}
```

## Use Case Examples

### Example 1: Enable Real-Time Sync for All Active Companies
Use this when you want all companies to sync exchange rates immediately:

1. Get list of all companies: `GET /api/v1/admin/companies`
2. Extract company IDs from active companies
3. Execute bulk enable: `POST /api/v1/admin/companies/bulk`
   ```json
   {
     "company_ids": ["id1", "id2", "id3", ...],
     "operation": "sync_enable"
   }
   ```
4. Trigger immediate sync: `POST /api/v1/admin/companies/bulk`
   ```json
   {
     "company_ids": ["id1", "id2", "id3", ...],
     "operation": "sync_now"
   }
   ```

### Example 2: Apply Standard Settings to New Companies
When onboarding multiple companies, apply your standard configuration:

```json
{
  "company_ids": ["new_company_1", "new_company_2"],
  "operation": "update_settings",
  "settings": {
    "auto_sync_enabled": true,
    "use_custom_schedule": false,
    "notify_on_sync": true,
    "notification_email": "admin@yourcompany.com"
  }
}
```

### Example 3: Disable Sync During Maintenance
Temporarily disable sync for all companies during maintenance:

```json
{
  "company_ids": ["all", "company", "ids"],
  "operation": "sync_disable"
}
```

## Using in Swagger UI (http://localhost:8000/docs)

1. **Login** to get your Bearer token:
   - POST `/api/v1/admin/login`
   - Use: `admin` / `admin123`

2. **Authorize** in Swagger UI:
   - Click the "Authorize" button (lock icon)
   - Enter: `Bearer <your_access_token>`

3. **Get Company List**:
   - GET `/api/v1/admin/companies`
   - Copy the `company_id` values

4. **Execute Bulk Operation**:
   - POST `/api/v1/admin/companies/bulk`
   - Try it out with the request body examples above

## Settings Fields Reference

When using `update_settings` operation, you can include any of these fields:

- `use_custom_schedule` (bool): Override global schedule
- `schedule_time` (time): Custom sync time (HH:MM format)
- `timezone` (string): Timezone for schedule
- `enabled_currencies` (array): Only sync these currencies
- `exclude_currencies` (array): Exclude these currencies
- `sync_on_create` (bool): Sync immediately when company is added
- `auto_sync_enabled` (bool): Enable automatic scheduled sync
- `notification_email` (string): Email for sync notifications
- `notify_on_sync` (bool): Send notifications on each sync

## Activity Logging

All bulk operations are logged in the admin activity log. View them at:
```
GET /api/v1/admin/logs
```

Filter by action:
- `bulk_sync_enable`
- `bulk_sync_disable`
- `bulk_sync_now`
- `bulk_update_settings`

## Error Handling

If any company fails during bulk operation, the operation continues for other companies. The response will show which succeeded and which failed:

```json
{
  "total": 5,
  "successful": 3,
  "failed": 2,
  "results": [
    {
      "company_id": "bad_id",
      "success": false,
      "message": "Company not found"
    },
    {
      "company_id": "disabled_company",
      "success": false,
      "message": "Sync is disabled for this company"
    },
    ...
  ]
}
```

## Best Practices

1. **Always check company list first** to ensure you have valid company IDs
2. **Test with a small subset** before applying to all companies
3. **Monitor activity logs** to track bulk operation results
4. **Use sync_now sparingly** - it triggers immediate API calls to QuickBooks
5. **Set up notifications** to be alerted when syncs complete or fail

## Next Steps

- Configure global settings: `PATCH /api/v1/admin/settings/global`
- View sync status: `GET /api/v1/sync/status`
- Monitor activity: `GET /api/v1/admin/logs`
