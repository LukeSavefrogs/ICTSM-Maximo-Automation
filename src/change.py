from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import sys
import os

import maximo_gui_connector as MGC

from maximo_gui_connector import MaximoWorkflowError, MaximoLoginFailed
from maximo_gui_connector.constants import SUPPORTED_BROWSERS

import json
import time

import logging
import coloredlogs
import shared.utils as utils

from colorama import Fore, Back, Style


import traceback
import textwrap
import re
import inspect

import pdb;

# CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

# To remove '[WDM]' logs (https://github.com/SergeyPirogov/webdriver_manager#configuration)
# os.environ['WDM_LOG_LEVEL'] = '0'
# os.environ['WDM_PRINT_FIRST_LINE'] = 'False'


def getEntryPoint():
	is_executable = getattr(sys, 'frozen', False)
	
	if is_executable:
		# print("Program is an executable")
		return sys.executable

	# print("Program is a script")
	return inspect.stack()[-1][1]


CURRENT_DIR = os.path.dirname(os.path.realpath(getEntryPoint()))


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

		DESCRIZIONE = [
			"\n".join([ re.sub("^", "# ", line) for line in ASCII_ART.splitlines() if line.strip() != "" ]) + "\n",
			"# \n",
			"# > Inserisci qui sotto tutti i change che desideri portare in REVIEW.\n",
			"# > Le linee precedute dal carattere '#' verranno ignorate e possono essere cancellate.\n",
		]
		with open(CHANGES_FILE, "w") as file: 
			# Writing data to a file 
			file.writelines(DESCRIZIONE) 

		os.startfile(CHANGES_FILE, 'open')
		# open(CHANGES_FILE, "w").close()

	return array_data


def implToReview (verbose=False, show_browser=False):
	log_level = "INFO" if not verbose else "DEBUG"

	logger = logging.getLogger(__name__)
	logger2 = logging.getLogger("maximo_gui_connector")

	logger_consoleHandler = logging.StreamHandler(sys.stdout)
	logger_consoleHandler.setFormatter(logging.Formatter(fmt='[%(levelname)s] - %(message)s'))

	current_filename_no_ext = os.path.splitext(os.path.basename(getEntryPoint()))[0]


	logfile = os.path.join(CURRENT_DIR, f"{current_filename_no_ext}.log")

	logger_fileHandler = logging.FileHandler(filename=logfile)
	logger_fileHandler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(process)d - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))
	logger_fileHandler.setLevel(logging.INFO)

	# Add handlers to the logger
	logger.addHandler(logger_consoleHandler)
	logger.addHandler(logger_fileHandler)

	logger2.addHandler(logger_consoleHandler)

	logger.propagate = False

	
	coloredlogs.install(level=log_level, logger=logger, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	coloredlogs.install(level=log_level, logger=logger2, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	

	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

	CHANGES = getChanges()

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

	completed = 0

	try:
		maximo = MGC.MaximoAutomation({ "debug": verbose, "headless": not show_browser })
		try:
			maximo.login(USERNAME, PASSWORD)
		except MaximoLoginFailed:
			print("----------------------------------------------------------------------")
			print("ATTENZIONE!".center(70))
			print("IMPOSSIBILE PROSEGUIRE:".center(70))
			print("")
			print("PASSWORD ERRATA".center(70))
			print("----------------------------------------------------------------------")
			CREDENTIALS_MANAGER.addFailedLoginAttempt()
			
			maximo.close()
			
			sys.exit(1)
		else:
			CREDENTIALS_MANAGER.clearFailedLoginAttempts()

		browser = maximo.driver

		INPRG_MAX_RETRIES = 5
		completed = 0

		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Activities and Tasks")

		for index, change in enumerate(CHANGES):
			logger.info("Current change: {change} ({partial} of {total})".format(change=change, partial=index+1, total=len(CHANGES)))

			maximo.advancedSearch({ "Parent:": change.strip() })

			foregroundDialog = maximo.getForegroundDialog()
			
			# If change was already CLOSED (not REVIEW)
			if foregroundDialog and "No records were found that match the specified query" in foregroundDialog["text"]:
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

			new_status_id = "#" + maximo.getNamedInput("New Status:").get_attribute('id')
					
			if not maximo.isInputEditable(element_selector=new_status_id):
				logger.error(f"You don't have enough permissions to manage the change {change}\n")
				
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
					

					try:
						taskRetryTimes += 1
						maximo.clickRouteWorkflow()

						foregroundDialog = maximo.getForegroundDialog()
						logger.debug(f"IMPL -> INPRG: {foregroundDialog}")

						if foregroundDialog:
							if "Complete Workflow Assignment" in foregroundDialog["title"]:
								foregroundDialog["buttons"]["OK"].click()
								maximo.waitUntilReady()

							elif "Please verify that TASK has a valid schedule start" in foregroundDialog["text"]:
								logger.error(f"Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}")

								foregroundDialog["buttons"]["Close"].click()
								maximo.waitUntilReady()
								break
							
							elif "The Change related to this task has been rescheduled." in foregroundDialog["text"]:
								logger.error(f"Il change e' stato RISCHEDULATO e non e' ancora in IMPL. Lo salto")

								foregroundDialog["buttons"]["Close"].click()
								maximo.waitUntilReady()
								break

							elif all(token in foregroundDialog["text"] for token in ["Warning! The Approved Scheduled Window has expired!", "According to Global Standard Process it's necessary to RE-SCHEDULE this change."]):
								logger.warning(f"Il change DEVE ESSERE RISCHEDULATO")

								# Dialog di avviso
								foregroundDialog["buttons"]["Close"].click()
								maximo.waitUntilReady()

								# Viene mostrato un altro dialog con due opzioni:
								# - Rischedulare il change
								# - Proseguire comunque 
								anotherDialog = maximo.getForegroundDialog()
								
								# Se non trovo il dialog che mi aspetto, esce
								if not anotherDialog:
									logger.error(f"Non ho trovato nessun dialog (atteso il dialog per la rischedulazione)")
									break
								if anotherDialog["title"].strip() != "Manual Input":
									logger.error(f"Non ho trovato il dialog per la rischedulazione (trovato dialog con titolo '{anotherDialog['title']}' e testo '{anotherDialog['text']}')")
									
									if "Close" in anotherDialog["buttons"]:
										logger.info("Trovato pulsante 'Close'. Chiudo il dialog...")
										anotherDialog["buttons"]["Close"].click()
										maximo.waitUntilReady()

									break

								# Seleziono "Continue anyway"
								browser.find_element_by_id("mc1493e00-rb").click()
								anotherDialog["buttons"]["OK"].click()
								maximo.waitUntilReady()
								logger.info("Cliccato su 'Continue anyway'. Ora posso procedere normalmente...")
					
								# break
							
							else:
								logger.error(f"Trovato dialog inatteso di tipo '{foregroundDialog['type']}' con titolo '{foregroundDialog['title']}' e testo '{foregroundDialog['text']}'")
								
								if "Close" in foregroundDialog["buttons"]:
									logger.info("Trovato pulsante 'Close'. Chiudo il dialog...")
									foregroundDialog["buttons"]["Close"].click()
									maximo.waitUntilReady()

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

					except MaximoWorkflowError as e:
						logger.error(f"Route Workflow fallito: comparso dialog 'Change SCHEDULED DATE is not reach to start Activity'")
						logger.error(f"Solitamente questo e' dovuto ad una data di Target Start FUTURA. Controllare le date in cui e' stato schedulato il change")
						break

					except Exception as e:
						logger2.exception(f"Errore in fase di cambio IMPL -> INPRG")
						break

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
							# print(f"INPRG -> COMP: {foregroundDialog}")

							if foregroundDialog:
								if "Complete Workflow Assignment" in foregroundDialog["title"]:
									foregroundDialog["buttons"]["OK"].click()
									maximo.waitUntilReady()

								# If change is not yet in INPRG status
								elif "The change is not in status INPRG yet, please wait few seconds then try again." in foregroundDialog["text"]:
									logger.warning(f"Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}")

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
		logger2.exception(f"Errore generico")
		
		logger2.debug("Starting Python debugger...")
		pdb.set_trace()


	finally:
		print(
			"\n----------------------------------------------------------------------\n" +
			f"Sono stati portati in REVIEW {completed}/{len(CHANGES)} change".center(70) + 
			"\n----------------------------------------------------------------------\n"
		)
		print()

		if maximo.debug: input ("Premi INVIO per continuare")

		# Per evitare che se il programma dumpi troppo presto cercando di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		input("Premi INVIO per terminare il programma...")



def closeAllReview(verbose=False, show_browser=False):
	log_level = "INFO" if not verbose else "DEBUG"
	
	logger = logging.getLogger(__name__)
	logger2 = logging.getLogger("maximo_gui_connector")

	logger_consoleHandler = logging.StreamHandler(sys.stdout)
	logger_consoleHandler.setFormatter(logging.Formatter(fmt='[%(levelname)s] - %(message)s'))

	current_filename_no_ext = os.path.splitext(os.path.basename(getEntryPoint()))[0]


	logfile = os.path.join(CURRENT_DIR, f"{current_filename_no_ext}.log")

	logger_fileHandler = logging.FileHandler(filename=logfile)
	logger_fileHandler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(process)d - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))

	# Add handlers to the logger
	logger.addHandler(logger_consoleHandler)
	logger.addHandler(logger_fileHandler)

	logger2.addHandler(logger_consoleHandler)

	logger.setLevel(logging.INFO if not verbose else logging.DEBUG)
	logger.propagate = False

	coloredlogs.install(level=log_level, logger=logger, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	coloredlogs.install(level=log_level, logger=logger2, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	

	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	# Get credentials
	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

	change_closed = 0
	CHANGES = []

	try:
		maximo = MGC.MaximoAutomation({ "debug": verbose, "headless": not show_browser })
		try:
			maximo.login(USERNAME, PASSWORD)
		except MaximoLoginFailed:
			print("----------------------------------------------------------------------")
			print("ATTENZIONE!".center(70))
			print("IMPOSSIBILE PROSEGUIRE:".center(70))
			print("")
			print("PASSWORD ERRATA".center(70))
			print("----------------------------------------------------------------------")
			CREDENTIALS_MANAGER.addFailedLoginAttempt()
			
			maximo.close()
			
			sys.exit(1)
		else:
			CREDENTIALS_MANAGER.clearFailedLoginAttempts()

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

		# print(records)

		CHANGES = [ record["data"]["Change"] for record in records ]

		logger.info(f"Data collected. Total {len(CHANGES)} changes\n")

		change_closed = 0
		for index, change in enumerate(CHANGES):
			logger.info(f"CERCO change: {change} (" + str(index + 1) + " of " + str(len(CHANGES)) + ")")

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

			logger.info(f"CHIUSO change: {change} (" + str(index + 1) + " of " + str(len(CHANGES)) + ")\n")
			change_closed += 1


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		logger.critical("Generic error during the script execution..." + str(e))
		logger.exception(e)

		logger2.debug("Starting Python debugger...")
		pdb.set_trace()
		
	except MaximoLoginFailed as e:
		logger.critical(f"Couldn't login... Check the credentials stored in file `maximo_credentials.json`! {str(e)}")

	finally:
		print(
			"\n----------------------------------------------------------------------\n" +
			f"Sono stati portati in CLOSE {change_closed}/{len(CHANGES)} change".center(70) + 
			"\n----------------------------------------------------------------------\n"
		)


		# Per evitare che se il programma dumpa troppo presto cerca di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		print()
		input("Premi INVIO per terminare il programma...")


def getAllOpen ():
	logger = logging.getLogger(__name__)
	logger2 = logging.getLogger("maximo_gui_connector")

	coloredlogs.install(level='INFO', logger=logger, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	coloredlogs.install(level='INFO', logger=logger2, fmt='[%(asctime)s] %(levelname)-8s - %(message)s')
	

	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	# Get credentials
	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

	try:
		maximo = MGC.MaximoAutomation({ "debug": True, "headless": False })
		try:
			maximo.login(USERNAME, PASSWORD)
		except MaximoLoginFailed:
			print("----------------------------------------------------------------------")
			print("ATTENZIONE!".center(70))
			print("IMPOSSIBILE PROSEGUIRE:".center(70))
			print("")
			print("PASSWORD ERRATA".center(70))
			print("----------------------------------------------------------------------")
			CREDENTIALS_MANAGER.addFailedLoginAttempt()

			maximo.close()
			
			sys.exit(1)
		else:
			CREDENTIALS_MANAGER.clearFailedLoginAttempts()
	
		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Changes")

		# Search ONLY the open Changes...
		maximo.advancedSearch({ 
			"Status:": "=IMPL,=INPRG,=INPROG", 
			"Is Task?": "N", 
			"Customer:": "=WTI-00" 
		})

		maximo.setFilters({"Owner Group": "=V-OST-IT-SYO-OPS-TRENITALIA_ICTSM"})

		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()

		logger.info(f"Trovati {len(records)} change aperti con 'Owner Group' == 'V-OST-IT-SYO-OPS-TRENITALIA_ICTSM'\n")

		# Used only for formatting purposes
		unique_statuses = set([ record["data"]["Status"] for record in records ])
		biggest_status = max(unique_statuses, key=len) if unique_statuses else ""

		for index, change in enumerate(records):
			change_id = change["data"]["Change"]
			change_summary = change["data"]["Summary"].replace("\n", " ")
			change_status = change["data"]["Status"]
			change_date = change["data"]["Reported Date"]

			print(f"[{str(index+1).rjust(len(str(len(records))))}/{len(records)}] {change_id} ({change_status.ljust(len(biggest_status))}) [Created on '{Fore.LIGHTCYAN_EX}{change_date}{Style.RESET_ALL}'] - {Fore.YELLOW}{change_summary}{Style.RESET_ALL}")


		print()
		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		logger.critical("Generic error during the script execution..." + str(e))
		logger.exception(e)

	except MaximoLoginFailed as e:
		logger.critical(f"Couldn't login... Check the credentials stored in file `maximo_credentials.json`! {str(e)}")

	finally:
		# Per evitare che se il programma dumpa troppo presto cerca di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		print()
		input("Premi INVIO per terminare il programma...")