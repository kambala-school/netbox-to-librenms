import requests
import time
import os
from dotenv import load_dotenv
from loguru import logger

# Parameters
load_dotenv()
sync_frequency = int(os.getenv("SYNC_FREQUENCY"))
netbox_url = os.getenv("NETBOX_URL")
netbox_api_token = os.getenv("NETBOX_API_TOKEN")
netbox_headers = {
    "Authorization": f"Token {netbox_api_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}
# move these to env
librenms_url = os.getenv("LIBRENMS_URL")
librenms_api_token = os.getenv("LIBRENMS_API_TOKEN")
librenms_headers = {
    "Authorization": f"Bearer {librenms_api_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}
domain_name = os.getenv("DOMAIN_NAME")

# Functions
def get_netbox_devices(netbox_session):
    """
    Get devices from NetBox
    """
    try:
        url = netbox_url + '/dcim/devices/'
        response = netbox_session.get(url).json()

        # Get the first page of devices
        devices = response["results"]
        logger.info("NetBox device count: {}",response["count"])

        # Get the rest of the devices if paginated
        while(response["next"]):
            logger.debug("NetBox pagination: {}",response["next"])
            response = netbox_session.get(response["next"]).json()
            for device in response["results"]:
                devices.append(device)

        # if response.json()["status"] == "error":
        #   raise Exception(f'Error received from NetBox: {response.json()["message"]}')    
        # if response.json()["detail"] == "Token expired":
        #   raise Exception(f'Error received from NetBox: {response.json()["detail"]}') 
        # if (response.status_code != 200):

        return devices
    except:
        logger.error(f'Failed to get devices from Netbox')

def filter_netbox_devices(netbox_devices):
    """
    Filter and sanitise the NetBox device list to remove devices that won't be synced to LibreNMS.
    """
    filtered_devices = []
    for device in netbox_devices:
        # Ignore devices that aren't part of the specified roles
        #  - move this variable to a env or something that's not hard coded
        #  - id 3 AV Control Button Device
        #  - id 4 AV Control Media Device
        #  - id 11 TV
        #  - id 6 Projector
        device_role_ids = [3, 4, 6, 11]
        for role in device_role_ids:
            if device["role"]["id"] == role:
                
                # Ignore devices with no IP address
                if device.get('primary_ip') is not None:
                    # Remove the netmask that comes from the NetBox IP
                    device["primary_ip"]["address"] = device["primary_ip"]["address"].split('/',1)[0]

                    filtered_devices.append(device)

    return filtered_devices

def get_librenms_devices(librenms_session):
    """
    Get devices from LibreNMS
    """
    try:
        url = librenms_url + '/devices/'
        response = librenms_session.get(url).json()

        # Get the first page of devices
        devices = response['devices']
        logger.info("LibreNMS device count: {}",response['count'])
        for device in devices:
            # Get netbox_id from LibreNMS Components
            # '/devices/:id/components?type=netbox_id'
            component_url = url + str(device['device_id']) + '/components?type=netbox_id'
            response = librenms_session.get(component_url).json()

            # Check if the device has any components
            if response.get('count') is not None:
                # Check if any of the components are of type netbox_id
                for component in response["components"].values():
                    if component["type"] == "netbox_id":
                        # Add the netbox_id to the LibreNMS device dict
                        device["netbox_id"] = component["label"]

        # Do more error checking on original HTTP GET

        return devices
    except:
        logger.error(f'Failed to get devices from LibreNMS')

def compare_device_details(device,netbox_devices,librenms_session):
    """
    Compare details of LibreNMS device to the NetBox source of truth and update if required.
    """
    try:
        logger.debug("Comparing {} with NetBox ID: {}",device['hostname'],device['netbox_id'])
        for netbox_device in netbox_devices:
            if netbox_device['id'] == int(device['netbox_id']):
                # Device found in NetBox, now compare details
                logger.trace(device)
                logger.trace(netbox_device)
                update_required = False
                # Compare status - disabled?
                if (netbox_device['status']['value'] != 'active') and (device['disabled'] != 1):
                    logger.debug("Compare status failed: {} <=> {}", netbox_device['status']['value'],device['disabled'] != 1)
                    update_required = True
                # Compare status - active?
                if (netbox_device['status']['value'] == 'active') and (device['disabled'] == 1):
                    logger.debug("Compare status failed: {} <=> {}", netbox_device['status']['value'],device['disabled'] != 1)
                    update_required = True
                # Compare hostname
                if netbox_device['name'] != device['hostname'].split('.',1)[0]:
                    logger.debug("Compare hostname failed: {} <=> {}", netbox_device['name'],device['hostname'].split('.',1)[0])
                    update_required = True
                # Compare location - requires a location id configured in LibreNMS
                # if netbox_device['location']['name'] != device['location']:
                #     logger.debug("Compare location failed: {} <=> {}", netbox_device['location']['name'], device['location'])
                #     update_required = True
                # Compare hardware
                if (netbox_device['device_type']['manufacturer']['name'] + ' ' + netbox_device['device_type']['model']) != device['hardware']:
                    logger.debug("Compare location failed: {} <=> {}",netbox_device['device_type']['manufacturer']['name'] + ' ' + netbox_device['device_type']['model'],device['hardware'])
                    update_required = True
                # Compare SNMP type using NetBox Configuration Contexts
                if (netbox_device['config_context']['snmp-version'] == 'disabled') and (device['snmp_disable'] != 1):
                    logger.debug("Compare SNMP disabled failed: {} <=> {}",netbox_device['config_context']['snmp-version'],device['snmp_disable'])
                    update_required = True
                if (netbox_device['config_context']['snmp-version'] == 'v2c') and (device['snmpver'] == 'v2c'):
                    logger.debug("Compare SNMP v2c failed: ")
                    update_required = True
                    # Check SNMP community string
                if (netbox_device['config_context']['snmp-version'] == 'v3') and (device['snmpver'] == 'v3'):
                    logger.debug("Compare SNMP v3 failed: ")
                    update_required = True
                    # Check SNMP auth? secrets?

                if update_required:
                    logger.info("Update of {} in LibreNMS is required", device['hostname'])
                    update_device_details(device, netbox_device, librenms_session)

            # else:
            #     logger.error("LibreNMS device not found in NetBox devices")

    except:
        logger.error("Failed to compare LibreNMS device with NetBox")

def update_device_details(device, netbox_device, librenms_session):
    """
    Update details of LibreNMS device from the NetBox source of truth.
    """
    try:
        logger.trace(device)
        logger.trace(netbox_device)
        # Check status - is it active?
        if (netbox_device['status']['value'] != 'active') and (device['disabled'] != 1):
            logger.info("Updating status of LibreNMS device: {}", device['hostname'])
            url = librenms_url + '/devices/' + str(device['device_id'])
            data = '{"field": "disabled", "data": 1}'
            logger.trace(data)
            response = librenms_session.patch(url,data=data)
            # Do some error checking on response
            logger.trace(response)
            logger.trace(response.text)

        # Compare status - active?
        if (netbox_device['status']['value'] == 'active') and (device['disabled'] == 1):
            logger.info("Updating status of LibreNMS device: {}", device['hostname'])
            url = librenms_url + '/devices/' + str(device['device_id'])
            data = '{"field": "disabled", "data": 0}'
            response = librenms_session.patch(url,data=data)
            # Do some error checking on response

        # Check hostname - assumes the NetBox device name is the hostname
        if netbox_device['name'] != device['hostname'].split('.',1)[0]:
            logger.info("Updating hostname of LibreNMS device: {}", device['hostname'])
            url = librenms_url + '/devices/' + str(device['device_id']) + '/rename/' + netbox_device['name'] + '.' + domain_name
            response = librenms_session.patch(url)
            # Do some error checking on response
            logger.trace(response)
            logger.trace(response.text)

        # Check location - requires the location to exist in LibreNMS
        # data = {
        #     "field":"location_id",
        #     "data":"48"
        # }
        # Locations probably have pagination after more than 50 items
        
        # Check hardware
        if (netbox_device['device_type']['manufacturer']['name'] + ' ' + netbox_device['device_type']['model']) != device['hardware']:
            logger.info("Updating hardware of LibreNMS device: {}", device['hostname'])
            url = librenms_url + '/devices/' + str(device['device_id'])
            data = '{"field": "hardware", "data": "%s"}' % (netbox_device['device_type']['manufacturer']['name'] + ' ' + netbox_device['device_type']['model'])
            logger.trace(data)
            response = librenms_session.patch(url,data=data)
            # Do some error checking on response
            logger.trace(response)
            logger.trace(response.text)

        # Check SNMP

    except Exception as err:
        logger.error(f"Failed to update LibreNMS device: {err}")

def create_librenms_device(device, librenms_session):
    """
    Create a LibreNMS device from the NetBox source of truth.
    """
    try:
        logger.info("Create {} in LibreNMS", device['name'])
        hostname = device['name'] + '.' + domain_name
        display = device['display']
        snmp = device['config_context']['snmp-version']
        hardware = device['device_type']['manufacturer']['name'] + ' ' + device['device_type']['model']
        location = device['site']['name']
        if device['location'] is not None:
            location = device['site']['name'] + ' ' + device['location']['name']
        logger.debug("{} {} {} {} {}",hostname,display,location,snmp,hardware)

        # Check SNMP details from NetBox
        data = None
        if device['config_context']['snmp-version'] == 'disabled':
            logger.debug("Creating as ping only, no SNMP")
            data = '{"hostname": "' + hostname + '", "display": "' + display + '", "location": "' + location + '", "force_add":"true", "snmp_disable":"true", "hardware": "' + hardware + '" }'
        # elif: SNMPv2, SNMPv3
        else:
            logger.debug("We need to implement more SNMP checks to add this correctly")

        if data is not None:
            logger.debug(data)
            response = librenms_session.post(librenms_url + '/devices', data=data).json()
            # Do some error checking on response
            logger.debug(response)
            if response['status'] == 'ok':
                # Add a 'netbox_id' component to the new LibreNMS device
                librenms_device_id = response['devices'][0]['device_id']
                url = librenms_url + '/devices/' + str(librenms_device_id) + '/components/netbox_id'
                logger.debug(url)
                response = librenms_session.post(url).json()
                
                # Add the Netbox ID to the new LibreNMS netbox_id component
                logger.debug(response)
                # Do some error checking
                if response['status'] == 'ok':
                    logger.debug('Adding the NetBox ID to the new LibreNMS component')
                    url = librenms_url + '/devices/' + str(librenms_device_id) + '/components'
                    logger.debug(url)
                    component_id = next(iter(response['components']))
                    data = '{ "' + component_id + '": {"type": "netbox_id", "label": "' + str(device['id']) + '", "status": null, "ignore": null, "disabled": null, "error": null } }'
                    logger.debug(data)
                    response = librenms_session.put(url, data=data).json()
                    logger.debug(data)
                    # Perform error checking

    except Exception as err:
        logger.error(f"Failed to create LibreNMS device: {err}")

# Main Function
logger.info("netbox-to-librenms starting")
logger.info(f"Sync frequency: {sync_frequency}")
logger.info(f"NetBox URL: {netbox_url}")

while True:
    try:
        #Create NetBox and LibreNMS sessions and get lists of devices
        netbox_session = requests.Session()
        netbox_session.headers = netbox_headers
        netbox_devices = get_netbox_devices(netbox_session)
        netbox_devices = filter_netbox_devices(netbox_devices)

        librenms_session = requests.Session()
        librenms_session.headers = librenms_headers
        librenms_devices = get_librenms_devices(librenms_session)

        logger.info("Comparing previously synced devices against NetBox source of truth")
        for device in librenms_devices:
            # Check if the LibreNMS device has a netbox_id component (previously synced)
            if device.get('netbox_id') is not None:
                # Compare LibreNMS device details and check if any updates from NetBox are required
                compare_device_details(device,netbox_devices,librenms_session)
            else:
                # Devices have not been synced
                logger.trace("LibreNMS device does not exist in NetBox - Hostname: {}  IP: {} ",device["hostname"],device["ip"])
                # Create new devices in Netbox??

        logger.info("Comparing devices from NetBox to LibreNMS")
        for device in netbox_devices: 

            # Check if there already exists a device in LibreNMS with a matching netbox_id component
            create_device = True
            for librenms_device in librenms_devices:
                if librenms_device.get('netbox_id') is not None:
                    if int(librenms_device.get('netbox_id')) == device['id']:
                        create_device = False
                        # How to delete or disable a device in LibreNMS if it is no longer active in NetBox?
                        break
            if create_device:
                create_librenms_device(device,librenms_session)  
                # TESTING with only one device for now
                # if device['id'] == 32:
                #     create_librenms_device(device,librenms_session)              

    except requests.exceptions.ConnectionError as err:
        # DNS failure, refused connection, etc
        logger.warning(err)
        pass
        
    except requests.exceptions.Timeout as err:
        # Check which number attempt this is
        logger.warning(err)
        pass
    
    except OSError as err:
        logger.warning(err)
        pass
    
    except Exception as err:
        # Other Exceptions
        logger.error(err)
        
    else:
        # Nothing went wrong...
        logger.info("Waiting for the next sync...")

    time.sleep(sync_frequency)  # Pause execution before trying again
