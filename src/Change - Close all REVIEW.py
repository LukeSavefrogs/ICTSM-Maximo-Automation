from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import sys
import os

from maximo_gui_connector import MaximoAutomation
from maximo_gui_connector import MaximoWorkflowError
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

	return (data["USERNAME"], data["PASSWORD"])


if __name__ == "__main__":
	checkUpdated(__file__)
	
	try:
		logger = logging.getLogger(__name__)
		logger2 = logging.getLogger()

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


		changes = [ record["data"]["change"]["value"] for record in records ]

		for index, change in enumerate(changes):
			maximo.quickSearch(change)
			maximo.handleIfComingFromDetail()
			
			# Change to the "Details & Closure" page
			maximo.goto_tab("Details & Closure")

			maximo.waitForInputEditable("#m8e32699b-tb")

			browser.find_element_by_id("m8e32699b-tb").send_keys("COMPLETE")
			browser.find_element_by_id("m8e32699b-tb").send_keys(Keys.TAB)
			
			maximo.waitUntilReady()

			# Click on the "Change Status" button and set the new Status
			maximo.routeWorkflowDialog.openDialog()
			maximo.routeWorkflowDialog.setStatus("CLOSE")
			
			time.sleep(0.5)
			
			# Click on "Route Workflow" button
			try:
				maximo.routeWorkflowDialog.clickRouteWorkflow()

			except MaximoWorkflowError as exception:
				print("Error while clicking on the 'Route Workflow' button:\n" + str(exception))

				continue
			except Exception as e:
				logger.exception(e)
				break

			time.sleep(0.5)

			maximo.routeWorkflowDialog.closeDialog()

			logger.info(f"Chiuso change: {change} (" + str(index + 1) + " of " + str(len(changes)) + ")\n")
			# break


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print()
		input("Premi un tasto per terminare il programma")

		maximo.close()