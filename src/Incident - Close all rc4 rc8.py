from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from maximo_gui_connector import MaximoAutomation
from maximo_gui_connector import MaximoWorkflowError
import json
import time
import re
import logging

def getCredentials ():	
	"""
	Gets the credentials from a local json

	Returns:
		tuple: contains USERNAME and PASSWORD
	"""
	with open('maximo_credentials_for_L1.json') as f:
		data = json.load(f)

	return (data["USERNAME"], data["PASSWORD"])


if __name__ == "__main__":
	try:
		# Get credentials
		USERNAME, PASSWORD = getCredentials()

		maximo = MaximoAutomation({ "debug": False, "headless": False })
		maximo.login(USERNAME, PASSWORD)

		log_incident_chiusi = logging.getLogger("INC_AUTO_CLOSE")
		log_incident_chiusi.setLevel(logging.INFO)
		
		log_incident_chiusi_handler = logging.FileHandler(filename='Incident RC4-8 closed.log')
		log_incident_chiusi_handler.setFormatter(logging.Formatter(fmt='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S'))

		log_incident_chiusi.addHandler(log_incident_chiusi_handler)


		browser = maximo.driver
	
		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Incidents")
		
		browser.find_element_by_xpath("//span[normalize-space(text()) = 'Incidents open owned by my Groups']/parent::a").click()
		
		# Setup the filters to get ONLY the Changes owned by our group...
		maximo.setFilters({ "summary": "client backup failed for node", "owner group": "V-OST-IT-SYO-OPS-TSM_TRENITALIA_L1" })
		# raise EnvironmentError()
		
		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()


		incidents = [ record["data"]["incident"]["value"] for record in records ]



		for index, incident in enumerate(incidents):
			maximo.quickSearch(incident)
			
			# Change to the "Details & Closure" page
			maximo.goto_tab("Incident")

			inc_details = maximo.getNamedInput("Details:").get_attribute("value")
			inc_summary = maximo.getNamedInput("Summary:").get_attribute("value")

			backup_info = {}

			rc_valid = bool(re.match(r"Summary:.*Failed\s*[48]\.", inc_details.split("\n")[0]))
			if not rc_valid:
				maximo.logger.warning(f"Skippato incident con Failed diverso da 4 o 8: {incident} (" + str(index + 1) + " of " + str(len(incidents)) + ")\n")
				continue

			backup_info["hostname"], backup_info["id"], backup_info["rc"] = re.search(r"client backup failed for node: (.*?) and schedule: (.*?). Status: Failed\s*([0-9]+)", inc_details.split("\n")[0]).groups()


			if not "BKP_INCR" in backup_info["id"] and not "BKP_VM" in backup_info["id"]:
				maximo.logger.warning(f"Skippato incident non BKP_INCR/BKP_VM: {incident} (" + str(index + 1) + " of " + str(len(incidents)) + ")\n")
				continue


			resolution = f"Backup {backup_info['id']} failed for host {backup_info['hostname']} with Return Code {backup_info['rc']}. Cause: file tmp not found"

			maximo.logger.info(f"In corso: {incident} ({ str(index + 1) } of { str(len(incidents)) })")
			maximo.logger.info(f"Resolution: {resolution}\n")
			continue
			current_status = ""
			while current_status != "RESOLVED":
				maximo.goto_tab("Incident")
				current_status = maximo.getNamedInput("Status:").get_attribute("value").upper()

				maximo.logger.info(f"Current status: {current_status}")

				if current_status == "QUEUED":
					try:
						maximo.routeWorkflowDialog.openDialog()
						maximo.setNamedInput({ 
							"New Status:": "INPROG",
							"New Owner Group:": "V-OST-IT-SYO-OPS-TSM_TRENITALIA_L1",
						})
						maximo.routeWorkflowDialog.clickRouteWorkflow()
					except Exception as identifier:
						print(identifier)

				if current_status == "INPROG":
					maximo.goto_tab("Solution Details")
					maximo.setNamedInput({ 
						"Quality:": "RECURRENT",
						"Solution Method:": "ON DUTY",
						"Resolution Code:": "NO ACTION REQUIRED",
						"Resolution:": "CLEAR EVENT BY SCRIPT FOR RC 4 AND 8"
					})

					maximo.goto_tab("Failure Reporting")
					maximo.setNamedInput({ 
						"Failure Class:": "EVENT MGMNT"
					})
					
					maximo.routeWorkflowDialog.openDialog().setStatus("RESOLVED")
					maximo.routeWorkflowDialog.clickRouteWorkflow()

			maximo.logger.info(f"Chiuso incident: {incident} (" + str(index + 1) + " of " + str(len(incidents)) + ")\n")
			log_incident_chiusi.info(f"Incident chiuso correttamente: {incident} ({inc_summary})")


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		maximo.logger.error("Exception occurred", exc_info=True)

	finally:
		input("Premi un tasto per terminare il programma")

		maximo.close()