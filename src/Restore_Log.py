import shutil
import os
from tempfile import gettempdir
import uuid
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from maximo_gui_connector import MaximoAutomation
import logging
import time
import os
import json
import subprocess

import shared.utils as utils



def every_downloads_chrome(driver):
	if not driver.current_url.startswith("chrome://downloads"):
		driver.get("chrome://downloads/")

	print("Waiting for Downloads to be ready")
	WebDriverWait(driver, 120, 1).until(
		EC.title_is("Download")
	)
	WebDriverWait(driver, 120, 1).until(
		EC.visibility_of_element_located((By.CSS_SELECTOR, "downloads-manager"))
	)
	print("Waiting for Downloads to be ready")

	# From https://stackoverflow.com/a/60677334/8965861
	return driver.execute_script("""
		return document.querySelector('downloads-manager')
			.shadowRoot.querySelector('#downloadsList')
			.items.filter(e => e.state === 'COMPLETE')
			.map(e => e.filePath || e.file_path || e.fileUrl || e.file_url);

		""")


def wait_for_downloads(driver, file_download_path, headless=False, num_files=1):
	max_delay = 60
	interval_delay = 0.5
	if headless:
		total_delay = 0
		done = False
		return_files = []
		while not done and total_delay < max_delay:
			files = os.listdir(file_download_path)

			# Remove system files if present: Mac adds the .DS_Store file
			if '.DS_Store' in files:
				files.remove('.DS_Store')
			if len(files) == num_files and not [f for f in files if f.endswith('.crdownload') or f.endswith('.tmp')]:
				done = True
			else:
				total_delay += interval_delay
				time.sleep(interval_delay)

		if not done:
			logging.error("File(s) couldn't be downloaded")
		
		logger.debug(f"Files finished downloading in {file_download_path}: " + ",".join(os.listdir(file_download_path)))
		return os.listdir(file_download_path)
	else:
		def all_downloads_completed(driver, num_files):
			return driver.execute_script("""
				var items = document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList').items;
				var i;
				var done = false;
				var count = 0;
				for (i = 0; i < items.length; i++) {
					if (items[i].state === 'COMPLETE') {count++;}
				}
				if (count === %d) {done = true;}
				return done;
				""" % (num_files))

		driver.execute_script("window.open();")
		driver.switch_to_window(driver.window_handles[1])
		driver.get('chrome://downloads/')
		# Wait for downloads to complete
		WebDriverWait(driver, max_delay, interval_delay).until(lambda d: all_downloads_completed(d, num_files))

		files = driver.execute_script("""
			return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList').items.map(item => item.fileName)
		""")

		# Clear all downloads from chrome://downloads/
		driver.execute_script("""
			document.querySelector('downloads-manager').shadowRoot
			.querySelector('#toolbar').shadowRoot
			.querySelector('#moreActionsMenu')
			.querySelector('button.clear-all').click()
			""")
		driver.close()
		driver.switch_to_window(driver.window_handles[0])

		logger.debug(f"Files finished downloading in {file_download_path}: " + ",".join(files))
		return files


def downloadRestoreTemplate(CHANGE_NUM):
	try:
		CREDENTIALS_MANAGER = utils.Credentials(product_name="Maximo")
		CRED_OBJ = CREDENTIALS_MANAGER.getCredentials()["data"]

		USERNAME, PASSWORD = CRED_OBJ["USERNAME"], CRED_OBJ["PASSWORD"]

		EXECUTE_HEADLESS = True

		TEMP_DIR = gettempdir()
		
		DOWNLOAD_DIR = os.path.join(TEMP_DIR, f"Restore_Log-{uuid.uuid4().hex}")
		FINAL_DIR = os.path.join(TEMP_DIR, f"Restore_Log-Final")
		os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # succeeds even if directory exists.
		shutil.rmtree(FINAL_DIR, ignore_errors=True)
		os.makedirs(FINAL_DIR, exist_ok=True)  # succeeds even if directory exists.

		# To remove '[WDM]' logs (https://github.com/SergeyPirogov/webdriver_manager#configuration)
		os.environ['WDM_LOG_LEVEL'] = '0'
		os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

		chrome_options = webdriver.ChromeOptions()
		preference = {'download.default_directory': DOWNLOAD_DIR, "safebrowsing.enabled": "false"}
		chrome_options.add_experimental_option('prefs', preference)
		chrome_flags = [
			"--disable-extensions",
			"--start-minimized",
			"--disable-gpu",
			"--ignore-certificate-errors",
			"--ignore-ssl-errors",
			"--log-level=3",
			#"--no-sandbox # linux only,
			# ,
		]

		if EXECUTE_HEADLESS: chrome_flags.append("--headless")
			
		for flag in chrome_flags:
			chrome_options.add_argument(flag)

		driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
		# driver.set_window_position(-10000,0)
		# driver.minimize_window()
		# driver.set_window_size(0,0)

		maximo = MaximoAutomation(config={ 
			"debug": False, 
			"driver": driver
		})
		browser = maximo.getBrowserInstance()

		
		maximo.login(USERNAME, PASSWORD)

		maximo.goto_section("Activities and Tasks")

		browser.find_element_by_id("quicksearchQSMenuImage").click()
		maximo.waitUntilReady()

		browser.find_element_by_id("menu0_SEARCHMORE_OPTION_a_tnode").click()
		maximo.waitUntilReady()

		time.sleep(1.5)


		maximo.setNamedInput({ "Parent:": CHANGE_NUM.strip() })

		# Find with the provided filters
		browser.find_element_by_id("maa8a5ebf-pb").click()
		maximo.waitUntilReady()

		# If change was already CLOSED (not REVIEW)
		if browser.find_elements_by_id("m88dbf6ce-pb") and "No records were found that match the specified query" in browser.find_element_by_id("mb_msg").get_attribute("innerText"):
			logger.info(f"Parent Change {CHANGE_NUM} is already in CLOSED status (not open Tasks found)\n")

			browser.find_element_by_id("m88dbf6ce-pb").click()
			maximo.waitUntilReady()

			sys.exit()

		if not browser.find_elements_by_id("m714e5172-tb"):
			tasks = maximo.getAllRecordsFromTable()

			logger.error("Found {n_tasks} tasks in total. The script, as of now, only accepts changes with a single task. Skipping...\n".format(n_tasks=len(tasks)))
			sys.exit()


		status = maximo.getNamedInput("Status:").get_attribute('value').upper()
		if status == "COMP":
			logger.info(f"Task for change {CHANGE_NUM} is already in COMP status\n")

			sys.exit()

		maximo.getNamedLabel("Attachments").click()
		maximo.waitUntilReady()
		
		attachments = browser.find_elements_by_css_selector("[id^='mcaebe976_tdrow_[C:0]_ttxt-lb[R:']")
		files_count = len(attachments)

		logger.info(f"Found {files_count} attachments")

		for attachment in attachments:
			attachment.click()
			maximo.waitUntilReady()

		wait_for_downloads(browser, DOWNLOAD_DIR, EXECUTE_HEADLESS, files_count)
		downloads = os.listdir(DOWNLOAD_DIR)

		new_download_list = []
		for file in downloads:
			OLD_FILE = os.path.join(DOWNLOAD_DIR, file)
			NEW_FILE = os.path.join(FINAL_DIR, file)

			# print(f"Moving {OLD_FILE} to {NEW_FILE}")

			os.replace(OLD_FILE, NEW_FILE)

			new_download_list.append(NEW_FILE)

		os.rmdir(DOWNLOAD_DIR)
		shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)

		logger.info("Files Downloaded: {files}".format(files=", ".join(new_download_list)))

		maximo.logout()
		maximo.close()

		return new_download_list
	except Exception as e:
		logger.exception(e)

		input()
		maximo.close()
		return []




logger = logging.getLogger(__name__)
if __name__ == "__main__":
	CHANGE_NUM = "CH1792330"


	try:
		logger.setLevel(logging.DEBUG)

		logger_consoleHandler = logging.StreamHandler(sys.stdout)
		logger_consoleHandler.setFormatter(logging.Formatter(fmt='[%(levelname)s] - %(message)s'))
		logger.addHandler(logger_consoleHandler)

		downloaded_files = downloadRestoreTemplate(CHANGE_NUM)

		if len(downloaded_files) == 0:
			logger.error("Deve essere scaricato SOLO un file. Nessuno trovato")

			sys.exit(1)
		elif len(downloaded_files) != 1:
			logger.error("Deve essere scaricato SOLO un file. File trovati: {files}".format(files=", ".join(downloaded_files)))
			
			sys.exit(2)

		for fileName in downloaded_files: os.startfile(fileName) #subprocess.run(['open', fileName], check=True)

	except Exception as e:
		logger.exception(e)

		input()