from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import maximo_gui_connector as MGC
import json
import time
import argparse

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

		maximo = MGC.MaximoAutomation({ "debug": False, "headless": True })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver



		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Changes")

		# Setup the filters to get ONLY the Changes owned by our group...
		maximo.setFilters({ "status": "!=REVIEW", "owner group": "V-OST-IT-SYO-OPS-TRENITALIA_ICTSM" })

		# Get all the records in the table (and all the pages available)
		records = maximo.getAllRecordsFromTable()

		# print(json.dumps(records, sort_keys=True, indent=4))

		changes = [ 
			{ 
				"change": record["data"]["change"]["value"],
				"reported date": record["data"]["reported date"]["value"],
				"status": record["data"]["status"]["value"],
				"summary": record["data"]["summary"]["value"],
			} for record in records 
		]

		print(json.dumps(changes, sort_keys=True, indent=4))

		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print()
		input("Premi un tasto per terminare il programma")

		maximo.close()