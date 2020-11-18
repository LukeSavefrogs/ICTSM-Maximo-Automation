from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

import maximo_gui_connector as MGC
from maximo_gui_connector import MaximoWorkflowError

import json
import time

import argparse
import logging

import os
import sys
from updateutils import checkUpdated
from os.path import expanduser
import shared.utils as utils

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


def getChanges (fileName = 'changes.txt'):
	"""
	Gets the changes from a local text file named 'changes.txt'.

	Ignores blank lines and lines starting with '#'

	Returns:
		list: contains all the changes to process
	"""
	array_data = []

	CHANGES_FILE = os.path.join(CURRENT_DIR, fileName)

	try:
		with open(CHANGES_FILE, "r") as f:
			array_data = [l for l in (line.strip() for line in f) if l and not l.startswith("#")]

	except FileNotFoundError as e:
		print(f"File '{fileName}' non trovato. Lo creo")

		open(CHANGES_FILE, "w").close()

	return array_data



if __name__ == "__main__":
	checkUpdated(__file__)
	# checkUpdated("Change - IMPL to REVIEW.py")

	logger = logging.getLogger(__name__)
	logger2 = logging.getLogger("maximo_gui_connector")

	logger_consoleHandler = logging.StreamHandler(sys.stdout)
	logger_consoleHandler.setFormatter(logging.Formatter(fmt='[%(levelname)s] - %(message)s'))

	current_filename_no_ext = os.path.splitext(os.path.basename(__file__))[0]


	logfile = os.path.join(CURRENT_DIR, f"{current_filename_no_ext}.log")

	logger_fileHandler = logging.FileHandler(filename=logfile)
	logger_fileHandler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(process)d - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))

	# Add handlers to the logger
	logger.addHandler(logger_consoleHandler)
	logger.addHandler(logger_fileHandler)

	logger2.addHandler(logger_consoleHandler)

	logger.setLevel(logging.INFO)
	logger.propagate = False

	# Get credentials
	USERNAME, PASSWORD = utils.getCredentials()

	CHANGES = getChanges()

	if not CHANGES:
		print()
		print("Non e' stato specificato nessun Change da portare in REVIEW. Esco...\n")

		exit(0)
	
	print("---------------------------------------------------------------------------")
	print()
	print("NOTA:")
	print(f"I principali eventi verranno salvati sul file di log: '{logfile}''")
	print()
	print("---------------------------------------------------------------------------\n")

	completed = 0

	try:
		maximo = MGC.MaximoAutomation({ "debug": False, "headless": True })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver

		INPRG_MAX_RETRIES = 5
		completed = 0

		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Activities and Tasks")

		for index, change in enumerate(CHANGES):
			logger.info("Current change: {change} ({partial} of {total})".format(change=change, partial=index+1, total=len(CHANGES)))

			browser.find_element_by_id("quicksearchQSMenuImage").click()
			maximo.waitUntilReady()

			browser.find_element_by_id("menu0_SEARCHMORE_OPTION_a_tnode").click()
			maximo.waitUntilReady()

			time.sleep(1.5)




			maximo.setNamedInput({ "Parent:": change.strip() })

			# Find with the provided filters
			browser.find_element_by_id("maa8a5ebf-pb").click()
			maximo.waitUntilReady()

			# If change was already CLOSED (not REVIEW)
			if browser.find_elements_by_id("m88dbf6ce-pb") and "No records were found that match the specified query" in browser.find_element_by_id("mb_msg").get_attribute("innerText"):
				logger.info(f"Parent Change {change} is already in CLOSED status (not open Tasks found)\n")

				browser.find_element_by_id("m88dbf6ce-pb").click()
				maximo.waitUntilReady()

				continue

			if not browser.find_elements_by_id("m714e5172-tb"):
				tasks = maximo.getAllRecordsFromTable()

				logger.error("Found {n_tasks} tasks in total. The script, as of now, only accepts changes with a single task. Skipping...\n".format(n_tasks=len(tasks)))
				continue

			status = maximo.getNamedInput("Status:").get_attribute('value').upper()
			if status == "COMP":
				logger.info(f"Task for change {change} is already in COMP status\n")

				continue
			
			taskRetryTimes = 0
			while True:
				status = maximo.getNamedInput("Status:").get_attribute('value').upper()

				logger.debug(f"Current status: {status}")
				
				if status == "IMPL":
					maximo.setNamedInput({ 
						"New Status:": "INPRG", 
						"Task Owner:": USERNAME 
					})
					
					time.sleep(1)

					# maximo.setNamedInput({ "Task Owner:": USERNAME })
					# maximo.waitUntilReady()

					# time.sleep(1)
					

					try:
						taskRetryTimes += 1
						maximo.clickRouteWorkflow()

						foregroundDialog = maximo.getForegroundDialog()
						print(f"IMPL -> INPRG: {foregroundDialog}")

						# TODO: Da portare all'interno dei singoli script per una migliore astrazione
						if foregroundDialog:
							if "Complete Workflow Assignment" in foregroundDialog["title"]:
								foregroundDialog["buttons"]["OK"].click()
								maximo.waitUntilReady()

							elif "Please verify that TASK has a valid schedule start" in foregroundDialog["text"]:
								logger.error(f"Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}")

								foregroundDialog["buttons"]["Close"].click()
								break

							if maximo.driver.find_elements_by_id("msgbox-dialog_inner"):
								msg_box_text = maximo.driver.find_element_by_id("mb_msg").get_attribute("innerText").strip()

								if "Change SCHEDULED DATE is not reach to start Activity" in msg_box_text:
									btn_close = maximo.driver.find_element_by_id("m15f1c9f0-pb")
									btn_close.click()

									maximo.waitUntilReady()

									if taskRetryTimes > 5:
										logger.error(f"Cannot change Task from IMPL to INPRG")
										break

									logger2.warning(f"Schedule Start not reached. Retrying in 20 seconds... ({taskRetryTimes} of 5 MAX)")
									time.sleep(20)

					except Exception as e:
						logger2.critical(f"Error: {e}")

					if browser.find_elements_by_id("m15f1c9f0-pb") and "The Approved Scheduled Window has expired" in browser.find_element_by_id("mb_msg").get_attribute("innerText"):
						browser.find_element_by_id("m15f1c9f0-pb").click()
						maximo.waitUntilReady()
						browser.find_element_by_id("mc1493e00-rb").click()
						maximo.waitUntilReady()
						browser.find_element_by_id("m37917b04-pb").click()
						maximo.waitUntilReady()

					time.sleep(3)

				elif status == "INPRG":
					retryTimes = 0

					try:
						while retryTimes < INPRG_MAX_RETRIES:
							retryTimes += 1

							maximo.setNamedInput({ "New Status:": "COMP", "Task Completion Code:": "COMPLETE" })

							time.sleep(1.5)

							if maximo.debug: logger.debug("Clicking on Route WF")

							maximo.clickRouteWorkflow()
							time.sleep(3)

							foregroundDialog = maximo.getForegroundDialog()
							print(f"INPRG -> COMP: {foregroundDialog}")

							if foregroundDialog:
								if "Complete Workflow Assignment" in foregroundDialog["title"]:
									foregroundDialog["buttons"]["OK"].click()
									maximo.waitUntilReady()

								# If change is not yet in INPRG status
								elif "The change is not in status INPRG yet, please wait few seconds then try again." in foregroundDialog["text"]:
									logger.error(f"Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}")

									foregroundDialog["buttons"]["Close"].click()
									maximo.waitUntilReady()

									if maximo.debug: logger.debug(f"Task is not yet in INPRG status: retrying in 10 seconds ({retryTimes} attempt of {INPRG_MAX_RETRIES} MAX)")
									time.sleep(10)

									continue
							break
						else:
							logger.error(f"Reached maximum retries number ({INPRG_MAX_RETRIES}) while trying to go from INPRG to COMP")

							break
					except MaximoWorkflowError as e:
						logger.exception(str(e))
						break
				elif status == "COMP":
					logger.info(f"Task for change {change} is now in COMP status\n")
					completed += 1
					
					break
				else:
					logger.error(f"Status {status} not handled by the script!\n")

					break

				if maximo.debug: logger.debug(f"Finished current status cycle... Getting next status")

		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print(
			"\n----------------------------------------------------------------------\n" +
			f"Sono stati portati in REVIEW {completed}/{len(CHANGES)} change".center(70) + 
			"\n----------------------------------------------------------------------\n"
		)
		print()
		
		# Per evitare che se il programma dumpi troppo presto cercando di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		input("Premi INVIO per terminare il programma...")