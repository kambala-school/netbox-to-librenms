# netbox-to-librenms
Sync devices from NetBox to LibreNMS, treating NetBox as the source of truth

### Installation
Clone this repository and configure the following environment variables in a .env file:
```shell
# Timezone
TZ = 'Australia/Sydney'
# How often to sync the two systems, in seconds
SYNC_FREQUENCY = '3600'
# Netbox API URL
NETBOX_URL = 'https://netbox.dev/api'
# Netbox API Token
NETBOX_API_TOKEN = '39083hpiubp0927hf08163gr1873gr'
# LibreNMS API URL
LIBRENMS_URL = 'https://librenms.dev/api/v0'
# LibreNMS API Token
LIBRENMS_API_TOKEN = '98w9w7eb1g79wifuwbeuo69f69137rv'
# Domain name to append to device hostnames
DOMAIN_NAME = 'kambala.nsw.edu.au'
# Log level. DEBUG will give you more info.
LOGURU_LEVEL = 'INFO'
```

Build and run the container locally or use docker-compose:
```shell
docker-compose pull
docker-compose up -d
```