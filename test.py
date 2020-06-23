import maximo_gui_connector as MGC
import json

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

		maximo.goto_section("Activities and Tasks")
		
		# maximo.quickSearch("CH1665157")

		maximo.setFilters({ "Change Num.": "CH1669684" })

		maximo.getAllRecordsFromTable()
		# maximo.setFilters({ "status": "!=REVIEW", "owner group": "V-OST-IT-SYO-OPS-TRENITALIA_ICTSM" })
		
		if maximo.debug: input("Premi per eseguire il logout")

		maximo.logout()
	
	except Exception as e:
		print(e)

	finally:
		print()
		input("Premi un tasto per terminare il programma")

		maximo.close()