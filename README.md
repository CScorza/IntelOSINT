# <img width="1362" height="353" alt="IntelOSINT Banner" src="https://github.com/user-attachments/assets/6727f5ad-829f-4dc2-908b-a5c5ca59301a"/>

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Active-success)
![Framework](https://img.shields.io/badge/Type-OSINT%20Platform-0f172a)

IntelOSINT e un framework OSINT all-in-one per investigazioni digitali con interfaccia web e workflow multi-tab.  
IntelOSINT is an all-in-one OSINT framework for digital investigations with a web dashboard and a multi-tab workflow.

<div align="center">
<img width="1280" height="613" alt="image" src="https://github.com/user-attachments/assets/51c4bba4-7d54-4251-bc8f-318d5289daf8"/>
</div>

## Moduli
### 1) 🌐 Social Scan
- **IT:** Ricerca e correlazione profili social per username o nome reale.  
- **EN:** Search and correlate social profiles by username or real name.
 
<div align="center">
  <img width="1280" height="605" alt="image" src="https://github.com/user-attachments/assets/1363d8d2-ae8b-4e25-bb32-231f884c9d94"/>
</div>

### 2) 📱 Phone Intelligence
- **IT:** Raccolta informazioni tramite bot Telegrma degli utilizzatori delle utenze telefoniche e verifica degli account WhatsApp e Telegram.  
- **EN:** Collecting information from telephone users via Telegram bots and verifying WhatsApp and Telegram accounts
 
<div align="center">
  <img width="2228" height="1169" alt="image" src="https://github.com/user-attachments/assets/8b2531af-efb5-461e-87c3-4e0caaa9d1b8"/>
</div>

### 3) 💰 Financial Investigation
- **IT:** Tracciamento wallet e visualizzazione relazioni.  
- **EN:** Wallet tracking and relationship visualization.
 
<div align="center">
  <img width="3392" height="870" alt="image" src="https://github.com/user-attachments/assets/ec71282b-a93d-4d4e-9eae-b7cc45132a77"/>
</div>

### 4) 🌍 Domain & IP Network
- **IT:** Raccolta dati WHOIS, DNS, porte, reverse DNS e contesto rete IP.  
- **EN:** WHOIS, DNS, port, reverse DNS, and IP network context collection.
 
<div align="center">
  <img width="2217" height="1106" alt="image" src="https://github.com/user-attachments/assets/fc2c700c-d404-4a28-ba0c-7cf6e00e2c08"/>
</div>

### 5) 📬 Gmail OSINT
- **IT:** LookUp Email Google.  
- **EN:** LookUp Email Google.
 
<div align="center">
<img width="2309" height="1122" alt="image" src="https://github.com/user-attachments/assets/f0cf879c-3804-4e52-b293-c57c965902f8"/>
</div>

### 6) 📄 Doc GDrive
- **IT:** Analisi di documenti pubblici Google e relativi metadati.  
- **EN:** Analysis of public Google documents and related metadata.

<div align="center">
  <img width="2052" height="683" alt="image" src="https://github.com/user-attachments/assets/af41895b-877e-43c7-ae15-a8abb95e1db2"/>

</div>

### 7) 🧠 Face Recognition
- **IT:** Confronto facciale con modalità 1:1, 1:tanti e tanti:tanti.  
- **EN:** Face matching in 1:1, 1-to-many, and many-to-many modes.
 
<div align="center">
<img width="2215" height="1100" alt="image" src="https://github.com/user-attachments/assets/029ac15e-0d7f-4e81-bbcf-9b80df85b35b"/>
</div>

### 8) 🎞️ Media Intelligence
- **IT:** Analisi forense di immagini e video con verifica metadati.  
- **EN:** Forensic analysis of images and videos with metadata inspection.
 
<div align="center">
<img width="2262" height="1069" alt="image" src="https://github.com/user-attachments/assets/4ad39cea-6468-4f04-8aba-301dc41018c2"/>
</div>

### 9) 🔍 Web Dork
- **IT:** Ricerche web mirate con filtri per motore e ambito.  
- **EN:** Targeted web searches with engine and scope filters.

<div align="center">
<img width="1889" height="682" alt="image" src="https://github.com/user-attachments/assets/f8e24f77-756c-4ff0-b308-e0d32670d86d"/>
</div>

## 🛠 Istruzioni per l'Installazione
*🇬🇧 Installation Instructions*

Il sistema è progettato per auto-configurarsi (Virtual Environment e dipendenze) al primo avvio.  
*🇬🇧 The system is designed to self-configure (Virtual Environment and dependencies) at first startup.*

### Requisiti
*🇬🇧 Requirements*

* **Python 3.8** o superiore installato.  
* 🇬🇧 Python 3.8 or higher installed.

### Procedura
*🇬🇧 Procedure*

1.  **Clona il repository:**  
    ***Clone the repository:***
    ```bash
    git clone https://github.com/CScorza/IntelOSINT.git
    cd CSCORZA-IntelOSINT
    ```
2.  **Avvia lo script:**  
    ***Run the script:***
    ```bash
    python IntelOSINT.py
    ```
    *Nota: Al primo avvio, il sistema installerà automaticamente i pacchetti necessari (Flask, Playwright, Telethon, ecc.) e configurerà Chromium.*  
    *🇬🇧 Note: On first startup, the system will automatically install required packages (Flask, Playwright, Telethon, etc.) and configure Chromium.*

---

## 🔑 Configurazione API e Autenticazioni
*🇬🇧 API Configuration and Authentication*

Per sbloccare le funzioni avanzate, inserisci le credenziali nella dashboard di login:  
*🇬🇧 To unlock advanced features, enter your credentials in the login dashboard:*

### 1. Telegram (Ricerca Profonda)
*🇬🇧 Telegram (Deep Search)*

* **Ottenimento:** Vai su [my.telegram.org](https://my.telegram.org), crea una "App" e copia `API ID` e `API HASH`.  
* 🇬🇧 How to get it: Go to [my.telegram.org](https://my.telegram.org), create an "App", and copy `API ID` and `API HASH`.
* **Uso:** Inserisci i dati e clicca su "Ricevi OTP" per autenticare la sessione live.  
* 🇬🇧 Usage: Enter the data and click "Receive OTP" to authenticate the live session.

### 2. Instagram (Data Extraction)
*🇬🇧 Instagram (Data Extraction)*

* **Ottenimento:** Accedi a Instagram dal browser -> F12 (Strumenti sviluppatore) -> Application -> Cookies. Copia il valore di `sessionid`.  
* 🇬🇧 How to get it: Log into Instagram from the browser -> F12 (Developer Tools) -> Application -> Cookies. Copy the `sessionid` value.
* **Uso:** Inseriscilo nel campo `sid` per bypassare i blocchi e vedere profili protetti.  
* 🇬🇧 Usage: Enter it in the `sid` field to bypass blocks and view protected profiles.

### 3. Shodan (Analisi Infrastruttura)
*🇬🇧 Shodan (Infrastructure Analysis)*

* **Ottenimento:** Registrati su [shodan.io](https://www.shodan.io/) e copia la tua `API Key`.  
* 🇬🇧 How to get it: Sign up at [shodan.io](https://www.shodan.io/) and copy your `API Key`.
* **Uso:** Permette di visualizzare ISP, organizzazione e vulnerabilità degli IP analizzati.  
* 🇬🇧 Usage: It allows viewing ISP, organization, and vulnerabilities of analyzed IPs.

---

## 📈 Funzioni Speciali
*🇬🇧 Special Features*

<table>
  <thead>
    <tr>
      <th>Funzione</th>
      <th>Descrizione</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2"><strong>Visual Network Graph</strong></td>
      <td>Mappa interattiva delle transazioni crypto o della rete IP di un dominio.</td>
    </tr>
    <tr>
      <td><em>🇬🇧 Interactive map of crypto transactions or a domain's IP network.</em></td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Telegram Crawler</strong></td>
      <td>Esporta la lista partecipanti di gruppi/canali pubblici in formato <strong>CSV</strong>.</td>
    </tr>
    <tr>
      <td><em>🇬🇧 Exports the participant list of public groups/channels in CSV format.</em></td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Email Leak (Holehe)</strong></td>
      <td>Verifica la registrazione di un'email su centinaia di siti (social, dating, ecc.).</td>
    </tr>
    <tr>
      <td><em>🇬🇧 Checks whether an email is registered on hundreds of sites (social, dating, etc.).</em></td>
    </tr>
    <tr>
      <td rowspan="2"><strong>PDF Reporting</strong></td>
      <td>Salva ogni scoperta nella History e genera un report investigativo finale in PDF.</td>
    </tr>
    <tr>
      <td><em>🇬🇧 Saves each finding in History and generates a final investigative PDF report.</em></td>
    </tr>
  </tbody>
</table>


---

## ⚠️ Disclaimer
*🇬🇧 This tool is provided solely for educational and ethical research purposes. The author assumes no responsibility for improper or illegal use of the software. Always respect privacy and platform terms of service.*

*Questo strumento è fornito esclusivamente a scopo educativo e per attività di ricerca etica.*  
*🇬🇧 This tool is provided exclusively for educational and ethical research activities.*

*L'autore non si assume alcuna responsabilità per l'uso improprio o illegale del software.*  
*🇬🇧 The author assumes no responsibility for improper or illegal use of the software.*

*Rispetta sempre la privacy e i termini di servizio delle piattaforme.*  
*🇬🇧 Always respect privacy and platform terms of service.*

---
**Sviluppato da [CScorza](https://github.com/CScorza)**  
*🇬🇧 Developed by [CScorza](https://github.com/CScorza)*

*🇬🇧 ☕ Support the Project/Support*

*IntelOSINT sarà sempre gratuito, perché la conoscenza deve essere accessibile; se questo progetto ti è utile, ricorda che il tempo è oro e il tuo supporto rende possibile continuare a svilupparlo.*

*🇬🇧 IntelOSINT will always be free to use, because knowledge should be accessible; if this project helps you, remember that time is gold and your support makes continued development possible.*


* **BTC**: bc1qfn9kynt7k26eaxk4tc67q2hjuzhfcmutzq2q6a
* **TON**: UQBtLB6m-7q8j9Y81FeccBEjccvl34Ag5tWaUD

**Contatti / Contacts:** cscorzaosint@protonmail.com
