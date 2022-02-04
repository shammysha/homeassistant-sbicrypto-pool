from typing import Dict, Optional, List, Tuple

import json
import aiohttp
import asyncio
import hashlib
import hmac
import requests
import time
from operator import itemgetter
from urllib.parse import urlencode
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.const import CONF_API_KEY, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle

__version__ = "1.0.2"

DOMAIN = "sbicrypto_pool"

DEFAULT_NAME = "SBICrypto"
CONF_API_SECRET = "api_secret"
CONF_MINING = "miners"

SCAN_INTERVAL = timedelta(minutes=1)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

DATA_SBICRYPTO = "sbicrypto_pool_cache"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_API_SECRET): cv.string,
                vol.Required(CONF_MINING): vol.All(
                    cv.ensure_list, [cv.string]
                ),                
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    api_key = config[DOMAIN][CONF_API_KEY]
    api_secret = config[DOMAIN][CONF_API_SECRET]
    name = config[DOMAIN].get(CONF_NAME)
    miners = config[DOMAIN].get(CONF_MINING)

    hass.data[DATA_SBICRYPTO] = sbicrypto_data = SBICryptoData(api_key, api_secret, miners)

    if not hasattr(sbicrypto_data, "mining") or "accounts" not in sbicrypto_data.mining:
        pass
    else:
        for account, type in sbicrypto_data.mining["accounts"].items():
            if "workers" in type:
                for worker in type["workers"]:
                    worker["prefix"] = name
                    load_platform(hass, "sensor", DOMAIN, worker, config)
                    
            if "status" in type:
                type["status"]["prefix"] = name
                load_platform(hass, "sensor", DOMAIN, type["status"], config)                                        
    return True


class SBICryptoData:
    def __init__(self, api_key, api_secret, miners = []):
        """Initialize."""
        self.client = SBICryptoPoolClient(api_key, api_secret)
        self.mining = {}

        if miners: 
            self.mining = { "accounts": {} }
            for account in miners:
                self.mining["accounts"] = { account: {} }
                
            self.update()                
        

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug(f"Fetching mining data from pool-api.sbicrypto.com")
        try:        
            if "accounts" in self.mining:
                coins = []
                status = self.client.get_account();
                accounts = status.get("subaccounts", [])
                
                if accounts:
                    workers_list = self.client.get_workers()
                    
                    for account in accounts:
                        accName = account["subaccountName"]
                        accCoin = account["currentMiningCurrency"]["code"].lower()
                        
                        self.mining["accounts"][accName] = {}                                                
                        
                        workers = []
                        status = { 
                            "workerStatus": { 
                                "OFFLINE" : 0, 
                                "DEAD": 0, 
                                "ONLINE": 0, 
                                "UNKNOWN": 0 
                            }, 
                            "numOfWorkers": 0, 
                            "hashrate": [ 0, 0, 0 ],
                            "coin": accCoin,
                            "name": accName
                        }
                        
                        if workers_list:
                            for worker in workers_list:
                                if accName == worker["subaccount"]:
                                    worker["hashrates"] = [ round(hr * 1000000) for hr in worker["hashrates"] ]
                                    worker.pop("coinId", None)
                                    
                                    workers.append(worker)
                                    
                                    if worker["state"] == "":
                                        status["workerStatus"]["UNKNOWN"] += 1
                                    elif worker["state"] == "DEAD":
                                        status["workerStatus"]["DEAD"] += 1
                                    elif worker["state"] == "OFFLINE":
                                        status["workerStatus"]["OFFLINE"] += 1 
                                    elif worker["state"] == "ONLINE":
                                        status["workerStatus"]["ONLINE"] += 1                                         
                               
                                    status["hashrate"][0] += worker["hashrates"][0]
                                    status["hashrate"][1] += worker["hashrates"][1]
                                    status["hashrate"][2] += worker["hashrates"][2]
                                    
                                    status["numOfWorkers"] += 1
                                    
                            if workers:
                                status["hashrate"] = [  round(hr / status["numOfWorkers"]) for hr in status["hashrate"] ]
                                
                                self.mining["accounts"][accName].update({ "workers": workers })
                                _LOGGER.debug(f"Mining workers updated for {accName} from pool-api.sbicrypto.com")
                        
                        self.mining["accounts"][accName].update({ "status": status })
                        _LOGGER.debug(f"Mining status updated for {accName} from pool-api.sbicrypto.com")    
                                      
        except (SBICryptoAPIException, SBICryptoRequestException) as e:
            _LOGGER.error(f"Error fetching mining data from pool-api.sbicrypto.com: {e.message}")
            return False                                       
            
            
class SBICryptoPoolClient():
    API_VERSION = 'v1'
    API_URL = 'https://pool-api.sbicrypto.com/api/external/{}'
    
    REQUEST_TIMEOUT: float = 20    
    
    
    def __init__(
            self, api_key: Optional[str] = None, api_secret: Optional[str] = None, requests_params: Dict[str, str] = None
    ):
        self.API_URL = self.API_URL.format(self.API_VERSION)
        self.API_KEY = api_key
        self.API_SECRET = api_secret
        self.session = self._init_session()        
        self._requests_params = requests_params
        self.response = None
        self.timestamp_offset = 0
         
    
    def _get_headers(self) -> Dict:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',  # noqa
        }
        
        if self.API_SECRET:
            assert self.API_SECRET
            headers['X-API-secret'] = self.API_SECRET  
        
        if self.API_KEY:
            assert self.API_KEY
            headers['X-API-key'] = self.API_KEY
          
        return headers
        
    
    def _init_session(self) -> requests.Session:

        headers = self._get_headers()

        session = requests.session()
        session.headers.update(headers)
        return session         
        

    def _get_request_kwargs(self, method, signed: bool, force_params: bool = False, **kwargs) -> Dict:

        # set default requests timeout
        kwargs['timeout'] = self.REQUEST_TIMEOUT

        # add our global requests params
        if self._requests_params:
            kwargs.update(self._requests_params)

        data = kwargs.get('data', None)
        if data and isinstance(data, dict):
            kwargs['data'] = data

            # find any requests params passed and apply them
            if 'requests_params' in kwargs['data']:
                # merge requests params into kwargs
                kwargs.update(kwargs['data']['requests_params'])
                del(kwargs['data']['requests_params'])

        if signed:
            # generate signature
            kwargs['data']['timestamp'] = int(time.time() * 1000 + self.timestamp_offset)
            kwargs['data']['signature'] = self._generate_signature(kwargs['data'])

        # sort get and post params to match signature order
        if data:
            # sort post params and remove any arguments with values of None
            kwargs['data'] = self._order_params(kwargs['data'])
            # Remove any arguments with values of None.
            null_args = [i for i, (key, value) in enumerate(kwargs['data']) if value is None]
            for i in reversed(null_args):
                del kwargs['data'][i]

        # if get request assign data array to params value for requests lib
        if data and (method == 'get' or force_params):
            kwargs['params'] = '&'.join('%s=%s' % (data[0], data[1]) for data in kwargs['data'])
            del(kwargs['data'])

        return kwargs
                 
    def _request(self, method, uri: str, signed: bool, force_params: bool = False, **kwargs):

        kwargs = self._get_request_kwargs(method, signed, force_params, **kwargs)

        self.response = getattr(self.session, method)(uri, **kwargs)
        return self._handle_response(self.response)


    @staticmethod
    def _handle_response(response: requests.Response):
        """Internal helper for handling API responses from the SBICrypto server.
        Raises the appropriate exceptions when necessary; otherwise, returns the
        response.
        """
        if not (200 <= response.status_code < 300):
            raise SBICryptoAPIException(response, response.status_code, response.text)
        try:
            return response.json()
        except ValueError:
            raise SBICryptoRequestException('Invalid Response: %s' % response.text)


    def _create_api_url(self, path: str ) -> str:
        return self.API_URL + '/' + path

      
    def _request_api(self, method, path, signed=False, **kwargs):
        uri = self._create_api_url(path)
        
        answer = self._request(method, uri, signed, True, **kwargs)
        
        if "content" not in answer:
           return answer   
        
        return answer["content"]


    def get_account(self):
        """ Acquiring Algorithm (MARKET_DATA)
        
            https://sbicrypto-docs.github.io/apidocs/spot/en/#acquiring-algorithm-market_data
            
        """
        return self._request_api('get', 'account')


    def get_workers(self):
        """ Acquiring CoinName (MARKET_DATA)
        
            https://sbicrypto-docs.github.io/apidocs/spot/en/#acquiring-coinname-market_data
        """
        return self._request_api('get', 'workers')        

        
class SBICryptoAPIException(Exception):

    def __init__(self, response, status_code, text):
        self.error = ''
        try:
            _LOGGER.debug(f"SBICryptoAPIException: {response} - {status_code}. {text}")
            json_res = json.loads(text)
        except ValueError:
            self.message = 'Invalid JSON error message from SBICrypto: {}'.format(response.text)
        else:
            self.error = json_res.get("error", "")
            self.description = json_res.get("error_description", "")
            
        self.status_code = status_code
        self.response = response
        self.request = getattr(response, 'request', None)

    def __str__(self):  # pragma: no cover
        return 'APIError(code=%s): %s. %s' % (self.status_code, self.error, self.description)


class SBICryptoRequestException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'SBICryptoRequestException: %s' % self.message