"""
SBICrypto sensor
"""
from datetime import datetime, timezone

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.components.sensor import SensorEntity


ATTRIBUTION = "Data provided by SBICrypto"

ATTR_WORKER_STATUS = "status"
ATTR_WORKER_REJECT = "reject_rate"
ATTR_WORKER_WORKER = "worker_name"
ATTR_WORKER_UPDATE = "updated"

ATTR_STATUS_HRATE10M = "average hashrate (10 mins)"
ATTR_STATUS_HRATE1H = "average hashrate (1 hour)"
ATTR_STATUS_HRATE24H = "average hashrate (24 hours)"
ATTR_STATUS_TOTAL_WORKERS = "count of workers"
ATTR_STATUS_VALID_WORKERS = "valid workers"
ATTR_STATUS_INVALID_WORKERS = "invalid workers"
ATTR_STATUS_INACTIVE_WORKERS = "inactive workers"
ATTR_STATUS_UNKNOWN_WORKERS = "unknown workers"
ATTR_STATUS_TOTAL_ALERTS = "All workers with alerts"

ATTR_ACCOUNT = "account"
ATTR_COIN = "coin"

DATA_SBICRYPTO = "sbicrypto_pool_cache"

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the SBICrypto sensors."""

    if discovery_info is None:
        return
    
    elif all(i in discovery_info for i in ["prefix", "name", "state", "lastShareTime", "subaccountId", "subaccount", "hashrates"):
        prefix = discovery_info["prefix"]
        name = discovery_info["name"]
        state = discovery_info["state"]
        lastShareTime = discovery_info["lastShareTime"]
        subaccountId = discovery_info["subaccountId"]
        subaccount = discovery_info["subaccount"]
        hashrates = discovery_info["hashrates"]

        sensor = SBICryptoWorkerSensor(hass.data[DATA_SBICRYPTO], prefix, name, state, lastShareTime, subaccountId, subaccount, hashrates)

    elif all(i in discovery_info for i in ["prefix", "name", "coin", "workerStatus", "numOfWorkers", "hashrate"]):
        prefix = discovery_info["prefix"]
        name = discovery_info["name"]
        coin = discovery_info["coin"]
        workerStatus = discovery_info["workerStatus"]
        numOfWorkers = discovery_info["numOfWorkers"]
        hashrate = discovery_info["hashrate"]

        sensor = SBICryptoStatusSensor(hass.data[DATA_SBICRYPTO], prefix, name, coin, workerStatus, numOfWorkers, hashrate)
        
    add_entities([sensor], True)

            
class SBICryptoWorkerSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, sbicrypto_data, prefix, name, state, lastShareTime, subaccountId, subaccount, hashrates):
        """Initialize the sensor."""
        self._sbicrypto_data = sbicrypto_data
        self._name = f"{prefix} {account}.{name} worker"
        self._account = subaccount
        self._worker = name
        self._status = state
        self._hrate10m = hashrates[0]
        self._hrate1h = hashrates[1]
        self._hrate24h = hashrates[2]
        self._update = lastShareTime
        self._unit_of_measurement = "H/s"        
        self._state = None
        
        self._status_vars = ["UNKNOWN", "ONLINE", "DEAD", "OFFLINE"]
        self._status_icons = ["mdi:sync-off", "mdi:server-network", "mdi:server-network-off", "mdi:power-plug-off"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""

        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        
        try:
            return self._status_icons[self._status]
        except KeyError as e:
            return self._status_icons[0]

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        data = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_STATUS_HRATE10M: f"{self._hrate10m}",
            ATTR_STATUS_HRATE1H: f"{self._hrate1h}",            
            ATTR_STATUS_HRATE24H: f"{self._hrate24h}",
            ATTR_WORKER_WORKER: f"{self._worker}",
            ATTR_WORKER_UPDATE: datetime.fromisoformat(self._update),
            ATTR_ACCOUNT: f"{self._account}"
        }
        
        try:
            data[ATTR_WORKER_STATUS] = self._status_vars[self._status]
        except KeyError as e:
            data[ATTR_WORKER_STATUS] = "unknown"
        
        return data
        
        
    def update(self):
        """Update current values."""
        self._sbicrypto_data.update()

        exists = False
                
        for account, type in self._sbicrypto_data.mining["accounts"].items():
            if account != self._account:
                continue
                
            if "workers" not in type:
                continue
                
            for worker in type["workers"]:
                if worker["name"] != self._worker:
                    continue
                
                exists = True
                    
                self._account = worker["subaccount"]
                self._worker = worker["name"]
                self._status = worker["state"]
                self._hrate10m = worker["hashrates"][0]
                self._hrate1h = worker["hashrates"][1]
                self._hrate24h = worker["hashrates"][2]                    

                self._state = self._hrate10m

                break                
            
            if exists:
                break
                            
        if not exists:
            self._state = None 
            
class SBICryptoStatusSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, sbicrypto_data, prefix, name, coin, workerStatus, numOfWorkers, hashrate):
        """Initialize the sensor."""
        self._sbicrypto_data = sbicrypto_data
        self._name = f"{prefix} {account} status"
        self._account = name
        self._coin = coin
        self._hrate10m = hashrate[0]
        self._hrate1h = hashrate[1]
        self._hrate24h = hashrate[2]
        self._total_workers = numOfWorkers
        self._valid_workers = workerStatus["ONLINE"]
        self._unknown_workers = workerStatus["UNKNOWN"]
        self._invalid_workers = workerStatus["DEAD"]
        self._inactive_workers = workerStatus["OFFLINE"]
        self._total_alerts = self._unknown_workers + self._invalid_workers + self._inactive_workers
        self._unit_of_measurement = "H/s"        
        self._state = None
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""

        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return f"mdi:currency-{self._coin}' . 

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_STATUS_HRATE10M: f"{self._hrate10m}",
            ATTR_STATUS_HRATE1H: f"{self._hrate1h}",            
            ATTR_STATUS_HRATE24H: f"{self._hrate24h}",
            ATTR_STATUS_TOTAL_WORKERS: f"{self._total_workers}",
            ATTR_STATUS_VALID_WORKERS: f"{self._valid_workers}",
            ATTR_STATUS_TOTAL_ALERTS: f"{self._total_alerts}",    
            ATTR_STATUS_UNKNOWN_WORKERS: f"{self._unknown_workers}",
            ATTR_STATUS_INVALID_WORKERS: f"{self._invalid_workers}",
            ATTR_STATUS_INACTIVE_WORKERS: f"{self._inactive_workers}",
            ATTR_ACCOUNT: f"{self._account}",
            ATTR_COIN: f"{self._coin}".upper(),
        }
        
        
    def update(self):
        """Update current values."""
        self._sbicrypto_data.update()

        exists = False

        for account, type in self._sbicrypto_data.mining["accounts"].items():
            if account != self._account:
                continue
                
            if "status" not in type:
                continue

            exists = True
            
            self._coin = type["status"]["coin"]
            self._hrate10m = type["status"]["hashrate"][0]
            self._hrate1h = type["status"]["hashrate"][1]
            self._hrate24h = type["status"]["hashrate"][2]
            self._total_workers = type["status"]["numOfWorkers"]
            self._valid_workers = type["status"]["workerStatus"]["ONLINE"]
            self._unknown_workers = type["status"]["workerStatus"]["UNKNOWN"]
            self._invalid_workers = type["status"]["workerStatus"]["DEAD"]
            self._inactive_workers = type["status"]["workerStatus"]["OFFLINE"]
            self._total_alerts = self._unknown_workers + self._invalid_workers + self._inactive_workers
            
            self._state = self._hrate10m
            
            break
                
        if not exists:
            self._state = 0
            
