# netbox-to-librenms

Sync devices from NetBox to LibreNMS, treating NetBox as the source of truth.

On each sync cycle the app:

1. Fetches devices from NetBox and LibreNMS
2. Cleans up LibreNMS devices that were previously synced but are no longer valid in NetBox
3. Updates existing synced devices when NetBox details have changed
4. Creates new LibreNMS devices for in-scope NetBox devices that are not yet synced

LibreNMS devices without a `netbox_id` component are left alone. Only devices created or managed by this app are changed.

## Which NetBox devices are synced

A device is synced when all of the following are true:

- Device role is one of: AV Control Button Device (3), AV Control Media Device (4), Projector (6), or TV (11)
- Device has a primary IP address
- Device status is `active`

NetBox configuration context must include `snmp-version` for each device. Currently only `disabled` (ping-only, no SNMP) is supported for new device creation.

## Sync tracking

When a device is created in LibreNMS, this app adds a `netbox_id` component and stores the NetBox device ID in its label. That marker is used on later syncs to match LibreNMS devices back to NetBox records.

## Cleanup behaviour

For LibreNMS devices with a `netbox_id` component:

| NetBox state | LibreNMS action |
| --- | --- |
| Device deleted | Delete from LibreNMS |
| No longer in sync scope (wrong role or no primary IP) | Delete from LibreNMS |
| Status not `active` | Disable in LibreNMS |

## Updates

For active synced devices, the app can update:

- Disabled/enabled status
- Hostname (NetBox name + `DOMAIN_NAME`)
- Hardware (manufacturer and model)

## Installation

Clone this repository and create a `.env` file:

```shell
# Timezone
TZ=Australia/Sydney

# How often to sync the two systems, in seconds
SYNC_FREQUENCY=3600

# NetBox API URL
NETBOX_URL=https://netbox.example.edu.au/api

# NetBox API token
NETBOX_API_TOKEN=your-netbox-api-token

# LibreNMS API URL
LIBRENMS_URL=https://librenms.example.edu.au/api/v0

# LibreNMS API token
LIBRENMS_API_TOKEN=your-librenms-api-token

# Domain name appended to device hostnames
DOMAIN_NAME=example.edu.au

# Log level (DEBUG for more detail)
LOGURU_LEVEL=INFO
```

### Docker Compose

Pull and run the published image:

```shell
docker compose pull
docker compose up -d
```

### Local development

Uncomment the build service in `compose.yml`, or run directly:

```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/app.py
```

## API permissions

- **NetBox**: read access to devices
- **LibreNMS**: read/write access to devices and device components
