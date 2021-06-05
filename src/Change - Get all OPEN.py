from updateutils import checkUpdated

import change

import argparse

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Chiude tutti i change trovati in stato "REVIEW".')
	parser.add_argument('-X', '--show_browser', dest='show_browser', action='store_true',
						help="Mostra l'interfaccia grafica di Maximo.")
	parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
						help="Aumenta la verbosita' dell'output.")

	args = parser.parse_args()

	checkUpdated(__file__)
	# checkUpdated("Change - IMPL to REVIEW.py")

	change.getAllOpen()