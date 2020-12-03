import os
from datetime import datetime
import time

import json
import yaml

from packaging.version import Version, LegacyVersion, InvalidVersion

HOME = os.path.expanduser("~")

def merge_dicts(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result
	
class Cache(object):
	__FILE_BASENAME = ""
	__MIN_SECONDS_BEFORE_UPDATE = 604800	# 7 days
	__API_VERSION = "0.0.0"

	def __init__(self, fileName:str, apiVersion:str = None, maximumTime:int = None) -> None:
		"""Initialize the Cache class

		Args:
			fileName (str): The name to give to the file
			apiVersion (str, optional): The current version of the app. If specified it will be checked any time you get the cache to ensure it is always updated. Defaults to None.
			maximumTime (int, optional): Maximum time expressed in seconds after which the configuration will be marked as expired. Defaults to None.
		"""
		if not fileName: 
			raise AttributeError("Required 'filename' is missing")

		self.__FILE_BASENAME = fileName
		self.__API_VERSION = apiVersion
		self.__MIN_SECONDS_BEFORE_UPDATE = None if maximumTime is not None and int(maximumTime) <= 0 else maximumTime


	def getCacheFilename(self) -> str:
		"""Returns the correct path of the Cache file

		Returns:
			str: The path to the Cache file
		"""
		return os.path.join(HOME, self.__FILE_BASENAME)

	def getRawContent (self) -> dict:
		config = {}

		# Leggo dal file
		with open(self.getCacheFilename(), 'r') as stream:
			config = yaml.safe_load(stream)
		
		return config
		
	def getCache(self, check_expired = True) -> dict:
		"""Retrieves the data saved into the file and checks if data is valid

		Args:
			check_expired (bool, optional): Whether to check if the data has expired (version too old or has passed too much time). Defaults to True.

		Returns:
			dict: Configuration
		"""
		if not self.exists(): 
			return None
		
		config = self.getRawContent()

		if not self.isValid(config):
			return None

		if check_expired and self.hasExpired(config):
			return None


		return config
		

	def setCache(self, data: dict, metadata: dict = {}) -> dict:
		"""Writes the configuration to file, so that it can easily be retrieved

		Args:
			data (dict): The data to be saved
			metadata (dict): The data to be added to the metadata section (Keys not allowed: `timestamp`/`version`)
		"""

		payload = {
			"metadata": {
				"timestamp": int(datetime.now().timestamp()),
				"version": "0.0.0" if self.__API_VERSION is None else self.__API_VERSION
			},
			"data": data
		}

		# This are created automatically, and thus they shouldn't be passed
		metadata.pop('timestamp', None)
		metadata.pop('version', None)

		payload["metadata"] = merge_dicts(payload["metadata"], metadata)

		# Actually write to disk
		with open(self.getCacheFilename(), 'w') as outfile:
			yaml.dump(payload, outfile, default_flow_style=False, explicit_start=True, explicit_end=True, indent=4)
		
		return payload


	def isValid(self, config: dict) -> bool:
		"""Shorthand for:
		- `isHeaderValid(config)`: Check if Header is well formed
		- `isPayloadValid(config)`: Check if Payload is well formed

		Args:
			config (dict): The whole configuration dictionary

		Returns:
			boolean: If valid
		"""
		return self.isHeaderValid(config) and self.isPayloadValid(config)


	def hasExpired(self, config: dict) -> bool:
		"""
		Controlla se:
			- Se è specificata un numero minimo di secondi prima di eseguire l'update, controlla che sia aggiornato
			- Contiene i dati aggiornati nell'Header (non è vecchio e ha la versione corretta)
		"""
		try:
			# Se i dati sono troppo vecchi...
			DATE_TOO_OLD = self.__MIN_SECONDS_BEFORE_UPDATE is not None and (int(datetime.now().timestamp()) - config['metadata']['timestamp']) >= self.__MIN_SECONDS_BEFORE_UPDATE
			
			# Se i dati sono inerenti ad una versione vecchia...
			IS_OLD_VERSION = self.__API_VERSION is not None and Version(self.__API_VERSION) > Version(config['metadata']['version'])
			
			return DATE_TOO_OLD or IS_OLD_VERSION
		except (KeyError, InvalidVersion):
			return True
		except: 
			return True


	def isHeaderValid(self, config: dict) -> bool:
		"""Checks whether the configuration header is well formed

		Args:
			config (dict): The whole configuration dict

		Returns:
			bool: Whether is valid
		"""
		return "metadata" in config and "timestamp" in config["metadata"]


	def isPayloadValid(self, config: dict) -> bool:
		"""Checks whether the configuration payload is well formed

		Args:
			config (dict): The whole configuration dict (NEEDS TO CONTAIN the "data" key)

		Returns:
			bool: Whether is valid
		"""
		return "data" in config


	def exists(self) -> bool:
		"""
		Controlla se esiste già il file usato come "Cache"
		"""
		# Controlla se esiste già il file usato come "Cache"
		if os.path.exists(self.getCacheFilename()):
			with open(self.getCacheFilename(), 'r') as stream:
				config = yaml.safe_load(stream)
			
			return self.isPayloadValid(config)

		return False