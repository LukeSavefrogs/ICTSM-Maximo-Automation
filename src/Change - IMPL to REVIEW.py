from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import maximo_gui_connector as MGC
from maximo_gui_connector import MaximoWorkflowError

import json
import time

import argparse
import logging

import os
import sys


def getCredentials ():	
	"""
	Gets the credentials from a local json

	Returns:
		tuple: contains USERNAME and PASSWORD
	"""
	fileName = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'maximo_credentials.json')
	with open(fileName) as f:
		data = json.load(f)

	return (data["USERNAME"], data["PASSWORD"])


def getChanges (fileName = 'changes.txt'):
	"""
	Gets the changes from a local text file named 'changes.txt'.

	Ignores blank lines and lines starting with '#'

	Returns:
		list: contains all the changes to process
	"""
	file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), fileName)
	with open(file_path, "r") as f:
		array_data = [l for l in (line.strip() for line in f) if l and not l.startswith("#")]

	return array_data

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

		try:
			# Get credentials
			USERNAME, PASSWORD = getCredentials()
			
			CHANGES = getChanges()
		except FileNotFoundError as e:
			fileName = e
			logger2.critical(f"File '{fileName}' mancante. Controllare e riavviare lo script... ")
			sys.exit(2)


		maximo = MGC.MaximoAutomation({ "debug": False, "headless": False })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver

		INPRG_MAX_RETRIES = 5


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
					except MaximoWorkflowError:
						if taskRetryTimes > 5:
							logger2.error(f"Cannot change Task from IMPL to INPRG")
							break

						logger2.warning(f"Schedule Start not reached. Retrying in 20 seconds... ({taskRetryTimes} of 5 MAX)")
						time.sleep(20)

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

							# If change is not yet in INPRG status
							if browser.find_elements_by_id("m15f1c9f0-pb"):
								if maximo.debug: logger.debug(f"Task is not yet in INPRG status: retrying in 10 seconds ({retryTimes} attempt of {INPRG_MAX_RETRIES} MAX)")

								browser.find_element_by_id("m15f1c9f0-pb").click()
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
		print()
		input("Premi un tasto per terminare il programma")

		try:
			maximo.close()
		except NameError as e:
			pass