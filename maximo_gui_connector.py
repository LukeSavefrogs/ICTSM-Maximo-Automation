import selenium
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import re
import logging
from selenium.webdriver.remote.remote_connection import LOGGER


# Just for Debug
import json

class MaximoAutomation():
	"""
		Abstraction layer over IBM Maximo Asset Management UI
	"""

	debug = False
	headless = False

	sections_cache = {}
	
	def __init__(self, config = {}):
		chrome_flags = []

		if "debug" in config:
			self.debug = bool(config["debug"])
			if self.debug: print("[DEBUG] - Debug mode enabled")
		
		if "headless" in config:
			self.headless = bool(config["debug"])
			if self.headless: chrome_flags.append("--headless")

		chrome_flags = chrome_flags + [
			# "--disable-extensions",
			"start-maximized",
			"--disable-gpu",
			"--ignore-certificate-errors",
			"--ignore-ssl-errors",
			#"--no-sandbox # linux only,
			# "--headless",
		]
		chrome_options = Options()
			
		for flag in chrome_flags:
			chrome_options.add_argument(flag)

		# LOGGER.setLevel(logging.WARNING)

		self.driver = webdriver.Chrome( options=chrome_options )
		self.driver.get("https://ism.italycsc.com/UI/maximo/webclient/login/login.jsp?appservauth=true")

		


	
	def login (self, username, password):
		"""Logs the user into Maximo, using the provided credentials"""
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "j_username")))

		self.driver.find_element_by_id("j_username").send_keys(username)
		self.driver.find_element_by_id("j_password").send_keys(password)

		if self.debug: print(f"[DEBUG] - Username/Password were sent to the login Form (using {username})")

		self.driver.find_element_by_css_selector("button#loginbutton").click()
		if self.debug: print("[DEBUG] - Clicked on Submit button")
		
		# Wait until Maximo has finished logging in
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "titlebar_hyperlink_9-lbsignout")))
		self.waitUntilReady()

		if self.debug: print("[DEBUG] - User successfully logged in")


	def logout (self):
		""" Performs the logout """
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "titlebar_hyperlink_9-lbsignout")))
		self.driver.find_element_by_id("titlebar_hyperlink_9-lbsignout").click()
		if self.debug: print("[DEBUG] - Clicked on the logout button")
		
		# Wait until have finished logging out and the confirm button is present
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#returnFrm > button#submit")))

		# Click on the Submit button 
		self.driver.find_element_by_id("submit").click()

		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "j_username")))
		if self.debug: print("[DEBUG] - User successfully logged out")


	def close (self):
		""" Closes the Browser instance """
		self.driver.quit()


	def isReady(self):
		""" Returns whether or not Maximo is ready to be automated """
		js_result = self.driver.execute_script("return waitOn == false && !document.getElementById('m935819a1-longop_message');")

		if self.debug: print ("Ready: ", str(js_result))
		return bool(js_result)

	def waitUntilReady (self):
		""" Stops the execution of the script until Maximo is ready """
		WebDriverWait(self.driver, 30).until(EC.invisibility_of_element((By.ID, "wait")))
		

	def goto_section (self, section_name):
		""" Goes to the one of the sections you can find under the GoTo Menu in Maximo (Ex. changes, problems...) """
		self.driver.find_element_by_id("titlebar-tb_gotoButton").click()
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#menu0_changeapp_startcntr_a")))
		
		""" Populate the cache ONLY the first time, so that it speeds up on the next calls """
		if len(self.sections_cache) == 0:
			if self.debug: print("[DEBUG] - Sections cache is empty. Analyzing DOM...")

			for section in self.driver.find_elements_by_css_selector("#menu0 li:not(.submenu) > a"): 
				text = section.get_attribute("innerText")
				text = re.sub(r'\(MP\)', '', text)
				text = re.sub(r'\s+', ' ', text).strip().lower()
				s_id = section.get_attribute("id") 
				self.sections_cache[text] = f"#{s_id}"

		if self.debug:
			print("[DEBUG] - Pretty printing sections cached:")
			print(json.dumps(self.sections_cache, sort_keys=True, indent=4))

		section_name_parsed = section_name.lower().replace("(MP)", "")
		if section_name_parsed in self.sections_cache:
			section_element = self.driver.find_element_by_css_selector(self.sections_cache[section_name_parsed])
			self.driver.execute_script("arguments[0].click();", section_element)
			if self.debug: print("[DEBUG] - Clicked on " + section_name)

		else:
			raise Exception(f"[ERROR] - Section '{section_name}' does not exist. The following were found:\n" + json.dumps(self.sections_cache, sort_keys=True, indent=4))

		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "quicksearch")))
		self.waitUntilReady()

	def getAvailableFiltersInListView (self):
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "m6a7dfd2f_tbod_ttrow-tr")))
		
		filters_found = {}
		
		for label in self.driver.find_elements_by_css_selector('#m6a7dfd2f_tbod_ttrow-tr th > span'):
			filter_label = label.get_attribute("innerText").strip().lower()

			if filter_label == "": continue

			cell = label.find_element_by_xpath('..')

			filter_sort = cell.find_element_by_css_selector("img").get_attribute("alt")

			filter_label_id = cell.get_attribute("id")
			filter_id = ""
			filter_column_number = self.getColumnFromFieldId(filter_label_id)

			try:
				filter_id = self.driver.find_element_by_css_selector("[headers='" + filter_label_id + "'] > input").get_attribute("id")
			except Exception as identifier:
				print("Errore - Nome colonna: " + filter_label + "\n" + str(identifier))

			filters_found[filter_label] = { "element_id": filter_id, "sorting": filter_sort, "column_number": filter_column_number }


		if self.debug: print("[DEBUG] - Pretty printing filters found:\n" + json.dumps(filters_found, sort_keys=True, indent=4))

		return filters_found


	def setFilters (self, filter_config):
		""" Change filters for the change list """
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "m6a7dfd2f_tbod_ttrow-tr")))
		
		filters_cache = self.getAvailableFiltersInListView()


		element = self.driver.find_element_by_id('m6a7dfd2f-ti_img')
		filters_enabled = element.get_attribute("src") != "tablebtn_filter_off.gif"

		if not filters_enabled:
			apri_filters = self.driver.find_element_by_id("m6a7dfd2f-lb2")
			ActionChains(self.driver).move_to_element(apri_filters).click(apri_filters).perform()

		
		for filter_name, filter_value in filter_config.items():
			if not filter_name.lower() in filters_cache:
				print (f"[WARNING] - Filter name '{filter_name}' does not exist. The following filters were found:\n" + json.dumps(filters_cache, sort_keys=True, indent=4))
				continue
			if filters_cache[filter_name.lower()]["element_id"].strip() == "":
				print (f"[WARNING] - Filter name '{filter_name}' is not editable:")
				continue


			self.driver.find_element_by_css_selector("[id='" + filters_cache[filter_name.lower()]["element_id"] + "']").send_keys(filter_value)
			if self.debug: print(f"[DEBUG] - Filter '{filter_name}' was correctly set with value '{filter_value}'")
			

		self.driver.find_element_by_id("m6a7dfd2f-ti2_img").click()
		self.waitUntilReady()


	def quickSearch(self, id):
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "quicksearch")))
		self.driver.find_element_by_id("quicksearch").send_keys(id.strip())
		
		self.driver.find_element_by_id("quicksearchQSImage").click()

		if self.debug: print(f"[DEBUG] - Searching for id: {id}")
		
		self.waitUntilReady()
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "m397b0593-tabs_middle")))


	def getBrowserInstance(self):
		"""
			Returns the Selenium Webdriver instance needed to perform operations in the current 
		"""
		return self.driver
	

	def getColumnFromFieldId(self, id):
		regex_result = re.search("\[C:([0-9]+)\]", id)
		if regex_result: 
			return regex_result.groups(1)[0].strip()
		else:
			return None
		pass

	def getRecordDetailsFromTable (self, record: selenium.webdriver.remote.webelement.WebElement, filters):
		"""
			When inside a Section with a Table list (ex. when inside the list of Changes open owned by my groups)
				returns

		Args:
			required_fields (list, optional): [description]. Defaults to [].
		"""
		current_row = {}
		for column in record.find_elements_by_tag_name("td"):
			field = {
				"element_id": column.get_attribute("id").strip(),
				"value": column.text.replace("\n", "").strip(),
				"column_number": self.getColumnFromFieldId(column.get_attribute("id")),
				"filter_type": ""
			}



			# Find the filter column name associated to the current field
			for key, values in filters.items():
				if values["column_number"] == field['column_number']:
					field['filter_type'] = key.strip()
					break

			# Add the current field to the list of fields ONLY if it has both a valid column name and a valid value
			if field['filter_type'] != "" and field['value'] != "":
				current_row[field['filter_type']] = field
			
		# if self.debug: print("Dettagli record:\n" + json.dumps(current_row, indent=4))

		return current_row


	def getAllRecordsFromTable (self, start=0, end=-1):
		table_rows = self.driver.find_elements_by_css_selector("#m6a7dfd2f_tbod-tbd tr.tablerow[id*='tbod_tdrow-tr[R:']")

		if self.debug: print("[DEBUG] - Total table rows: " + str(len(table_rows)))

		filters = self.getAvailableFiltersInListView()

		record_list = []

		for index in range(len(table_rows)): 
			record_list.append(
				{
					"data": self.getRecordDetailsFromTable(table_rows[index], filters),
					"element_id": table_rows[index].get_attribute("id")
				}
			)

		if self.debug: print("Dettagli record:\n" + json.dumps(record_list, indent=4))

		return record_list