import os
import sys
import inspect
import json

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
