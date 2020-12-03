import os
import sys
import inspect
import json

from shared.cache import Cache

class Credentials (Cache):
	FILENAME_TEMPLATE = "{product}_credentials.yaml"

	def __init__(self, product_name:str, max_login_fails:int = 2, **kwds) -> None:
		"""Initialize the Credentials for the application

		Args:
			product_name (str): Name of the product. Used to build the filename
			max_login_fails (int, optional): Max number of failures allowed for the credentials. Defaults to 2.
		"""
		file_name = self.FILENAME_TEMPLATE.format(product=product_name.lower())
		self.max_login_fails = max_login_fails if isinstance(max_login_fails, int) else 2

		super().__init__(file_name, **kwds)

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
		USERNAME = self.__single_input_cred("Inserisci lo USERNAME di Maximo: ")
		PASSWORD = self.__single_input_cred("Inserisci la PASSWORD di Maximo: ")

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






def getCredentials ():	
	"""
	Gets the credentials from a local json

	Returns:
		tuple: contains USERNAME and PASSWORD
	"""

	FILE_BASENAME = "maximo_credentials.json"
	HOME_DIR = os.path.expanduser("~")
	CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
	CREDENTIALS_FILE = os.path.join(HOME_DIR, FILE_BASENAME)

	data = {}

	# Se il file di configurazione esiste usa quello
	if os.path.exists(CREDENTIALS_FILE):
		print(f"Carico le credenziali dal file '{FILE_BASENAME}'", )

		with open(CREDENTIALS_FILE) as f:
			data = json.load(f)
	
	else:
		# Altrimenti chiedi all'utente di inserire i dati necessari e crea il file di configurazione
		print(f"File di configurazione '{FILE_BASENAME}' non trovato.\n")

		USERNAME = input("Inserisci lo USERNAME di Maximo: ")
		PASSWORD = input("Inserisci la PASSWORD di Maximo: ")

		data = { "USERNAME": USERNAME, "PASSWORD": PASSWORD }


		with open(CREDENTIALS_FILE, 'w') as outfile:
			outfile.write(json.dumps(data, indent=4))
		
		print(f"Ho salvato le credenziali nel file '{FILE_BASENAME}'", )


	return (data["USERNAME"], data["PASSWORD"])


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
