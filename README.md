<p align="center">
	<h1 align="center">Maximo Automation for ICTSM Team</h1>
	<p align="center">
		<strong><i>- "Not your regular monkey" -</i></strong>
	</p>
</p>

## Elenco contenuti
- [Elenco contenuti](#elenco-contenuti)
- [:light_rail: Introduzione :bullettrain_side:](#-introduzione-)
- [Elenco Automazioni](#elenco-automazioni)
	- [Chiusura change in REVIEW](#chiusura-change-in-review)
	- [Portare change da IMPL/INPRG a REVIEW](#portare-change-da-implinprg-a-review)
- [Compilazione degli script](#compilazione-degli-script)
		- [Istruzioni](#istruzioni)

## :light_rail: Introduzione :bullettrain_side:
Questo progetto mira all'automatizzazione di specifiche procedure del **Team ICTSM Trenitalia**, in modo da velocizzarne l'esecuzione.

Il core è formato da una [libreria in Python](https://github.com/LukeSavefrogs/maximo-gui-connector) di mia creazione e ogni script crea un file di log con lo stesso nome in cui vengono salvate informazioni utili.

Per utilizzare gli script è **OBBLIGATORIO** salvare nella **stessa cartella** un file chiamato `maximo_credentials.json` con al suo interno le **credenziali** di Maximo secondo il seguente schema:
```json
{
	"USERNAME": "",
	"PASSWORD": ""
}
```

## Elenco Automazioni
Di seguito un elenco delle automazioni disponibili al momento...

### Chiusura change in REVIEW
:eyes:

### Portare change da IMPL/INPRG a REVIEW
:eyes:

## Compilazione degli script
La compilazione degli script è gestita a sua volta da [uno script](./startDeploy.py) che ha il duplice scopo di compilare e aggiornare la versione degli script.

#### Istruzioni
Usare lo script **`startDeploy.py`** passando come parametri i nomi dei file senza estensione:
```bash
python ./startDeploy.py 'Change - IMPL to REVIEW' 'Change - Close all REVIEW'
```

Se invece non vengono specificati dei file come parametri, verranno compilati di **default**:
- [Change - IMPL to REVIEW](./src/Change%20-%20IMPL%20to%20REVIEW.py)
- [Change - Close all REVIEW](./src/Change%20-%20Close%20all%20REVIEW.py)
  

![Script per compilazione](images/b26221ab3ec3295d09b691ac5a0651dc9fe1450ab36a6892afd448be6e3e165d.png)