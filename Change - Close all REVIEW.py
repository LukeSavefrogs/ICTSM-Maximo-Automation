from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import maximo_gui_connector as MGC
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

		maximo = MGC.MaximoAutomation({ "debug": True, "headless": True })
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

			# Click on the "Change Status" button
			browser.find_element_by_link_text("Change Status/Group/Owner (MP)").click()
			maximo.waitUntilReady()

			maximo.waitForInputEditable("#m67b8314e-tb")

			# Set the desired status
			browser.find_element_by_id("m67b8314e-tb").send_keys("CLOSE")
			browser.find_element_by_id("m67b8314e-tb").send_keys(Keys.TAB)
			maximo.waitUntilReady()

			time.sleep(0.5)

			# Click on "Route Workflow" button
			browser.find_element_by_id("m24bf0ed1-pb").click()
			maximo.waitUntilReady()
			
			if browser.find_elements_by_id("m88dbf6ce-pb") and "Errors exist in the application that prevent this action from being performed" in browser.find_element_by_id("mb_msg").get_attribute("innerText"):
				# browser.find_elements_by_id("m88dbf6ce-pb").click()
				break
			
			time.sleep(0.5)

			# Click on "Close Window" button to close the dialog
			browser.find_element_by_id("mbdb65f6b-pb").click()
			maximo.waitUntilReady()

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