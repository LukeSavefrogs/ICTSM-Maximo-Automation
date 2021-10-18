import os, argparse
from updateutils import checkUpdated

import change

# Import logging modules
import logging, coloredlogs

from shared.utils import get_entry_point, get_entry_point_dir


if __name__ == "__main__":
	# Gets the full path to both the executable/script and its parent directory
	CURRENT_FILE = get_entry_point()
	CURRENT_DIR = get_entry_point_dir()

	# Gets the script/executable filename WITHOUT extension
	current_filename_no_ext = os.path.splitext(os.path.basename(CURRENT_FILE))[0]

	parser = argparse.ArgumentParser(description='Chiude tutti i change trovati in stato "REVIEW".')
	parser.add_argument('-X', '--show_browser', dest='show_browser', action='store_true',
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
	logger.addHandler(logger_fileHandler)	
	
	# Installs the loggers
	coloredlogs.install(level=log_level, logger=logger, fmt=log_format)
	coloredlogs.install(level=log_level, logger=logger_mgc, fmt=log_format)



	checkUpdated(__file__)
	# checkUpdated("Change - Close all REVIEW.py")
	
	change.closeAllReview(verbose=args.verbose, show_browser=args.show_browser)