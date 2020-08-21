import sys
import os
import urllib.parse
import requests
import re

def getCorrectPath(filePath):
	if hasattr(sys, "_MEIPASS"):
		# if getattr(sys, 'frozen', False):
		file = os.path.join(sys._MEIPASS, filePath)
	else:
		file = filePath

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



def checkUpdated(fileName):
	fileName = os.path.splitext(fileName)[0]
	
	if not os.path.exists(getCorrectPath(f"{fileName}.version")):
		raise FileNotFoundError(f"File '{fileName}'.version not exists")
	
	current_vers_fd = open(getCorrectPath(f"{fileName}.version"), "r")
	current_vers = current_vers_fd.readline()

	url = f"https://raw.githubusercontent.com/LukeSavefrogs/ICTSM-Maximo-Automation/master/dist/{urllib.parse.quote(os.path.splitext(os.path.basename(fileName))[0])}.version"
	url_download = f"https://github.com/LukeSavefrogs/ICTSM-Maximo-Automation/blob/master/dist/{urllib.parse.quote(os.path.splitext(os.path.basename(fileName))[0])}.exe?raw=true"

	comp_vers = (requests.get(url)).text
	diff = compare_versions(current_vers, comp_vers)

	# print(current_vers, comp_vers, diff)

	if diff < 0:
		print("-----------------------------------")
		print("ATTENZIONE:")
		print(f"\tE' presente una nuova versione ({comp_vers}, attuale: {current_vers}).")
		print(f"\tPer scaricarla vai al seguente link: {url_download}")
		print("-----------------------------------")

		sys.exit()


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

