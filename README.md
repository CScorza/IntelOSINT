<img width="1362" height="353" alt="Immagine1" src="https://github.com/user-attachments/assets/6727f5ad-829f-4dc2-908b-a5c5ca59301a" />

*È un framework avanzato di Cyber Intelligence (OSINT) all-in-one, progettato per investigazioni digitali su social media, numerazioni telefoniche, domini e transazioni crypto. 
Grazie a un'interfaccia web futuristica, permette di correlare dati provenienti da diverse fonti in tempo reale.*

---
<img width="1287" height="910" alt="image" src="https://github.com/user-attachments/assets/3160c7ec-1715-4375-bad0-d9637aa0262c" />
<img width="2468" height="1125" alt="image" src="https://github.com/user-attachments/assets/ce1bea47-4b70-4a83-bdbc-a28b1539a760" />

## 🚀 Funzionalità Principali
Il sistema integra quattro moduli investigativi verticali:
### 🌐 Social Scan
Ricerca globale per username o nome reale.

<div align="center">
  <img width="800" alt="Social Scan" src="https://github.com/user-attachments/assets/d1e63207-a28a-42bd-b329-b6db5cfd7925" />
</div>

---

### 📱 Phone Intelligence
Analisi numeri internazionali con **Telegram Live** (verifica presenza, foto profilo e nome), **TrueCaller** (Funziona solo tramite bot) e **WhatsApp**.

<div align="center">
  <img width="800" alt="Phone Intelligence" src="https://github.com/user-attachments/assets/9bde9620-07a9-4e78-9884-3e97ddec07ac" />
</div>

---

### 💰 Financial Investigation
Tracking wallet **BTC, ETH, BSC, Polygon, Solana**. Include un **analizzatore grafico di nodi** per flussi di denaro e grafici di bilancio.

<div align="center">
  <img width="800" alt="Financial Investigation" src="https://github.com/user-attachments/assets/6138876c-5517-4971-843b-96bcd6a11c07" />
</div>

---

### 🌍 Domain & IP Network
Analisi DNS (A, MX, NS, TXT), WHOIS, scansione porte, Reverse DNS e integrazione **Shodan**.

<div align="center">
  <img width="800" alt="Domain & IP Network" src="https://github.com/user-attachments/assets/a43222d8-1f19-4c60-be9e-ff451904f290" />
</div>

---

## 🛠 Istruzioni per l'Installazione

Il sistema è progettato per auto-configurarsi (Virtual Environment e dipendenze) al primo avvio.

### Requisiti
* **Python 3.8** o superiore installato.

### Procedura
1.  **Clona il repository:**
    ```bash
    git clone https://github.com/CScorza/IntelOSINT.git
    cd CSCORZA-IntelOSINT
    ```
2.  **Avvia lo script:**
    ```bash
    python IntelOSINT.py
    ```
    *Nota: Al primo avvio, il sistema installerà automaticamente i pacchetti necessari (Flask, Playwright, Telethon, ecc.) e configurerà Chromium.*

---

## 🔑 Configurazione API e Autenticazioni

Per sbloccare le funzioni avanzate, inserisci le credenziali nella dashboard di login:

### 1. Telegram (Ricerca Profonda)
* **Ottenimento:** Vai su [my.telegram.org](https://my.telegram.org), crea una "App" e copia `API ID` e `API HASH`.
* **Uso:** Inserisci i dati e clicca su "Ricevi OTP" per autenticare la sessione live.

### 2. Instagram (Data Extraction)
* **Ottenimento:** Accedi a Instagram dal browser -> F12 (Strumenti sviluppatore) -> Application -> Cookies. Copia il valore di `sessionid`.
* **Uso:** Inseriscilo nel campo `sid` per bypassare i blocchi e vedere profili protetti.

### 3. Shodan (Analisi Infrastruttura)
* **Ottenimento:** Registrati su [shodan.io](https://www.shodan.io/) e copia la tua `API Key`.
* **Uso:** Permette di visualizzare ISP, organizzazione e vulnerabilità degli IP analizzati.

---

## 📈 Funzioni Speciali

| Funzione | Descrizione |
| :--- | :--- |
| **Visual Network Graph** | Mappa interattiva delle transazioni crypto o della rete IP di un dominio. |
| **Telegram Crawler** | Esporta la lista partecipanti di gruppi/canali pubblici in formato **CSV**. |
| **Email Leak (Holehe)** | Verifica la registrazione di un'email su centinaia di siti (social, dating, ecc.). |
| **PDF Reporting** | Salva ogni scoperta nella History e genera un report investigativo finale in PDF. |

---

## ⚠️ Disclaimer
*Questo strumento è fornito esclusivamente a scopo educativo e per attività di ricerca etica. L'autore non si assume alcuna responsabilità per l'uso improprio o illegale del software. Rispetta sempre la privacy e i termini di servizio delle piattaforme.*

---
**Sviluppato da [CScorza](https://github.com/CScorza)**

☕ Supporta il Progetto/Support

* **BTC**:	bc1qfn9kynt7k26eaxk4tc67q2hjuzhfcmutzq2q6a
* **TON**:	UQBtLB6m-7q8j9Y81FeccBEjccvl34Ag5tWaUD
