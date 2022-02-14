from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import sys
import os

import maximo_gui_connector as MGC

from maximo_gui_connector import MaximoWorkflowError, MaximoLoginFailed
from maximo_gui_connector.constants import SUPPORTED_BROWSERS

import time

import shared.utils as utils

import logging
logger = logging.getLogger("maximo4ictsm")

from colorama import Fore, Back, Style

import inspect

import tempfile

from pathlib import Path


import rich

def getEntryPoint():
	is_executable = getattr(sys, 'frozen', False)
	
	if is_executable:
		# print("Program is an executable")
		return sys.executable

	# print("Program is a script")
	return inspect.stack()[-1][1]


# OLD - Don't use!
# @deprecated
def implToReview (change_list: list, verbose=False, show_browser=False):
	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

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

		for index, change in enumerate(change_list):
			logger.info("Current change: {change} ({partial} of {total})".format(change=change, partial=index+1, total=len(change_list)))

			maximo.advancedSearch({ "Parent:": change.strip() })

			foregroundDialog = maximo.getForegroundDialog()
			
			# If change was already CLOSED (not REVIEW)
			if foregroundDialog and "No records were found that match the specified query" in foregroundDialog["text"]:
				logger.info(f"Parent Change {change} is already in CLOSED status (not open Tasks found)\n")

				browser.find_element(By.ID, "m88dbf6ce-pb").click()
				maximo.waitUntilReady()

				continue

			if not browser.find_elements(By.ID, "m714e5172-tb"):
				tasks = maximo.getAllRecordsFromTable()
				logger.error(f"Found {len(tasks)} tasks in total. The script, as of now, only accepts changes with a single task. Skipping...\n")
				continue
			
			close_task(maximo, USERNAME)

		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		logger.exception(f"Errore generico")
		
		# logger_mgc.debug("Starting Python debugger...")
		# pdb.set_trace()


	finally:
		print(
			"\n----------------------------------------------------------------------\n" +
			f"Sono stati portati in REVIEW {completed}/{len(change_list)} change".center(70) + 
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


def implToReview (change_list: list, verbose=False, show_browser=False):
	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

	completed = 0

	try:
		maximo = MGC.MaximoAutomation(window_size=(1920, 1080), config={ "debug": verbose, "headless": not show_browser })

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
		maximo.goto_section("Changes")

		print()

		for index, change in enumerate(change_list):
			logger.info("In corso: {change} ({partial} di {total})".format(change=change, partial=index+1, total=len(change_list)))

			maximo.quickSearch(change.strip())
			maximo.waitUntilReady()

			foregroundDialog = maximo.getForegroundDialog()
			
			# Se il change NON ESISTE
			if foregroundDialog and "No records were found that match the specified query" in foregroundDialog["text"]:
				logger.error(f"Il Change '{change}' NON esiste. Procedo con il prossimo.\n")

				logger.debug(foregroundDialog)
				
				try:
					foregroundDialog["buttons"]["OK"].click()
				except:
					browser.find_element(By.ID, "m88dbf6ce-pb").click()

				maximo.waitUntilReady()

				continue

			# ------------- 
			maximo.goto_tab("Change")


			# ------------- Prendi lo Status del Change
			maximo.routeWorkflowDialog.openDialog()
			maximo.waitUntilReady()
			current_status = maximo.routeWorkflowDialog.getStatus()
			maximo.waitUntilReady()
			maximo.routeWorkflowDialog.closeDialog()

			logger.info(f"Il Change {change} si trova in stato '{current_status}'")

			# ------------- 
			if current_status in ["REVIEW", "CLOSE", "CAN"]:
				logger.info(f"Nessuna azione necessaria\n")
				continue
			
			elif current_status in ["NEW"]:
				submitter = maximo.getNamedInput('Submitter:').get_attribute('value').strip()
				submitter_name = maximo.getNamedInput('Submitter Name:').get_attribute('value').strip()
				
				logger.critical(f"Il change e' ancora in stato NEW!")
				logger.error(f"Contattare il Submitter '{submitter_name}' ({submitter}) oppure avanzare il change manualmente.\n")
				continue

			elif current_status in ["ACC_CAT"]:
				submitter = maximo.getNamedInput('Submitter:').get_attribute('value').strip()
				submitter_name = maximo.getNamedInput('Submitter Name:').get_attribute('value').strip()
				
				logger.critical(f"Change SENZA TASK: Il change aperto da '{submitter_name}' ({submitter}) si trova ancora in stato di '{current_status}'.")
				logger.error(f"Portarlo in stato di IMPL e poi rilanciare lo script. Al momento lo salto!\n")
				continue
			
			elif current_status not in ["IMPL", "INPRG"]:
				submitter = maximo.getNamedInput('Submitter:').get_attribute('value').strip()
				submitter_name = maximo.getNamedInput('Submitter Name:').get_attribute('value').strip()

				logger.critical(f"Stato '{current_status}' NON VALIDO oppure non gestito dallo script.")
				logger.error(f"Contattare '{submitter_name}' ({submitter}) se si dovesse trattare di un errore oppure controllare manualmente.\n")
				continue


			maximo.goto_tab("Schedule")
			maximo.waitUntilReady()

			# Prende una lista di TUTTI i task legati al Change
			tasks_object = browser.execute_script("""
				return Array
					.from(document.querySelectorAll("#mbb442a0c_tbod-co_0 .tablerow[id^='mbb442a0c_tbod_tdrow-tr[R:']"))
					.map(el => {
						return {
							"id": el.querySelector("[id^='mbb442a0c_tdrow_[C:1]-c[R:']").innerText.trim(),
							"gruppo": el.querySelector("[id^='mbb442a0c_tdrow_[C:7]-c[R:']").innerText.trim()
						};
					});
			""")

			# Se non sono presenti Task
			if len(tasks_object) == 0:
				logger.error("Il change non ha ancora nessun Task aperto")
				continue

			task_ids = [ task["id"] for task in tasks_object if task["gruppo"] == "V-OST-IT-SYO-OPS-TRENITALIA_ICTSM" ]

			if len(task_ids) == 0:
				logger.warning("Il change NON contiene Task in carico al Team ICTSM!")
				continue

			logger.info(f"Trovati {len(task_ids)} task in carico al gruppo ICTSM ({len(tasks_object)} totali) {tasks_object}")

			for row_task_id in task_ids:
				logger.debug(f"Espando task n.{row_task_id}")
				task_row = browser.execute_script("""
					return Array
						.from(
							document.querySelectorAll("#mbb442a0c_tbod-co_0 .tablerow[id^='mbb442a0c_tbod_tdrow-tr[R:']")
						)
						.find(
							el => el.querySelector("[id^='mbb442a0c_tdrow_[C:1]-c[R:']").innerText.trim() == arguments[0]
						);
				""", row_task_id)

				# Espandi il task solo se non lo è già
				task_icon = task_row.find_element(By.CSS_SELECTOR, "[id^='mbb442a0c_tdrow_[C:0]-c[R:']")
				if task_icon.find_element(By.CSS_SELECTOR, "a > img").get_attribute("source").strip() == "img_row_unselect":
					task_icon.click()

				maximo.waitUntilReady()
				
				for retry in range(0, 3):
					try:
						tasks_contents = browser.find_elements(By.CSS_SELECTOR, "#mbb442a0c_tdet-co_0")
						task_id = maximo.getNamedInput("Task Id & Status:", context=tasks_contents).get_attribute("value").strip()

						logger.debug(f"Cerco e clicco l'elemento 'Detail Menu' di fianco all'elemento 'Activity:'...")
						
						detail_menu = maximo.getNamedInput("Activity:", context=tasks_contents)
						
						maximo.waitUntilReady()

						# Scrollo fino a che non trovo l'elemento
						ActionChains(browser).move_to_element(detail_menu).perform()
					except StaleElementReferenceException as e:
						logger.debug(f"StaleElementReferenceException => Non sono riuscito a trovare il menu dei dettagli (tentativo {retry} su 3)")
					else:
						break
				else:
					logger.exception("Non sono riuscito ad espandere le freccette per accedere al Task", extra={"tracebacks_show_locals": True})
				

				# Clicco sull'immagine con le frecce
				browser.execute_script("""
					console.log("Clicco sull'elemento: %o", arguments[0].nextElementSibling);
					arguments[0].nextElementSibling.click();
				""", detail_menu)

				maximo.waitUntilReady()

				try:
					WebDriverWait(browser, 5).until(EC.visibility_of_element_located((By.ID, "HYPERLINK_applink_undefined_a")))
				except TimeoutException:
					browser.execute_script("""
						console.log("Clicco sull'elemento con id '%s': %o", arguments[0], document.getElementById(arguments[0]).nextElementSibling);
						document.getElementById(arguments[0]).nextElementSibling.click();
					""", detail_menu.get_attribute("id"))
				
				# Cerco e clicco il context "Go To Activities and Tasks(MP)"
				logger.debug(f"Cerco e clicco il context 'Go To Activities and Tasks(MP)'...")
				browser.execute_script("""
					const target_text = arguments[0];
					Array
						.from(document.querySelectorAll('#menuholder #HYPERLINK_applink_undefined_a'))
						.find(el => el.innerText.trim() == target_text)
						.click();
				""", "Go To Activities and Tasks(MP)")
				
				maximo.waitUntilReady()

				# Aspetto di arrivare alla pagina dei task
				WebDriverWait(browser, 5).until(EC.title_contains("Activities and Tasks"))

				# time.sleep(1)

				logger.info("Status: " + maximo.getNamedInput("Status:").get_attribute("value"))
				
				time.sleep(1)


				close_task(maximo, USERNAME)


				# Go back
				logger.debug("Torno al Change principale")
				browser.execute_script("""
					return Array.from(document.querySelectorAll("#psuedoForm .bottomApp > .linkedAppTitle > a")).find(el => el.innerText.trim() == arguments[0]).click()
				""", "Changes (MP)")
				
				maximo.waitUntilReady()
				WebDriverWait(browser, 5).until(EC.visibility_of_element_located((By.ID, "mbb442a0c_tbod-co_0")))
				maximo.waitUntilReady()

				logger.debug("Sono nella tab 'Schedule' del Change principale. Proseguo con gli altri task...")



		maximo.logout()
	
	except Exception as e:
		logger.exception(f"Errore generico durante il cambio da IMPL a REVIEW")

		with tempfile.TemporaryFile() as tmp_file:
			path_to_image = str(Path(f"{tmp_file.name}.png").absolute())
			logger.info(f"Salvo screenshot in '{path_to_image}'")
			maximo.driver.save_screenshot(path_to_image)
			
			if sys.platform == "win32" and str(USERNAME).upper() == "ITY9DN3D":
				logger.info(f"Apro screenshot: '{path_to_image}'")
				os.startfile(path_to_image)

		
		
		# logger_mgc.debug("Starting Python debugger...")
		# pdb.set_trace()


	finally:
		rich.print(rich.panel.Panel(rich.align.Align(f"Sono stati portati in REVIEW {completed}/{len(change_list)} change", align="center"), title="Risultati", padding=2))
		
		print()

		if maximo.debug: input ("Premi INVIO per continuare")

		# Per evitare che se il programma dumpi troppo presto cercando di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		input("Premi INVIO per terminare il programma...")



def close_task(maximo: MGC.MaximoAutomation, owner_username, max_retries_inprg_comp = 3, max_retries_impl_inprg = 3):
	browser = maximo.driver

	# Se il task è già in stato 'COMP', allora esci con return code positivo
	status = maximo.getNamedInput("Status:").get_attribute('value').upper()
	if status == "COMP":
		logger.info(f"Il task si trova gia' in stato 'COMP'\n")

		return True

			
	# Se il campo di 'New Status:' non è modificabile significa che non possiamo modificarlo
	new_status_id = maximo.getNamedInput("New Status:").get_attribute('id')
	if not maximo.isInputEditable(f"#{new_status_id}"):
		logger.error(f"Non hai abbastanza permessi!\n")
		return False

	
	status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()
	logger.debug(f"Current status: {status}")

	# Inizializzo i contatori
	cur_retries_impl_inprg = 0
	cur_retries_inprg_comp = 0


	if status == "IMPL":
		new_status = status
		while new_status == status:
			# Se supera i tentatvi massimi
			if cur_retries_impl_inprg == max_retries_impl_inprg:
				logger.error(f"({cur_retries_impl_inprg} of {max_retries_impl_inprg} MAX)")
				return False

			# Incrementa il contatore
			cur_retries_impl_inprg += 1


			# Imposta il nuovo Status 'INPRG'
			maximo.setNamedInput({ 
				"New Status:": "INPRG", 
				"Task Owner:": owner_username 
			})
			
			time.sleep(1)


			# Provo a salvare
			try:
				maximo.clickRouteWorkflow()
			except MaximoWorkflowError as e:
				logger.error(f"Route Workflow fallito: comparso dialog 'Change SCHEDULED DATE is not reach to start Activity'")
				logger.error(f"Solitamente questo e' dovuto ad una data di Target Start FUTURA. Controllare le date in cui e' stato schedulato il change")
				break

			except Exception as e:
				logger.exception(f"Errore in fase di cambio di stato del Task da 'IMPL' a 'INPRG'")
				return False

			maximo.waitUntilReady()

			# Controllo se sono usciti dei Dialog
			foregroundDialog = maximo.getForegroundDialog()
			
			if foregroundDialog:
				if "Complete Workflow Assignment" in foregroundDialog["title"]:
					foregroundDialog["buttons"]["OK"].click()
					maximo.waitUntilReady()

				elif "Please verify that TASK has a valid schedule start" in foregroundDialog["text"]:
					logger.error(f"Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}")

					foregroundDialog["buttons"]["Close"].click()
					maximo.waitUntilReady()
					return False
				
				elif "The Change related to this task has been rescheduled." in foregroundDialog["text"]:
					logger.error(f"Il change e' stato RISCHEDULATO e non e' ancora in IMPL. Lo salto")

					foregroundDialog["buttons"]["Close"].click()
					maximo.waitUntilReady()
					return False


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
						return False

					if anotherDialog["title"].strip() != "Manual Input":
						logger.error(f"Non ho trovato il dialog per la rischedulazione (trovato dialog con titolo '{anotherDialog['title']}' e testo '{anotherDialog['text']}')")
						
						if "Close" in anotherDialog["buttons"]:
							logger.warning("Trovato pulsante 'Close'. Chiudo il dialog...")
							anotherDialog["buttons"]["Close"].click()
							maximo.waitUntilReady()

						return False

					# Seleziono "Continue anyway"
					browser.find_element(By.ID, "mc1493e00-rb").click()
					anotherDialog["buttons"]["OK"].click()
					maximo.waitUntilReady()
					logger.info("Cliccato su 'Continue anyway'. Ora posso procedere normalmente...")
		
					break
				
				else:
					logger.critical(f"Trovato dialog inatteso di tipo '{foregroundDialog['type']}' con titolo '{foregroundDialog['title']}' e testo '{foregroundDialog['text']}'")
					
					if "Close" in foregroundDialog["buttons"]:
						logger.info("Trovato pulsante 'Close'. Chiudo il dialog...")
						foregroundDialog["buttons"]["Close"].click()
						maximo.waitUntilReady()

					return False

					
				if maximo.driver.find_elements(By.ID, "msgbox-dialog_inner"):
					msg_box_text = maximo.driver.find_element(By.ID, "mb_msg").get_attribute("innerText").strip()

					if "Change SCHEDULED DATE is not reach to start Activity" in msg_box_text:
						btn_close = maximo.driver.find_element(By.ID, "m15f1c9f0-pb")
						btn_close.click()

						maximo.waitUntilReady()
						
						logger.warning(f"Schedule Start not reached. Retrying in 20 seconds... ({cur_retries_impl_inprg} of {max_retries_impl_inprg} MAX)")
						time.sleep(20)
						continue
				

			if browser.find_elements(By.ID, "m15f1c9f0-pb") and "The Approved Scheduled Window has expired" in browser.find_element(By.ID, "mb_msg").get_attribute("innerText"):
				browser.find_element(By.ID, "m15f1c9f0-pb").click()
				maximo.waitUntilReady()
				browser.find_element(By.ID, "mc1493e00-rb").click()
				maximo.waitUntilReady()
				browser.find_element(By.ID, "m37917b04-pb").click()
				maximo.waitUntilReady()

			time.sleep(3)
			new_status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()
	
	status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()
	if status == "INPRG":
		new_status = status
		while new_status == status:
			try:
				while cur_retries_inprg_comp < max_retries_inprg_comp:
					cur_retries_inprg_comp += 1

					maximo.setNamedInput({ "New Status:": "COMP", "Task Completion Code:": "COMPLETE" })

					time.sleep(1.5)

					logger.debug("Clicco sul pulsante 'Route WF' in alto")

					maximo.clickRouteWorkflow()
					time.sleep(3)
					maximo.waitUntilReady()

					foregroundDialog = maximo.getForegroundDialog()

					if not foregroundDialog:
						break

					if "Complete Workflow Assignment" in foregroundDialog["title"]:
						foregroundDialog["buttons"]["OK"].click()
						maximo.waitUntilReady()
						break

					# If change is not yet in INPRG status
					elif "The change is not in status INPRG yet, please wait few seconds then try again." in foregroundDialog["text"]:
						logger.warning(f"Comparso dialog: 'Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}'")

						foregroundDialog["buttons"]["Close"].click()
						maximo.waitUntilReady()

						logger.info(f"Riprovo in 10 secondi ({cur_retries_inprg_comp} tentativi su {max_retries_inprg_comp} MAX)")
						time.sleep(10)

				else:
					logger.error(f"Reached maximum retries number ({max_retries_inprg_comp}) while trying to go from INPRG to COMP")

					return False
			except MaximoWorkflowError as e:
				logger.exception(str(e))
				break
		
			new_status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()

	status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()
	if status == "COMP":
		logger.info(f"Il task è ora in stato 'COMP'\n")
		return True

	logger.error("Il task NON E' ANCORA in stato 'COMP'!")
	logger.exception("Probabilmente qualcosa e' andato storto da qualche parte")

	return False


	## VECCHIA VERSIONE (funzionante btw)
	cur_retries_impl_inprg = 0
	cur_retries_inprg_comp = 0
	while True:
		status = maximo.getNamedInput("Status:").get_attribute('value').strip().upper()

		logger.debug(f"Current status: {status}")
		
		# Interrompe il loop se è riusito a portare il task in stato 'COMP'
		if status == "COMP":
			logger.info(f"Il task è ora in stato 'COMP'\n")
			break
		
		if status == "IMPL":
			maximo.setNamedInput({ 
				"New Status:": "INPRG", 
				"Task Owner:": owner_username 
			})
			
			time.sleep(1)
			

			try:
				cur_retries_impl_inprg += 1
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
						browser.find_element(By.ID, "mc1493e00-rb").click()
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

					if maximo.driver.find_elements(By.ID, "msgbox-dialog_inner"):
						msg_box_text = maximo.driver.find_element(By.ID, "mb_msg").get_attribute("innerText").strip()

						if "Change SCHEDULED DATE is not reach to start Activity" in msg_box_text:
							btn_close = maximo.driver.find_element(By.ID, "m15f1c9f0-pb")
							btn_close.click()

							maximo.waitUntilReady()

							if cur_retries_impl_inprg > max_retries_impl_inprg:
								logger.error(f"Cannot change Task from IMPL to INPRG")
								break

							logger.warning(f"Schedule Start not reached. Retrying in 20 seconds... ({cur_retries_impl_inprg} of {max_retries_impl_inprg} MAX)")
							time.sleep(20)

			except MaximoWorkflowError as e:
				logger.error(f"Route Workflow fallito: comparso dialog 'Change SCHEDULED DATE is not reach to start Activity'")
				logger.error(f"Solitamente questo e' dovuto ad una data di Target Start FUTURA. Controllare le date in cui e' stato schedulato il change")
				break

			except Exception as e:
				logger.exception(f"Errore in fase di cambio IMPL -> INPRG")
				break

			if browser.find_elements(By.ID, "m15f1c9f0-pb") and "The Approved Scheduled Window has expired" in browser.find_element(By.ID, "mb_msg").get_attribute("innerText"):
				browser.find_element(By.ID, "m15f1c9f0-pb").click()
				maximo.waitUntilReady()
				browser.find_element(By.ID, "mc1493e00-rb").click()
				maximo.waitUntilReady()
				browser.find_element(By.ID, "m37917b04-pb").click()
				maximo.waitUntilReady()

			time.sleep(3)

		elif status == "INPRG":
			try:
				while cur_retries_inprg_comp < max_retries_inprg_comp:
					cur_retries_inprg_comp += 1

					maximo.setNamedInput({ "New Status:": "COMP", "Task Completion Code:": "COMPLETE" })

					time.sleep(1.5)

					logger.debug("Clicco sul pulsante 'Route WF' in alto")

					maximo.clickRouteWorkflow()
					time.sleep(3)
					maximo.waitUntilReady()

					foregroundDialog = maximo.getForegroundDialog()
					# print(f"INPRG -> COMP: {foregroundDialog}")


					if not foregroundDialog:
						break

					if "Complete Workflow Assignment" in foregroundDialog["title"]:
						foregroundDialog["buttons"]["OK"].click()
						maximo.waitUntilReady()
						break

					# If change is not yet in INPRG status
					elif "The change is not in status INPRG yet, please wait few seconds then try again." in foregroundDialog["text"]:
						logger.warning(f"Comparso dialog: 'Cannot change Task from IMPL to INPRG: {foregroundDialog['text']}'")

						foregroundDialog["buttons"]["Close"].click()
						maximo.waitUntilReady()

						logger.info(f"Riprovo in 10 secondi ({cur_retries_inprg_comp} tentativi su {max_retries_inprg_comp} MAX)")
						time.sleep(10)

				else:
					logger.error(f"Reached maximum retries number ({max_retries_inprg_comp}) while trying to go from INPRG to COMP")

					break
			except MaximoWorkflowError as e:
				logger.exception(str(e))
				break
			
		else:
			logger.error(f"Status {status} not handled by the script!\n")

			break

		logger.debug(f"Finished current status cycle... Getting next status")


def closeAllReview(verbose=False, show_browser=False):
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

			maximo.waitUntilReady()
			maximo.routeWorkflowDialog.closeDialog()

			logger.info(f"CHIUSO change: {change} (" + str(index + 1) + " of " + str(len(CHANGES)) + ")\n")
			change_closed += 1


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		logger.critical("Generic error during the script execution...")
		logger.exception(e)

		# logger_mgc.debug("Starting Python debugger...")
		# pdb.set_trace()
		
	except MaximoLoginFailed as e:
		logger.critical(f"Couldn't login... Check the credentials stored in file `maximo_credentials.json`! {str(e)}")

	finally:
		rich.print(rich.panel.Panel(rich.align.Align(f"Sono stati portati in CLOSE {change_closed}/{len(CHANGES)} change", align="center"), title="Risultati", padding=2))
		
		print()

		if maximo.debug: input ("Premi INVIO per continuare")


		# Per evitare che se il programma dumpa troppo presto cerca di chiudere un oggetto non ancora instanziato
		try:
			maximo.close()
		except NameError as e:
			pass
		
		print()
		input("Premi INVIO per terminare il programma...")


def getAllOpen (verbose=False, show_browser=False):
	# Get credentials
	CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
	CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

	# Get credentials
	USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

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
	
		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Changes")

		# Search ONLY the open Changes...
		maximo.advancedSearch({ 
			"Status:": "=ACC_CAT,=IMPL,=INPRG,=INPROG", 
			"Is Task?": "N", 
			"Customer:": "=WTI-00" 
		})

		maximo.setFilters({"Owner Group": "=V-OST-IT-SYO-OPS-TRENITALIA_ICTSM%"})

		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()

		logger.info(f"Trovati {len(records)} change aperti con 'Owner Group' == 'V-OST-IT-SYO-OPS-TRENITALIA_ICTSM%'\n")

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