import os, sys
import inspect
import json

import logging

# from deprecated import deprecated

from shared.cache import Cache

logger = logging.getLogger(__name__)

class Credentials (Cache):
	FILENAME_TEMPLATE = "{product}_credentials.yaml"
	PRODUCT_NAME = ""

	def __init__(self, product_name:str, max_login_fails:int = 2, **kwds) -> None:
		"""Initialize the Credentials for the application

		Args:
			product_name (str): Name of the product. Used to build the filename
			max_login_fails (int, optional): Max number of failures allowed for the credentials. Defaults to 2.
		"""
		self.PRODUCT_NAME = product_name

		file_name = self.FILENAME_TEMPLATE.format(product=self.PRODUCT_NAME.lower())
		self.max_login_fails = max_login_fails if isinstance(max_login_fails, int) else 2

		super().__init__(file_name, **kwds)
		logger.info(f"Credential storage initialization completed successfully for product '{self.PRODUCT_NAME}' with {self.max_login_fails} MAX login failures")

	def getCredentials(self):
		if not self.exists():
			print(f"File di configurazione '{self.getCacheFilename()}' non trovato.\n")
			self.setCredentials()

		conf = self.getRawContent()

		if not self.isValid(conf):
			print(f"File di configurazione '{self.getCacheFilename()}' non valido.\n")
			self.setCredentials()
			conf = self.getRawContent()

		print(f"File di configurazione '{self.getCacheFilename()}' caricato.\n")

		return conf

	def setCredentials(self):
		USERNAME = self.__single_input_cred(f"Inserisci lo USERNAME di {self.PRODUCT_NAME.strip()}: ")
		PASSWORD = self.__single_input_cred(f"Inserisci la PASSWORD di {self.PRODUCT_NAME.strip()}: ")

		data = {
			"USERNAME": USERNAME, 
			"PASSWORD": PASSWORD,
			"FAILED_LOGINS": 0
		}

		self.setCache(data)

		print(f"\nHo salvato le credenziali nel file '{self.getCacheFilename()}'")

	def isValid(self, config: dict):
			# print("Configurazione: " + str(config))
		
		if not super().isValid(config):
			return False

		# Additional checks
		for key in ["FAILED_LOGINS", "USERNAME", "PASSWORD"]:
			if key not in config["data"]:
				print(f"Chiave necessaria non trovata: {key}")
				return False

		if config["data"]["FAILED_LOGINS"] >= self.max_login_fails:
			print("\n\n------------------------------------------------------------------------------------------")
			print("PASSWORD SCADUTA".center(90))
			print("Cambiare la password e reimmetterla in questo script".center(90))
			print("------------------------------------------------------------------------------------------\n\n")

			return False
	
		return True

	def addFailedLoginAttempt(self):
		config = self.getRawContent()["data"]
		config["FAILED_LOGINS"] += 1

		self.setCache(config)

	def clearFailedLoginAttempts(self):
		config = self.getRawContent()["data"]
		config["FAILED_LOGINS"] = 0

		self.setCache(config)


	# Hidden method
	def __single_input_cred(self, text:str = ""):
		"""Utility method. Used internally to execute checks on user credential input

		Args:
			text (str, optional): The label text to show to the user. Defaults to "".

		Returns:
			str: The value provided by the user
		"""
		while True:
			try:
				value = str(input(text))
			except ValueError:
				print("ERRORE - Valore non valido. Deve essere una stringa\n")
				continue

			if value.strip() == "":
				print("ERRORE - Il valore non puo' essere lasciato vuoto\n")
				continue
			else:
				break

		return value


def getCorrectPath(filePath):
	"""Returns the correct path (relative/absolute) wether is a frozen app or a script 

	Args:
		filePath (str): The path to the resource you need

	Returns:
		str: Final resolved path
	"""
	# Se il percorso specificato è assoluto non fare nulla
	if os.path.isabs(filePath):
		return filePath


	# Se è un'applicazione PyInstaller e il percorso è relativo
	if hasattr(sys, "_MEIPASS"):
		file = os.path.join(sys._MEIPASS, filePath)
	
	# Se è uno script e il percorso è relativo
	else:
		# Scopro il percorso del file chiamante
		frame = inspect.stack()[1]
		caller_filename = frame[0].f_code.co_filename

		# Prendo la cartella parent del file chiamante
		caller_working_directory = os.path.dirname(os.path.realpath(caller_filename))

		# Risolvo i percorsi relativi alla cartella in cui è presente lo script chiamante
		file = os.path.abspath(os.path.join(caller_working_directory, filePath))


		# print(f"Caller: {caller_filename}")
		# print(f"Caller WD: {caller_working_directory}")
		# print(f"Final path: {file}\n")

	return file


# Description:
#	Returns the path of where the script (or executable) is ACTUALLY located.
#	It even works for frozen applications (like executables created with `pyinstaller`)
#
#	I tried `os.path.dirname(os.path.realpath(__file__))` but it returned the correct result only when 
# 		the script was NOT frozen.
#	A different but still working approach would have been `os.path.dirname(os.path.realpath(getEntryPoint()))`,,
#		in which getEntryPoint() checks if script is frozen.
#
# From:
#	https://stackoverflow.com/a/4943474/8965861
#
def get_entry_point():
	"""Returns the name of the script currently running. 
		It works both independent, launched from within a module or from a frozen script (with a 
		tool like pyinstaller)

	Returns:
		str: The absolute path of the script/executable
	"""
	return os.path.realpath(sys.argv[0])

def get_entry_point_dir():
	"""Returns the directory of the script currently running. 
		It works both independent, launched from within a module or from a frozen script (with a 
		tool like pyinstaller)

	Returns:
		str: The absolute path of the directory the script/executable is placed in
	"""
	return os.path.dirname(get_entry_point())


# @deprecated()
def getEntryPoint():
	raise Exception("This function should not be used. Use `get_entry_point()` or `get_entry_point_dir()` instead...")
	
	is_executable = getattr(sys, 'frozen', False)
	
	if is_executable:
		# print("Program is an executable")
		return sys.executable

	# print("Program is a script")
	return inspect.stack()[-1][1]
