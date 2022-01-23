import sys, os, re, argparse
from updateutils import checkUpdated

import change

# Import logging modules
import logging
# import coloredlogs

from shared.utils import get_entry_point, get_entry_point_dir

# pyinstaller --noconfirm --log-level=WARN --onefile --specpath=./build_spec --add-data=../src/Change - IMPL to REVIEW.version;. ./src/Change - IMPL to REVIEW.py 

from rich.logging import RichHandler

# From: http://patorjk.com/software/taag/#p=display&h=0&v=3&f=3D-ASCII&t=Lista%20Change
ASCII_ART = r"""
 ___           ___      ________       _________    ________          ________      ___  ___      ________      ________       ________      _______      
|\  \         |\  \    |\   ____\     |\___   ___\ |\   __  \        |\   ____\    |\  \|\  \    |\   __  \    |\   ___  \    |\   ____\    |\  ___ \     
\ \  \        \ \  \   \ \  \___|_    \|___ \  \_| \ \  \|\  \       \ \  \___|    \ \  \\\  \   \ \  \|\  \   \ \  \\ \  \   \ \  \___|    \ \   __/|    
 \ \  \        \ \  \   \ \_____  \        \ \  \   \ \   __  \       \ \  \        \ \   __  \   \ \   __  \   \ \  \\ \  \   \ \  \  ___   \ \  \_|/__  
  \ \  \____    \ \  \   \|____|\  \        \ \  \   \ \  \ \  \       \ \  \____    \ \  \ \  \   \ \  \ \  \   \ \  \\ \  \   \ \  \|\  \   \ \  \_|\ \ 
   \ \_______\   \ \__\    ____\_\  \        \ \__\   \ \__\ \__\       \ \_______\   \ \__\ \__\   \ \__\ \__\   \ \__\\ \__\   \ \_______\   \ \_______\
    \|_______|    \|__|   |\_________\        \|__|    \|__|\|__|        \|_______|    \|__|\|__|    \|__|\|__|    \|__| \|__|    \|_______|    \|_______|
                          \|_________|                                                                                                                    
"""

def getChanges (file_name = 'changes.txt'):
	"""
	Gets the changes from a local text file named 'changes.txt'.

	Ignores blank lines and lines starting with '#'

	Returns:
		list: contains all the changes to process
	"""
	array_data = []

	try:
		with open(file_name, "r") as f:
			array_data = [l for l in (line.strip() for line in f) if l and not l.startswith("#")]

	except FileNotFoundError as e:
		print(f"File '{file_name}' non trovato. Lo creo")

		INITIAL_FILE_CONTENT = [
			"\n".join([ re.sub("^", "# ", line) for line in ASCII_ART.splitlines() if line.strip() != "" ]) + "\n",
			"# \n",
			"# > Inserisci qui sotto tutti i change che desideri portare in REVIEW.\n",
			"# > Le linee precedute dal carattere '#' verranno ignorate e possono essere cancellate.\n",
		]
		with open(file_name, "w") as file: 
			# Writing data to a file 
			file.writelines(INITIAL_FILE_CONTENT) 

		os.startfile(file_name, 'open')
		# open(file_name, "w").close()

	return array_data



if __name__ == "__main__":
	# Gets the full path to both the executable/script and its parent directory
	CURRENT_FILE = get_entry_point()
	CURRENT_DIR = get_entry_point_dir()

	# Gets the script/executable filename WITHOUT extension
	current_filename_no_ext = os.path.splitext(os.path.basename(CURRENT_FILE))[0]

	# Parse the CLI parameters passed to the program
	parser = argparse.ArgumentParser(description='Porta i change specificati nel file "changes.txt" in stato "REVIEW" (da IMPL o INPRG).')
	parser.add_argument('-X', '--show-browser', dest='show_browser', action='store_true',
						help="Mostra l'interfaccia grafica di Maximo.")
	parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
						help="Aumenta la verbosita' dell'output.")
	args = parser.parse_args()


	# Gets the desired loggers
	logger = logging.getLogger("maximo4ictsm")
	logger_mgc = logging.getLogger("maximo_gui_connector")

	# Configures desired logging level and format
	log_level = "DEBUG" if args.verbose else "INFO"
	log_format = '[%(asctime)s] {%(name)s/%(funcName)s} %(levelname)-8s - %(message)s' if args.verbose else '[%(asctime)s] %(levelname)-8s - %(message)s'
	
	# Configures custom File Handler for logger
	logfile = os.path.join(CURRENT_DIR, f"{current_filename_no_ext}.log")
	logger_fileHandler = logging.FileHandler(filename=logfile)
	logger_fileHandler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(process)d - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))
	logger_fileHandler.setLevel(logging.INFO)

	# Add handlers to the logger
	# logger.addHandler(logger_fileHandler)
	# console.print("TEST")
	logger.addHandler(RichHandler(omit_repeated_times=False, rich_tracebacks=True))
	logger.setLevel(log_level)
	logger_mgc.addHandler(RichHandler(level="INFO", omit_repeated_times=False, rich_tracebacks=True))
	logger_mgc.setLevel(log_level)
	
	# Installs the loggers
	# coloredlogs.install(level=log_level, logger=logger, fmt=log_format)
	# coloredlogs.install(level=log_level, logger=logger_mgc, fmt=log_format)


	checkUpdated(__file__)
	# checkUpdated("Change - IMPL to REVIEW.py")


	CHANGES = getChanges(os.path.join(CURRENT_DIR, "changes.txt"))
	if not CHANGES:	
		print()
		print("Non e' stato specificato nessun Change da portare in REVIEW. Esco...\n")

		sys.exit(0)
	
	print("---------------------------------------------------------------------------")
	print()
	print("NOTA:")
	print(f"I principali eventi verranno salvati sul file di log: '{logfile}''")
	print()
	print("---------------------------------------------------------------------------\n")


	change.implToReview(change_list=CHANGES, verbose=args.verbose, show_browser=args.show_browser)