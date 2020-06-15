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

# Just for Debug
import json

class MaximoAutomation():
	"""
		Abstraction layer over IBM Maximo Asset Management UI
	"""

	debug = False
	
	sections_cache = {}
	
	def __init__(self, config = {}):
		if "debug" in config:
			self.debug = bool(config["debug"])
			if self.debug: print("[DEBUG] - Debug mode enabled")

		chrome_flags = [
			# "--disable-extensions",
			"start-maximized",
			"--disable-gpu",
			"--ignore-certificate-errors",
			"--ignore-ssl-errors",
			#"--no-sandbox # linux only,
			"--headless",
		]


		chrome_options = Options()

		for flag in chrome_flags:
			chrome_options.add_argument(flag)

		self.driver = webdriver.Chrome( options=chrome_options )
		self.driver.get("https://ism.italycsc.com/UI/maximo/webclient/login/login.jsp?appservauth=true")

	
	def login (self, username, password):
		"""Logs the user into Maximo, using the provided credentials"""
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "j_username")))

		self.driver.find_element_by_id("j_username").send_keys(username)
		self.driver.find_element_by_id("j_password").send_keys(password)

		if self.debug: print("[DEBUG] - Username/Password were sent to the login Form")

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


		if section_name.lower().replace("(MP)", "") in self.sections_cache:
			section_element = self.driver.find_element_by_css_selector(self.sections_cache[section_name])
			self.driver.execute_script("arguments[0].click();", section_element)
		else:
			raise Exception(f"[ERROR] - Section '{section_name}' does not exist. The following were found:\n" + json.dumps(self.sections_cache, sort_keys=True, indent=4))

		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "quicksearch")))
		self.waitUntilReady()


	def setFilters (self, filter_config):
		""" Change filters for the change list """
		WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "m6a7dfd2f_tbod_ttrow-tr")))
		
		filters_cache = {}
		
		for label in self.driver.find_elements_by_css_selector('#m6a7dfd2f_tbod_ttrow-tr th > span'):
			filter_label = label.get_attribute("innerText").strip().lower()

			if filter_label == "": continue

			cell = label.find_element_by_xpath('..')

			filter_sort = cell.find_element_by_css_selector("img").get_attribute("alt")

			filter_label_id = cell.get_attribute("id")
			filter_id = self.driver.find_element_by_css_selector("[headers='" + filter_label_id + "'] > input").get_attribute("id")
			filters_cache[filter_label] = { "id": filter_id, "sorting": filter_sort }


		if self.debug:
			print("[DEBUG] - Pretty printing filters found:\n" + json.dumps(filters_cache, sort_keys=True, indent=4))


		element = self.driver.find_element_by_css_selector('[id="m6a7dfd2f_tfrow_[C:3]_txt-tb"]')
		filters_enabled = self.driver.execute_script('return window.getComputedStyle(arguments[0], null).display;', element) != "none"

		if not filters_enabled:
			apri_filters = self.driver.find_element_by_id("m6a7dfd2f-lb2")
			ActionChains(self.driver).move_to_element(apri_filters).click(apri_filters).perform()

		
		for filter_name, filter_value in filter_config.items():
			if not filter_name in filters_cache:
				print (f"[WARNING] - Filter name '{filter_name}' does not exist. The following filters were found:\n" + json.dumps(filters_cache, sort_keys=True, indent=4))
				continue

			self.driver.find_element_by_css_selector("[id='" + filters_cache[filter_name]["id"] + "']").send_keys(filter_value)
			if self.debug: print(f"[DEBUG] - Filter '{filter_name}' was correctly set with value '{filter_value}'")
			

		self.driver.find_element_by_id("m6a7dfd2f-ti2_img").click()
		self.waitUntilReady()
