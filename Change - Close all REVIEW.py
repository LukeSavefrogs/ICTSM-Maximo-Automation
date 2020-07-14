from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from maximo_gui_connector import MaximoAutomation
from maximo_gui_connector import MaximoWorkflowError
import json
import time

def getCredentials ():	
	"""
	Gets the credentials from a local json

	Returns:
		tuple: contains USERNAME and PASSWORD
	"""
	with open('maximo_credentials.json') as f:
		data = json.load(f)

	return (data["USERNAME"], data["PASSWORD"])


if __name__ == "__main__":
	try:
		# Get credentials
		USERNAME, PASSWORD = getCredentials()

		maximo = MaximoAutomation({ "debug": True, "headless": False })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver
	
		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Changes")

		# Setup the filters to get ONLY the Changes owned by our group...
		maximo.setFilters({ "status": "=REVIEW", "owner group": "V-OST-IT-SYO-OPS-TRENITALIA_ICTSM" })

		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()


		changes = [ record["data"]["change"]["value"] for record in records ]

		for index, change in enumerate(changes):
			maximo.quickSearch(change)
			
			# Change to the "Details & Closure" page
			browser.find_element_by_link_text("Details & Closure").click()
			maximo.waitUntilReady()

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
				print("Error while clicking on the 'Route Workflow' button:\n" + exception)

				continue


			time.sleep(0.5)

			maximo.routeWorkflowDialog.closeDialog()

			print(f"[INFO] - Chiuso change: {change} (" + str(index + 1) + " of " + str(len(changes)) + ")\n")
			# break


		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print()
		input("Premi un tasto per terminare il programma")

		maximo.close()