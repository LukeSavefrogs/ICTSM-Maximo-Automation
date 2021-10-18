from updateutils import checkUpdated

import change
import argparse
import os

import logging
import coloredlogs

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Chiude tutti i change trovati in stato "REVIEW".')
	parser.add_argument('-X', '--show_browser', dest='show_browser', action='store_true',
						help="Mostra l'interfaccia grafica di Maximo.")
	parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
						help="Aumenta la verbosita' dell'output.")

	args = parser.parse_args()


	#### LOGGING SECTION - START
	# Gets the desired loggers
	logger = logging.getLogger(__name__)
	logger_mgc = logging.getLogger("maximo_gui_connector")

	# Configures desired logging level and format
	log_level = "DEBUG" if args.verbose else "INFO"
	log_format = '[%(asctime)s] {%(name)s/%(funcName)s} %(levelname)-8s - %(message)s' if args.verbose else '[%(asctime)s] %(levelname)-8s - %(message)s'
	
	# Installs the loggers
	coloredlogs.install(level=log_level, logger=logger, fmt=log_format)
	coloredlogs.install(level=log_level, logger=logger_mgc, fmt=log_format)
	#### LOGGING SECTION - END



	checkUpdated(__file__)
	# checkUpdated("Change - IMPL to REVIEW.py")

	change.getAllOpen(verbose=args.verbose, show_browser=args.show_browser)