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

		maximo = MGC.MaximoAutomation({ "debug": True, "headless": True })
		maximo.login(USERNAME, PASSWORD)

		browser = maximo.driver
		changes = [
			"CH1678913",
			"CH1678915",
			"CH1678919",
			"CH1678917",
			"CH1678910",
			"CH1678906",
			"CH1678900",
			"CH1678794",
			"CH1678800",
			"CH1678786",
		]

		INPRG_MAX_RETRIES = 5


		# Here we are into the Home Page.
		# We need to go to the Changes section...
		maximo.goto_section("Activities and Tasks")

		for index, change in enumerate(changes):
			print("[INFO] - Current change: {change} ({partial} of {total})".format(change=change, partial=index+1, total=len(changes)))

			browser.find_element_by_id("quicksearchQSMenuImage").click()
			maximo.waitUntilReady()

			browser.find_element_by_id("menu0_SEARCHMORE_OPTION_a_tnode").click()
			maximo.waitUntilReady()

			time.sleep(1.5)


			# Set Change number as Parent 
			browser.find_element_by_id("m716fdd63-tb").clear()
			browser.find_element_by_id("m716fdd63-tb").send_keys(change.strip())
			browser.find_element_by_id("m716fdd63-tb").send_keys(Keys.TAB)
			maximo.waitUntilReady()

			# Find with the provided filters
			browser.find_element_by_id("maa8a5ebf-pb").click()
			maximo.waitUntilReady()

			# If change was already CLOSED (not REVIEW)
			if browser.find_elements_by_id("m88dbf6ce-pb") and "No records were found that match the specified query" in browser.find_element_by_id("mb_msg").get_attribute("innerText"):
				print(f"[WARNING] - Parent Change {change} is in CLOSED status (not open Tasks found)\n")

				browser.find_element_by_id("m88dbf6ce-pb").click()
				maximo.waitUntilReady()

				continue

			if not browser.find_elements_by_id("m714e5172-tb"):
				tasks = maximo.getAllRecordsFromTable()

				print("[ERROR] - Found {n_tasks} tasks in total. The script, as of now, only accepts changes with a single task. Skipping...\n".format(n_tasks=len(tasks)))
				continue

			status = browser.find_element_by_id("m714e5172-tb").get_attribute('value').upper()
			if status == "COMP":
				print(f"[WARNING] - Task for change {change} is already in COMP status\n")

				continue
					
			while True:
				status = browser.find_element_by_id("m714e5172-tb").get_attribute('value').upper()

				print(f"[INFO] - \tCurrent status: {status}")
				
				if status == "IMPL":
					browser.find_element_by_id("mde239204-tb").clear()
					browser.find_element_by_id("mde239204-tb").send_keys("INPRG")
					browser.find_element_by_id("mde239204-tb").send_keys(Keys.TAB)
					maximo.waitUntilReady()
					
					time.sleep(1)

					browser.find_element_by_id("m944e29a9-tb").clear()
					browser.find_element_by_id("m944e29a9-tb").send_keys(USERNAME)
					browser.find_element_by_id("m944e29a9-tb").send_keys(Keys.TAB)
					maximo.waitUntilReady()

					time.sleep(1)

					maximo.clickRouteWorkflow()

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

					while retryTimes < INPRG_MAX_RETRIES:
						retryTimes += 1

						browser.find_element_by_id("mde239204-tb").clear()
						browser.find_element_by_id("mde239204-tb").send_keys("COMP")
						browser.find_element_by_id("mde239204-tb").send_keys(Keys.TAB)
						maximo.waitUntilReady()

						maximo.waitForInputEditable("#mc9f23617-tb")

						browser.find_element_by_id("mc9f23617-tb").clear()
						browser.find_element_by_id("mc9f23617-tb").send_keys("COMPLETE")
						browser.find_element_by_id("mc9f23617-tb").send_keys(Keys.TAB)
						maximo.waitUntilReady()

						time.sleep(1.5)

						if maximo.debug: print("[DEBUG] - \tClicking on Route WF")

						maximo.clickRouteWorkflow()

						time.sleep(3)

						# If change is not yet in INPRG status
						if browser.find_elements_by_id("m15f1c9f0-pb"):
							if maximo.debug: print(f"[DEBUG] - \tTask is not yet in INPRG status: retrying in 10 seconds ({retryTimes} attempt of {INPRG_MAX_RETRIES} MAX)")

							browser.find_element_by_id("m15f1c9f0-pb").click()
							time.sleep(10)

							continue

						break
					else:
						print(f"[ERROR] - \tReached maximum retries number ({INPRG_MAX_RETRIES}) while trying to go from INPRG to COMP")

						break
				elif status == "COMP":
					print(f"[INFO] - \tTask for change {change} is in COMP status\n")
					
					break
				else:
					print(f"[ERROR] - \tStatus {status} not handled by the script!\n")

					break

				if maximo.debug: print(f"[DEBUG] - \tFinished current status cycle... Getting next status")

		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print()
		input("Premi un tasto per terminare il programma")

		maximo.close()