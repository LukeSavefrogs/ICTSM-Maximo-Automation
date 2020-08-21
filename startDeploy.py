import subprocess
import re
import os
import logging
import sys

# ---------------------------------------------------------------------------------

def checkVersions (fileName):
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



def updateVersions (fileName):
	if not checkVersions (fileName): 
		return;

	source_vers_filename = f"./src/{fileName}.version"
	compil_vers_filename = f"./dist/{fileName}.version"

	source_vers_fd = open(source_vers_filename,"r")
	compil_vers_fd = open(compil_vers_filename,"w+")

	source_vers = source_vers_fd.readline().strip()
	compil_vers_fd.write(source_vers)

	if not checkVersions (fileName):
		logging.error(f"ERRORE - NON e' stato possibile aggiornare la versione dello script compilato alla {source_vers}:")
		
		return False
		
	logging.info(f"SUCCESSO - Versione script compilato aggiornata alla {source_vers}")

	return True

# ---------------------------------------------------------------------------------

def compileScript(fileName):
	logging.info(f"Inizio compilazione del file: {fileName}")

	if checkVersions (fileName): 
		command = [
			"pyinstaller",
			"--noconfirm",
			"--log-level=WARN",
			"--onefile",
			# "--debug=all",
			"--specpath=./build_spec",
			f"--add-data=../src/{fileName}.version;.",
			f"./src/{fileName}.py"
		]

		output = subprocess.run(command, capture_output=True)
		
		if output.returncode == 0:
			logging.info(f"SUCCESSO - Script '{fileName}' compilato correttamente")

			updateVersions(fileName)
			
		else:
			logging.error(f"ATTENZIONE: Errore durante la compilazione dello script '{fileName}'\n")
			logging.error(f"Return Code: {output.returncode}")
			logging.error(f"StdErr stream: {output.stderr.decode('cp1252')}")

	logging.info(f"Fine compilazione del file: {fileName}")
	print()



if __name__ == "__main__":
	logging.getLogger(__name__)
	logging.basicConfig(level=logging.INFO, format="[%(asctime)s] - %(levelname)s - %(message)s")

	print(
		"""
        CCCCCCCCCCCCC                                                               iiii  lllllll   iiii                                       
     CCC::::::::::::C                                                              i::::i l:::::l  i::::i                                      
   CC:::::::::::::::C                                                               iiii  l:::::l   iiii                                       
  C:::::CCCCCCCC::::C                                                                     l:::::l                                              
 C:::::C       CCCCCC   ooooooooooo      mmmmmmm    mmmmmmm   ppppp   ppppppppp   iiiiiii  l::::l iiiiiiinnnn  nnnnnnnn       ggggggggg   ggggg
C:::::C               oo:::::::::::oo  mm:::::::m  m:::::::mm p::::ppp:::::::::p  i:::::i  l::::l i:::::in:::nn::::::::nn    g:::::::::ggg::::g
C:::::C              o:::::::::::::::om::::::::::mm::::::::::mp:::::::::::::::::p  i::::i  l::::l  i::::in::::::::::::::nn  g:::::::::::::::::g
C:::::C              o:::::ooooo:::::om::::::::::::::::::::::mpp::::::ppppp::::::p i::::i  l::::l  i::::inn:::::::::::::::ng::::::ggggg::::::gg
C:::::C              o::::o     o::::om:::::mmm::::::mmm:::::m p:::::p     p:::::p i::::i  l::::l  i::::i  n:::::nnnn:::::ng:::::g     g:::::g 
C:::::C              o::::o     o::::om::::m   m::::m   m::::m p:::::p     p:::::p i::::i  l::::l  i::::i  n::::n    n::::ng:::::g     g:::::g 
C:::::C              o::::o     o::::om::::m   m::::m   m::::m p:::::p     p:::::p i::::i  l::::l  i::::i  n::::n    n::::ng:::::g     g:::::g 
 C:::::C       CCCCCCo::::o     o::::om::::m   m::::m   m::::m p:::::p    p::::::p i::::i  l::::l  i::::i  n::::n    n::::ng::::::g    g:::::g 
  C:::::CCCCCCCC::::Co:::::ooooo:::::om::::m   m::::m   m::::m p:::::ppppp:::::::pi::::::il::::::li::::::i n::::n    n::::ng:::::::ggggg:::::g 
   CC:::::::::::::::Co:::::::::::::::om::::m   m::::m   m::::m p::::::::::::::::p i::::::il::::::li::::::i n::::n    n::::n g::::::::::::::::g 
     CCC::::::::::::C oo:::::::::::oo m::::m   m::::m   m::::m p::::::::::::::pp  i::::::il::::::li::::::i n::::n    n::::n  gg::::::::::::::g 
        CCCCCCCCCCCCC   ooooooooooo   mmmmmm   mmmmmm   mmmmmm p::::::pppppppp    iiiiiiiilllllllliiiiiiii nnnnnn    nnnnnn    gggggggg::::::g 
                                                               p:::::p                                                                 g:::::g 
                                                               p:::::p                                                     gggggg      g:::::g 
                                                              p:::::::p                                                    g:::::gg   gg:::::g 
                                                              p:::::::p                                                     g::::::ggg:::::::g 
                                                              p:::::::p                                                      gg:::::::::::::g  
                                                              ppppppppp                                                        ggg::::::ggg    
                                                                                                                                  gggggg       
"""
	)

	cli_args = sys.argv[1:]
	if cli_args: 
		for file in cli_args: compileScript(file)
	else:
		print("Automatic Compile\n")
		compileScript("Change - Close all REVIEW")
		compileScript("Change - IMPL to REVIEW")