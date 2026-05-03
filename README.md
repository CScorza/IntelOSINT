<img width="1362" height="353" alt="Immagine1" src="https://github.com/user-attachments/assets/6727f5ad-829f-4dc2-908b-a5c5ca59301a" />

*È un framework avanzato di Cyber Intelligence (OSINT) all-in-one, progettato per investigazioni digitali su social media, numerazioni telefoniche, domini e transazioni crypto.*  
*🇬🇧 It is an advanced all-in-one Cyber Intelligence (OSINT) framework designed for digital investigations across social media, phone numbers, domains, and crypto transactions.*

*Grazie a un'interfaccia web futuristica, permette di correlare dati provenienti da diverse fonti in tempo reale.*  
*🇬🇧 Thanks to a futuristic web interface, it enables real-time correlation of data from multiple sources.*

---
<img width="1287" height="910" alt="image" src="https://github.com/user-attachments/assets/3160c7ec-1715-4375-bad0-d9637aa0262c" />

## 🚀 Funzionalità Principali
*🇬🇧 Main Features*

Il sistema integra quattro moduli investigativi verticali:  
*🇬🇧 The system integrates four vertical investigative modules:*

### 🌐 Social Scan
Ricerca globale per username o nome reale.  
*🇬🇧 Global search by username or real name.*

<div align="center">
  <img width="800" alt="Social Scan" src="https://github.com/user-attachments/assets/d1e63207-a28a-42bd-b329-b6db5cfd7925" />
</div>

---

### 📱 Phone Intelligence
Analisi numeri internazionali con **Telegram Live** (verifica presenza, foto profilo e nome), **TrueCaller** (Funziona solo tramite bot) e **WhatsApp**.  
*🇬🇧 International phone number analysis with Telegram Live (presence check, profile photo, and name), TrueCaller (works only through bot), and WhatsApp.*

<div align="center">
  <img width="800" alt="Phone Intelligence" src="https://github.com/user-attachments/assets/9bde9620-07a9-4e78-9884-3e97ddec07ac" />
</div>

---

### 💰 Financial Investigation
Tracking wallet **BTC, ETH, BSC, Polygon, Solana**.  
*🇬🇧 Wallet tracking for BTC, ETH, BSC, Polygon, Solana.*

Include un **analizzatore grafico di nodi** per flussi di denaro e grafici di bilancio.  
*🇬🇧 Includes a graph-based node analyzer for money flows and balance charts.*

<div align="center">
  <img width="800" alt="Financial Investigation" src="https://github.com/user-attachments/assets/6138876c-5517-4971-843b-96bcd6a11c07" />
</div>

---

### 🌍 Domain & IP Network
Analisi DNS (A, MX, NS, TXT), WHOIS, scansione porte, Reverse DNS e integrazione **Shodan**.  
*🇬🇧 DNS analysis (A, MX, NS, TXT), WHOIS, port scanning, Reverse DNS, and Shodan integration.*

<div align="center">
  <img width="800" alt="Domain & IP Network" src="https://github.com/user-attachments/assets/a43222d8-1f19-4c60-be9e-ff451904f290" />
</div>

---

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

| Funzione | Descrizione |
| :--- | :--- |
| **Visual Network Graph** | Mappa interattiva delle transazioni crypto o della rete IP di un dominio. |
| *Function* | *Description* |
| **Visual Network Graph** | *Interactive map of crypto transactions or a domain's IP network.* |
| **Telegram Crawler** | Esporta la lista partecipanti di gruppi/canali pubblici in formato **CSV**. |
| **Telegram Crawler** | *Exports the participant list of public groups/channels in **CSV** format.* |
| **Email Leak (Holehe)** | Verifica la registrazione di un'email su centinaia di siti (social, dating, ecc.). |
| **Email Leak (Holehe)** | *Checks whether an email is registered on hundreds of sites (social, dating, etc.).* |
| **PDF Reporting** | Salva ogni scoperta nella History e genera un report investigativo finale in PDF. |
| **PDF Reporting** | *Saves each finding in History and generates a final investigative PDF report.* |

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
