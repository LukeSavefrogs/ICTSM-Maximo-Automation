from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import sys
import os

from maximo_gui_connector import MaximoAutomation
from maximo_gui_connector import MaximoWorkflowError, MaximoLoginFailed
from maximo_gui_connector.constants import SUPPORTED_BROWSERS

import json
import time

import logging
from updateutils import checkUpdated

def getCredentials ():	
	"""
	Gets the credentials from a local json

	Returns:
		tuple: contains USERNAME and PASSWORD
	"""
	fileName = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'maximo_credentials.json')
	with open(fileName, "r") as f:
		data = json.load(f)

	# return (data["USERNAME"], "TEST_WRONG_PASSWORD")
	return (data["USERNAME"], data["PASSWORD"])




def closeAllReview(): 
	try:
		logger = logging.getLogger(__name__)
		logger2 = logging.getLogger("maximo_gui_connector")

		logger_consoleHandler = logging.StreamHandler(sys.stdout)
		logger_consoleHandler.setFormatter(logging.Formatter(fmt='[%(levelname)s] - %(message)s'))

		current_directory = os.path.dirname(os.path.realpath(__file__))
		current_filename_no_ext = os.path.splitext(os.path.basename(__file__))[0]


		logfile = os.path.join(current_directory, f"{current_filename_no_ext}.log")

		logger_fileHandler = logging.FileHandler(filename=logfile)
		logger_fileHandler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(process)d - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))

		# Add handlers to the logger
		logger.addHandler(logger_consoleHandler)
		logger.addHandler(logger_fileHandler)

		logger2.addHandler(logger_consoleHandler)

		logger.setLevel(logging.INFO)
		logger.propagate = False


		# Get credentials
		USERNAME, PASSWORD = getCredentials()
				
		maximo = MaximoAutomation({ "debug": False, "headless": True })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver
	
		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Changes")

		# Setup the filters to get ONLY the Changes owned by our group...
		maximo.setFilters({ 
			"status": "=REVIEW", 
			"owner group": "V-OST-IT-SYO-OPS-TRENITALIA_ICTSM" 
		})

		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()

		print(records)

		changes = [ record["data"]["Change"] for record in records ]

		logger.info(f"Data collected. Total {len(changes)} changes\n")

		change_closed = 0
		for index, change in enumerate(changes):
			logger.info(f"Cerco change: {change} (" + str(index + 1) + " of " + str(len(changes)) + ")")

			maximo.quickSearch(change)
			maximo.handleIfComingFromDetail()
			
			# Change to the "Details & Closure" page
			maximo.goto_tab("Details & Closure")

			maximo.waitForInputEditable("#m8e32699b-tb")


			maximo.setNamedInput({ 
				"Completion Code:": "COMPLETE", 
			})
						
			maximo.waitUntilReady()

			# Click on the "Change Status" button and set the new Status
			maximo.routeWorkflowDialog.openDialog()
			maximo.routeWorkflowDialog.setStatus("CLOSE")
			
			time.sleep(0.5)
			
			# Click on "Route Workflow" button
			try:
				maximo.routeWorkflowDialog.clickRouteWorkflow()

			except MaximoWorkflowError as exception:
				logger.exception("Error while clicking on the 'Route Workflow' button: " + str(exception) + "\n")

				continue
			except Exception as e:
				logger.exception(e)
				break

			time.sleep(0.5)

			maximo.routeWorkflowDialog.closeDialog()

			logger.info(f"Chiuso change: {change} (" + str(index + 1) + " of " + str(len(changes)) + ")\n")
			change_closed += 1


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		logger.critical("Generic error during the script execution..." + str(e))
		logger.exception(e)

	except MaximoLoginFailed as e:
		logger.critical(f"Couldn't login... Check the credentials stored in file `maximo_credentials.json`! {str(e)}")

	finally:
		print(
			"\n----------------------------------------------------------------------\n" + 
			f"             Sono stati portati in CLOSE {change_closed}/{len(changes)} change\n" +
			"----------------------------------------------------------------------\n"
		)


		# Per evitare che se il programma dumpa troppo presto cerca di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		print()
		input("Premi un tasto per terminare il programma")


		
if __name__ == "__main__":
	checkUpdated(__file__)
	
	closeAllReview()