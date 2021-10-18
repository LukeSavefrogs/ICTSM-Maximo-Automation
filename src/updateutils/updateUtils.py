import sys
import os
import urllib.parse
import requests
import re
import inspect
from urllib3.exceptions import InsecureRequestWarning

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



def compare_versions(vA, vB):
	"""
		Compares two version number strings
		@param vA: first version string to compare
		@param vB: second version string to compare
		@author <a href="http_stream://sebthom.de/136-comparing-version-numbers-in-jython-pytho/">Sebastian Thomschke</a>
		@return negative if vA < vB, zero if vA == vB, positive if vA > vB.
	"""
	def cmp(a, b):
		return (a > b) - (a < b) 

	def num(s):
		if s.isdigit(): return int(s)
		return s

	if vA == vB: return 0


	seqA = list(map(num, re.findall('\d+|\w+', vA.replace('-SNAPSHOT', ''))))
	seqB = list(map(num, re.findall('\d+|\w+', vB.replace('-SNAPSHOT', ''))))

	# this is to ensure that 1.0 == 1.0.0 in cmp(..)
	lenA, lenB = len(seqA), len(seqB)
	for i in range(lenA, lenB): seqA += (0,)
	for i in range(lenB, lenA): seqB += (0,)

	rc = cmp(seqA, seqB)

	if rc == 0:
		if vA.endswith('-SNAPSHOT'): return -1
		if vB.endswith('-SNAPSHOT'): return 1
	return rc


def uri_exists_stream(uri: str) -> bool:
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    try:
        with requests.head(uri, stream=True, allow_redirects=True, headers=headers, verify=False) as response:
            try:
                response.raise_for_status()
                return True
            except requests.exceptions.HTTPError:
                return False
    except requests.exceptions.ConnectionError:
        return False



def checkUpdated(fileName):
	fileName_noExt = os.path.splitext(fileName)[0]


	script_name = urllib.parse.quote(os.path.splitext(os.path.basename(fileName_noExt))[0])
	
	url = f"https://raw.githubusercontent.com/LukeSavefrogs/ICTSM-Maximo-Automation/master/dist/{script_name}.version"
	url_download = f"https://github.com/LukeSavefrogs/ICTSM-Maximo-Automation/blob/master/dist/{script_name}.exe?raw=true"

	print(f"Comparing {fileName_noExt} against:")
	print(f"- Local: {getCorrectPath(f'{fileName_noExt}.version')}")
	print(f"- Remote: {url}")

	if not os.path.exists(getCorrectPath(f"{fileName_noExt}.version")):
		print("\n\n")
		print("ERRORE CRITICO:")
		print(f"Il file LOCALE '{fileName_noExt}.version' non esiste.")
		print(f"Contattare lo sviluppatore (Caller: {fileName})\n\n")
		print("\n\n")

		sys.exit(23)
	elif not uri_exists_stream(url):
		print("\n\n")
		print("ERRORE CRITICO:")
		print(f"Il file REMOTO '{url}' non esiste.")
		print(f"Contattare lo sviluppatore (Caller: {fileName})")
		print("\n\n")
		
		sys.exit(23)
	

	current_vers_fd = open(getCorrectPath(f"{fileName_noExt}.version"), "r")
	current_vers = current_vers_fd.readline()

	comp_vers = (requests.get(url)).text
	diff = compare_versions(current_vers, comp_vers)

	# print(f"Remote version: {comp_vers}")
	if diff < 0:
		print("-----------------------------------")
		print("ATTENZIONE:")
		print(f"\tE' presente una nuova versione ({comp_vers}, attuale: {current_vers}).")
		print(f"\tPer scaricarla vai al seguente link: {url_download}")
		print("-----------------------------------")
		print()

		input("Premi un tasto per terminare")

		sys.exit()

	print(f"-------------- Versione script: {current_vers} --------------\n")


def checkVersions (fileName):
	try:
		source_vers_filename = f"./src/{fileName}.version"
		if not os.path.exists(source_vers_filename):
			open(source_vers_filename, 'w').close()

		source_vers_fd = open(source_vers_filename, "r")

		compil_vers_filename = f"./dist/{fileName}.version"
		if not os.path.exists(compil_vers_filename):
			open(compil_vers_filename, 'w').close()

		compil_vers_fd = open(compil_vers_filename, "r")



		source_vers = source_vers_fd.readline()

		if source_vers == "":
			logging.error(f"ATTENZIONE: Versione non impostata nel file '{source_vers}'. Impostarla e riprovare...")
			
			return False

		compil_vers = compil_vers_fd.readline()
		rc = compare_versions(source_vers, compil_vers)

		if rc == 0:
			logging.error(f"ATTENZIONE: Versioni uguali. Se è stato modificato qualcosa, cambiare la versione corrente ({source_vers}) nel file '{source_vers_filename}' e riprovare...")

			return False

		elif rc < 0:
			logging.error(f"ATTENZIONE: La versione del file sorgente è MINORE di quella del file compilato...")
			logging.error(f"Source	: {source_vers}")
			logging.error(f"Compiled: {compil_vers}")

			return False
		
		return True
	except Exception as e:
		logging.exception(e)
		
	finally:
		source_vers_fd.close()
		compil_vers_fd.close()

