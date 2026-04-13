#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSCORZA IntelOSINT V.1
"""

import os, sys, subprocess, threading, webbrowser, time, base64, json, re, asyncio, io, random, socket, urllib.parse, csv, uuid, hmac, hashlib, ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

# --- AUTO-SETUP ENVIRONMENT ---
def setup_env():
    script_path = Path(__file__).resolve()
    venv_path = script_path.parent / "venv_cscorza_intel_v1"
    py = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pip = venv_path / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    
    if sys.prefix == str(venv_path): return

    required_pkgs = [
        "flask", "requests", "phonenumbers", "telethon", "fpdf2", "bs4",
        "dnspython", "python-whois", "lxml", "pycountry", "playwright",
        "holehe", "ignorant", "trio", "httpx"
    ]

    if not venv_path.exists():
        print("[*] Init CSCORZA IntelOSINT v.1...")
        try:
            print("[*] Creazione ambiente virtuale...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
            print("[*] Installazione dipendenze Python (incluso Playwright)...")
            subprocess.run([
                str(py), "-m", "pip", "install", *required_pkgs
            ], check=True)
            print("[*] Installazione browser invisibile...")
            subprocess.run([str(py), "-m", "playwright", "install", "chromium"], check=True)
            print("[*] Setup completato con successo!")
        except Exception as e:
            print(f"[!] Setup Error: {e}")
            return
    else:
        try:
            missing = []
            checks = ["flask", "requests", "phonenumbers", "dns", "whois", "playwright", "trio", "httpx", "holehe", "ignorant"]
            for mod in checks:
                r = subprocess.run([str(py), "-c", f"import {mod}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r.returncode != 0:
                    missing.append(mod)

            if missing:
                print(f"[*] Installazione dipendenze mancanti nella venv: {', '.join(missing)}")
                subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=False)
                subprocess.run([str(py), "-m", "pip", "install", *required_pkgs], check=True)
        except Exception as e:
            print(f"[!] Setup deps error: {e}")

    try:
        os.execv(str(py), [str(py), str(script_path)])
    except OSError: pass

if __name__ == "__main__" and "FLASK_RUN_FROM_CLI" not in os.environ:
    setup_env()

# --- IMPORTS ---
from flask import Flask, render_template_string, request, jsonify, send_file, Response
import requests
import phonenumbers
from phonenumbers import geocoder, carrier
from phonenumbers import timezone as phone_timezone
from phonenumbers.phonenumberutil import region_code_for_country_code
import pycountry
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import functions, types
from bs4 import BeautifulSoup
import dns.resolver
import whois
from fpdf import FPDF
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- ASYNC SETUP ---
telethon_loop = asyncio.new_event_loop()
def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
threading.Thread(target=start_background_loop, args=(telethon_loop,), daemon=True).start()

def run_async(coro): 
    return asyncio.run_coroutine_threadsafe(coro, telethon_loop).result()

app = Flask(__name__)
session = requests.Session()

class TelegramMonitor:

    def __init__(self):
        self.active_tasks = {}
        self.status_data = {}

    async def _monitor_loop(self, target_id, target_name, duration_seconds, creds):
        client = TelegramClient(StringSession(creds['tg_session']), int(creds['tg_id']), creds['tg_hash'], loop=telethon_loop)
        await client.connect()
        if not await client.is_user_authorized():
            self.active_tasks.pop(target_id, None)
            return

        end_time = time.time() + duration_seconds
        # Clean target_id for filename
        safe_id = "".join(c for c in str(target_id) if c.isalnum() or c in ('_', '-'))
        log_file = f"TG_Monitor_{safe_id}.txt"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AVVIO MONITORAGGIO per {target_name} ({target_id})\n")

        last_state = None
        last_first_name = None
        last_last_name = None
        last_username = None

        while time.time() < end_time and self.active_tasks.get(target_id):
            try:
                entity = await client.get_entity(int(target_id))
                is_online = False
                last_seen_str = "Sconosciuto"
                
                if isinstance(entity.status, types.UserStatusOnline):
                    is_online = True
                    last_seen_str = "Adesso"
                elif getattr(entity.status, "was_online", None):
                    dt = entity.status.was_online
                    last_seen_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(entity.status, types.UserStatusRecently):
                    last_seen_str = "Di recente"
                elif isinstance(entity.status, types.UserStatusLastWeek):
                    last_seen_str = "Entro una settimana"
                elif isinstance(entity.status, types.UserStatusLastMonth):
                    last_seen_str = "Entro un mese"
                
                self.status_data[target_id] = {
                    "online": is_online, 
                    "last_seen": last_seen_str,
                    "first_name": entity.first_name,
                    "last_name": entity.last_name,
                    "username": entity.username
                }

                # Check for profile changes
                changes = []
                if last_first_name is not None and entity.first_name != last_first_name:
                    changes.append(f"Nome cambiato da '{last_first_name}' a '{entity.first_name}'")
                if last_last_name is not None and entity.last_name != last_last_name:
                    changes.append(f"Cognome cambiato da '{last_last_name}' a '{entity.last_name}'")
                if last_username is not None and entity.username != last_username:
                    changes.append(f"Username cambiato da '{last_username}' a '{entity.username}'")
                
                if changes:
                    with open(log_file, "a", encoding="utf-8") as f:
                        for change in changes:
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ALERT] {change}\n")
                
                last_first_name = entity.first_name
                last_last_name = entity.last_name
                last_username = entity.username

                if is_online != last_state:
                    if last_state is not None: # Don't log OFFLINE immediately on start if they are just offline
                        with open(log_file, "a", encoding="utf-8") as f:
                            state_str = "ONLINE" if is_online else "OFFLINE"
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] L'utente {target_name}  andato {state_str}. (Ultimo accesso: {last_seen_str})\n")
                    last_state = is_online

            except Exception as e:
                print(f"Error TG monitor loop: {e}")
            
            await asyncio.sleep(5)

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] MONITORAGGIO TERMINATO.\n")
        self.active_tasks.pop(target_id, None)
        await client.disconnect()

    async def start_monitor(self, target_id, target_name, duration_str, creds):
        if not creds.get('tg_session'):
            return {"status": "error", "error": "Non autenticato su Telegram"}

        duration_map = {"1 Ora": 3600, "6 Ore": 21600, "1 Giorno": 86400, "3 Giorni": 259200, "1 Settimana": 604800}
        dur_sec = duration_map.get(duration_str, 3600)
        
        self.active_tasks[target_id] = True
        telethon_loop.create_task(self._monitor_loop(target_id, target_name, dur_sec, creds))
        return {"status": "ok"}

tg_monitor = TelegramMonitor()

@app.route('/api/tg/start_monitoring', methods=['POST'])
def tg_start_monitoring():
    data = request.json
    target = data.get('target')
    duration = data.get('duration', '1 Ora')
    # Assumiamo di avere accesso a core.creds globale
    return jsonify(run_async(tg_monitor.start_monitor(target, target, duration, core.creds)))

@app.route('/api/tg/check_status', methods=['POST'])
def tg_check_status():
    target = request.json.get('target')
    if target in tg_monitor.active_tasks:
        return jsonify({"status": "ok", "data": tg_monitor.status_data.get(target, {"online": False, "last_seen": "Attendere..."})})
    return jsonify({"status": "stopped"})

@app.route('/api/tg/stop_monitoring', methods=['POST'])
def tg_stop_monitoring():
    target = request.json.get('target')
    if target in tg_monitor.active_tasks:
        tg_monitor.active_tasks[target] = False
    return jsonify({"status": "ok"})

@app.route('/api/tg/get_intelligence_logs', methods=['POST'])
def tg_get_intelligence_logs():
    target = request.json.get('target')
    safe_id = "".join(c for c in str(target) if c.isalnum() or c in ('_', '-'))
    log_file = f"TG_Monitor_{safe_id}.txt"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return jsonify({"status": "ok", "logs": lines})
    return jsonify({"status": "error", "logs": []})

@app.route('/api/tg/export_report', methods=['GET'])
def tg_export_report():
    target = request.args.get('target')
    if not target:
        return "Target mancante", 400
    safe_id = "".join(c for c in str(target) if c.isalnum() or c in ('_', '-'))
    log_file = f"TG_Monitor_{safe_id}.txt"
    if not os.path.exists(log_file):
        return "Nessun dato di monitoraggio trovato", 404

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"INTELLIGENCE REPORT: {target}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=10)

    for line in lines:
        clean_line = line.strip().encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, clean_line, new_x='LMARGIN', new_y='NEXT')

    return send_file(io.BytesIO(pdf.output()), mimetype='application/pdf', as_attachment=True, download_name=f"Intelligence_Report_{safe_id}.pdf")

import zipfile

class ScrapeTaskManager:
    def __init__(self):
        self.tasks = {}

    def start_task(self, target, platform, options):
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            'target': target,
            'platform': platform,
            'options': options,
            'status': 'running',
            'progress': 0,
            'result_file': None
        }
        threading.Thread(target=self._run_scrape, args=(task_id,), daemon=True).start()
        return task_id

    def _run_scrape(self, task_id):
        task = self.tasks[task_id]
        target = task['target']
        platform = task['platform']
        options = task['options']
        task['progress'] = 5
        
        tmp_dir = os.path.join(os.getcwd(), f"tmp_scrape_{task_id}")
        os.makedirs(tmp_dir, exist_ok=True)
        
        try:
            if platform == 'Telegram':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._scrape_telegram(task, tmp_dir))
                loop.close()
            elif platform == 'Instagram':
                self._scrape_instagram(task, tmp_dir)
            elif platform == 'TikTok':
                self._scrape_tiktok(task, tmp_dir)
            elif platform == 'YouTube':
                self._scrape_youtube(task, tmp_dir)
            elif platform == 'GitHub':
                self._scrape_github(task, tmp_dir)
            else:
                raise Exception("Piattaforma non supportata")
                
            task['progress'] = 90
            
            zip_filename = f"scrape_{platform}_{target}_{task_id}.zip"
            zip_path = os.path.join(os.getcwd(), zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(tmp_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        zf.write(filepath, os.path.relpath(filepath, tmp_dir))
                        
            task['progress'] = 95
            
            with open(zip_path, 'rb') as f:
                file_bytes = f.read()
                md5_hash = hashlib.md5(file_bytes).hexdigest()
                sha256_hash = hashlib.sha256(file_bytes).hexdigest()
                
            hashes_str = f"File: {zip_filename}\nMD5: {md5_hash}\nSHA256: {sha256_hash}\n"
            hashes_path = os.path.join(os.getcwd(), f"hashes_{task_id}.txt")
            with open(hashes_path, "w") as f:
                f.write(hashes_str)
                
            with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                zf.write(hashes_path, 'hashes.txt')
            os.remove(hashes_path)
                
            task['result_file'] = zip_path
            task['status'] = 'completed'
            task['progress'] = 100
            
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
        finally:
            import shutil
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _scrape_telegram(self, task, tmp_dir):
        global core
        creds = core.creds
        if not creds.get('tg_session'):
            raise Exception("Non autenticato su Telegram. Inserisci le API e fai login.")
            
        client = TelegramClient(StringSession(creds['tg_session']), int(creds['tg_id']), creds['tg_hash'])
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Sessione Telegram non valida.")
            
        target = task['target']
        opts = task['options']
        tutto = opts.get('tutto', False)
        
        try:
            entity = await client.get_entity(target)
        except Exception as e:
            raise Exception(f"Impossibile trovare il target: {e}")
            
        task['progress'] = 15
        
        if tutto or opts.get('dati', False):
            info = {
                "id": entity.id,
                "username": getattr(entity, 'username', None),
                "title": getattr(entity, 'title', getattr(entity, 'first_name', '')),
                "type": type(entity).__name__
            }
            if isinstance(entity, types.User):
                try:
                    full = await client(functions.users.GetFullUserRequest(entity))
                    info["bio"] = full.full_user.about
                except: pass
            elif isinstance(entity, (types.Channel, types.Chat)):
                try:
                    full = await client(functions.channels.GetFullChannelRequest(entity))
                    info["bio"] = full.full_chat.about
                except: pass
                
            with open(os.path.join(tmp_dir, "info.json"), "w", encoding="utf-8") as f:
                json.dump(info, f, indent=4, ensure_ascii=False)
                
            if isinstance(entity, (types.Channel, types.Chat)):
                try:
                    chat_history = []
                    async for msg in client.iter_messages(entity, limit=None):
                        if msg.text:
                            chat_history.append({
                                "id": msg.id,
                                "date": str(msg.date),
                                "sender_id": msg.sender_id,
                                "text": msg.text,
                                "fwd_from": str(msg.fwd_from) if msg.fwd_from else None
                            })
                    with open(os.path.join(tmp_dir, "chat_history.json"), "w", encoding="utf-8") as f:
                        json.dump(chat_history, f, indent=4, ensure_ascii=False)
                except: pass
                
        task['progress'] = 30
        
        if tutto or opts.get('media', False):
            try:
                await client.download_profile_photo(entity, file=os.path.join(tmp_dir, "profile_pic.jpg"))
            except: pass
            
            if isinstance(entity, (types.Channel, types.Chat)):
                os.makedirs(os.path.join(tmp_dir, "media"), exist_ok=True)
                try:
                    async for msg in client.iter_messages(entity, limit=None):
                        if msg.media:
                            await msg.download_media(file=os.path.join(tmp_dir, "media"))
                except: pass
                        
        task['progress'] = 60
        
        if (tutto or opts.get('follower', False) or opts.get('following', False)) and isinstance(entity, types.Channel):
            try:
                participants = []
                async for user in client.iter_participants(entity, limit=5000):
                    participants.append({
                        "id": user.id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    })
                with open(os.path.join(tmp_dir, "participants.json"), "w", encoding="utf-8") as f:
                    json.dump(participants, f, indent=4, ensure_ascii=False)
            except: pass
            
        task['progress'] = 80
        await client.disconnect()

    def _scrape_instagram(self, task, tmp_dir):
        global core
        opts = task['options']
        tutto = opts.get('tutto', False)
        target = task['target'].replace('@', '').strip()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )

            sid = core.creds.get('sid')
            if sid:
                context.add_cookies([{"name": "sessionid", "value": sid, "domain": ".instagram.com", "path": "/"}])

            page = context.new_page()

            # --- API Interception for raw post data ---
            api_data = []
            def handle_response(response):
                try:
                    url = response.url
                    if any(x in url for x in ["graphql/query", "api/v1/feed", "api/v1/profile", "api/v1/users", "api/v1/media", "api/v1/highlights", "tags", "comments"]):
                        data = response.json()
                        api_data.append(data)
                except:
                    pass
            page.on("response", handle_response)

            page.goto(f"https://www.instagram.com/{target}/", wait_until="domcontentloaded")
            task['progress'] = 10
            time.sleep(5)

            if tutto or opts.get('dati', False):
                try:
                    bio_el = page.query_selector("header section")
                    info = {"username": target, "text": bio_el.inner_text() if bio_el else "N/A"}

                    # Extract external link if present
                    link_el = page.locator("header section a[target='_blank']")
                    if link_el.count() > 0:
                        info['external_link'] = link_el.first.get_attribute("href")

                    with open(os.path.join(tmp_dir, "info.json"), "w", encoding="utf-8") as f:
                        json.dump(info, f, indent=4, ensure_ascii=False)
                except: pass

            task['progress'] = 15

            # --- Extract Highlights ---
            try:
                highlights = page.locator("ul[class*='_aow'] li")
                if highlights.count() > 0:
                    for i in range(min(5, highlights.count())):
                        try:
                            highlights.nth(i).click()
                            time.sleep(3)
                            page.locator("svg[aria-label='Close']").click()
                            time.sleep(1)
                        except: pass
            except: pass

            task['progress'] = 20

            # --- Scrolling to load ALL content ---
            try:
                page.wait_for_selector("article", timeout=10000)
                previous_height = page.evaluate("document.body.scrollHeight")
                stuck_counter = 0
                max_scrolls = 200 # Approx ~2400 posts
                for _ in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == previous_height:
                        stuck_counter += 1
                        if stuck_counter > 2:
                            # Micro-scroll to trigger lazy loading
                            page.evaluate("window.scrollBy(0, -300)")
                            time.sleep(0.5)
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(2)
                            new_height2 = page.evaluate("document.body.scrollHeight")
                            if new_height2 == previous_height:
                                break
                            else:
                                stuck_counter = 0
                                previous_height = new_height2
                    else:
                        stuck_counter = 0
                        previous_height = new_height

                    if task['progress'] < 40:
                        task['progress'] += 1
            except:
                pass
                
            task['progress'] = 40
            
            # --- Extract Tagged Posts ---
            try:
                tagged_link = page.locator(f"a[href='/{target}/tagged/']")
                if tagged_link.count() > 0:
                    tagged_link.click()
                    time.sleep(3)
                    for _ in range(10): # Scroll a few times in tagged
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)
            except: pass

            task['progress'] = 50

            if tutto or opts.get('media', False):
                os.makedirs(os.path.join(tmp_dir, "media"), exist_ok=True)
                posts_dir = os.path.join(tmp_dir, "media", "posts")
                os.makedirs(posts_dir, exist_ok=True)

                try:
                    pfp = page.query_selector("header img")
                    if pfp:
                        src = pfp.get_attribute("src")
                        if src:
                            import requests
                            r = requests.get(src)
                            with open(os.path.join(tmp_dir, "media", "profile_pic.jpg"), "wb") as f:
                                f.write(r.content)

                    page.screenshot(path=os.path.join(tmp_dir, "media", "profile_feed.png"), full_page=True)
                except: pass

                # Save collected JSON data
                try:
                    with open(os.path.join(tmp_dir, "media", "all_posts_data.json"), "w", encoding="utf-8") as f:
                        json.dump(api_data, f, indent=4, ensure_ascii=False)
                except: pass

                # --- DOWNLOAD MEDIA ---
                try:
                    extracted_media = []
                    def extract_urls(obj):
                        if isinstance(obj, dict):
                            if "image_versions2" in obj:
                                cands = obj["image_versions2"].get("candidates", [])
                                if cands: extracted_media.append(cands[0].get("url"))
                            if "video_versions" in obj:
                                cands = obj["video_versions"]
                                if cands: extracted_media.append(cands[0].get("url"))
                            if "display_url" in obj:
                                extracted_media.append(obj["display_url"])
                            if "video_url" in obj:
                                extracted_media.append(obj["video_url"])

                            for k, v in obj.items(): extract_urls(v)
                        elif isinstance(obj, list):
                            for item in obj: extract_urls(item)

                    extract_urls(api_data)

                    # Also fallback to DOM images
                    dom_images = page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('article img')).map(img => img.src).filter(src => src);
                    }""")
                    extracted_media.extend(dom_images)
                    extracted_media = list(set([u for u in extracted_media if u and u.startswith('http')]))

                    import requests
                    import uuid
                    pw_cookies = context.cookies()
                    req_cookies = {c['name']: c['value'] for c in pw_cookies}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.instagram.com/"
                    }

                    downloaded = 0
                    max_downloads = 1000 # Configurable limit

                    for url in extracted_media:
                        if downloaded >= max_downloads: break
                        try:
                            res = requests.get(url, headers=headers, cookies=req_cookies, stream=True, timeout=15)
                            if res.status_code == 200:
                                ext = "mp4" if "video" in url or "mp4" in url else "jpg"
                                fname = f"post_{uuid.uuid4().hex[:8]}.{ext}"
                                with open(os.path.join(posts_dir, fname), "wb") as f:
                                    for chunk in res.iter_content(8192):
                                        f.write(chunk)
                                downloaded += 1
                        except: pass
                except: pass

            task['progress'] = 70

            if tutto or opts.get('follower', False):
                try:
                    followers_link = page.locator(f"a[href='/{target}/followers/']")
                    if followers_link.count() > 0:
                        followers_link.first.click()
                        page.wait_for_selector("div[role='dialog']", timeout=5000)
                        time.sleep(2)

                        followers_data = page.evaluate("""() => {
                            let dialog = document.querySelector('div[role="dialog"]');
                            let results = [];
                            if(dialog) {
                                let scrollable = dialog.querySelector('div[style*="overflow-y"], div[style*="hidden"] > div > div > div > div, div[role="dialog"] div:nth-child(2) > div > div');
                                if(scrollable) {
                                    for(let i=0; i<15; i++) {
                                        scrollable.scrollBy(0, 5000);
                                    }
                                }
                                let items = dialog.querySelectorAll('span[dir="auto"], a[role="link"]');
                                items.forEach(el => {
                                    if(el.innerText && el.innerText.trim().length > 0) {
                                        let text = el.innerText.trim();
                                        if(!results.includes(text) && !text.includes('Follow') && !text.includes('Rimuovi') && !text.includes('Remove')) {
                                            results.push(text);
                                        }
                                    }
                                });
                            }
                            return results;
                        }""")
                        if followers_data:
                            with open(os.path.join(tmp_dir, "followers.json"), "w", encoding="utf-8") as f:
                                json.dump(followers_data, f, indent=4, ensure_ascii=False)
                except: pass

            task['progress'] = 100
            browser.close()
    def _scrape_tiktok(self, task, tmp_dir):
        global core
        opts = task['options']
        tutto = opts.get('tutto', False)
        target = task['target']
        if not target.startswith('@'): target = '@' + target

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )

            tiktok_sid = core.creds.get('tiktok_sid')
            if tiktok_sid:
                context.add_cookies([{"name": "sessionid", "value": tiktok_sid, "domain": ".tiktok.com", "path": "/"}])

            page = context.new_page()
            
            # --- API Interception for raw video data ---
            api_videos = []
            def handle_response(response):
                try:
                    if "api/item_list" in response.url or "api/post/item_list" in response.url:
                        data = response.json()
                        if 'itemList' in data:
                            api_videos.extend(data['itemList'])
                except:
                    pass
            page.on("response", handle_response)
            
            page.goto(f"https://www.tiktok.com/{target}", wait_until="domcontentloaded")
            task['progress'] = 10
            time.sleep(5)
            
            if tutto or opts.get('dati', False):
                try:
                    info = {"username": target}
                    title = page.title()
                    info['page_title'] = title
                    
                    stats = page.locator("[data-e2e='user-stat']")
                    if stats.count() > 0:
                        info['stats'] = stats.inner_text()
                        
                    bio = page.locator("[data-e2e='user-bio']")
                    if bio.count() > 0:
                        info['bio'] = bio.inner_text()
                        
                    link_el = page.locator("[data-e2e='user-link']")
                    if link_el.count() > 0:
                        info['external_link'] = link_el.get_attribute("href")
                        
                    with open(os.path.join(tmp_dir, "info.json"), "w", encoding="utf-8") as f:
                        json.dump(info, f, indent=4, ensure_ascii=False)
                except: pass
                
            task['progress'] = 20
            
            if tutto or opts.get('follower', False):
                try:
                    followers_link = page.locator(f"a[href='/{target.strip('@')}/followers'], a[href*='/followers']")
                    if followers_link.count() > 0:
                        followers_link.first.click()
                        page.wait_for_selector("[data-e2e='user-followers-modal'], [role='dialog'], .tiktok-1x9h687-DivUserContainer", timeout=5000)
                        time.sleep(2)
                        
                        # Scroll and extract using JS
                        followers_data = page.evaluate("""() => {
                            let dialog = document.querySelector('[role="dialog"]') || document.querySelector('.tiktok-1x9h687-DivUserContainer');
                            let results = [];
                            if(dialog) {
                                let scrollable = dialog.querySelector('div[style*="overflow-y"], ul, .tiktok-1x9h687-DivUserContainer');
                                if(scrollable) {
                                    // Scroll multiple times to fetch followers
                                    for(let i=0; i<15; i++) {
                                        scrollable.scrollBy(0, 5000);
                                    }
                                }
                                let items = dialog.querySelectorAll('li, [data-e2e="search-user-info-container"]');
                                items.forEach(el => {
                                    let title = el.querySelector('h4, h3, [data-e2e="search-user-title"], span[class*="SpanUserNameText"]');
                                    let subtitle = el.querySelector('p, [data-e2e="search-user-desc"], span[class*="SpanCustomUserName"]');
                                    if(title && title.innerText.trim()) {
                                        results.push({
                                            username: title.innerText.trim(),
                                            name: subtitle ? subtitle.innerText.trim() : ''
                                        });
                                    }
                                });
                            }
                            // Fallback to searching all a tags with user-title class if modal parsing fails
                            if (results.length === 0) {
                                let fallbackItems = document.querySelectorAll('li[class*="UserItem"], div[class*="DivUserContainer"]');
                                fallbackItems.forEach(el => {
                                    let title = el.querySelector('h4, span[class*="SpanUserNameText"]');
                                    let subtitle = el.querySelector('span[class*="SpanCustomUserName"]');
                                    if(title && title.innerText.trim()) {
                                        results.push({
                                            username: title.innerText.trim(),
                                            name: subtitle ? subtitle.innerText.trim() : ''
                                        });
                                    }
                                });
                            }
                            return results;
                        }""")
                        if followers_data:
                            with open(os.path.join(tmp_dir, "followers.json"), "w", encoding="utf-8") as f:
                                json.dump(followers_data, f, indent=4, ensure_ascii=False)
                except: pass
                
            task['progress'] = 25
            
            # --- Scrolling to load ALL content ---
            try:
                page.wait_for_selector("[data-e2e='user-post-item-list']", timeout=10000)
                previous_height = page.evaluate("document.body.scrollHeight")
                stuck_counter = 0
                max_scrolls = 200 # Support for ~2000+ videos
                for _ in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == previous_height:
                        stuck_counter += 1
                        if stuck_counter > 2:
                            # Micro-scroll to trigger lazy loading if stuck
                            page.evaluate("window.scrollBy(0, -300)")
                            time.sleep(0.5)
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(2)
                            new_height2 = page.evaluate("document.body.scrollHeight")
                            if new_height2 == previous_height:
                                break
                            else:
                                stuck_counter = 0
                                previous_height = new_height2
                    else:
                        stuck_counter = 0
                        previous_height = new_height
                        
                    if task['progress'] < 50:
                        task['progress'] += 1
            except:
                pass
                
            task['progress'] = 50
            
            # --- Extract initial videos from Rehydration Script ---
            try:
                script_content = page.evaluate("() => document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')?.textContent")
                if script_content:
                    data = json.loads(script_content)
                    initial_video_objects = []
                    
                    def find_video_objects(obj):
                        if isinstance(obj, dict):
                            if 'id' in obj and 'video' in obj and isinstance(obj['video'], dict) and 'playAddr' in obj['video']:
                                initial_video_objects.append(obj)
                            else:
                                for v in obj.values():
                                    find_video_objects(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_video_objects(item)
                                
                    find_video_objects(data)
                    
                    # Merge avoiding duplicates
                    existing_ids = {v.get('id') for v in api_videos if v.get('id')}
                    for v in initial_video_objects:
                        if v.get('id') and v['id'] not in existing_ids:
                            api_videos.append(v)
                            existing_ids.add(v['id'])
            except:
                pass
            
            # --- Extract DOM fallback videos ---
            dom_videos = []
            try:
                video_elements = page.locator("[data-e2e='user-post-item']").all()
                for idx, el in enumerate(video_elements):
                    try:
                        link_el = el.locator("a").first
                        link = link_el.get_attribute("href")
                        views = el.locator("[data-e2e='video-views']").inner_text()
                        if link:
                            dom_videos.append({"url": link, "views": views})
                    except:
                        pass
            except:
                pass
                
            # --- Extract Metadata (Hashtags, Sounds, Captions, Emails) ---
            try:
                import csv
                import re
                metadata_path = os.path.join(tmp_dir, "tiktok_metadata.csv")
                with open(metadata_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Video ID', 'Description', 'Hashtags', 'Sound/Music', 'Found Emails'])
                    
                    for v in api_videos:
                        v_id = v.get('id', '')
                        desc = v.get('desc', '')
                        
                        # Extract hashtags from textChallenges
                        hashtags = [h.get('hashtagName', '') for h in v.get('textExtra', []) if h.get('hashtagName')]
                        if not hashtags and desc:
                            hashtags = re.findall(r'#(\w+)', desc)
                            
                        # Extract sound
                        music = v.get('music', {})
                        sound_title = music.get('title', '')
                        sound_author = music.get('authorName', '')
                        sound = f"{sound_title} - {sound_author}" if sound_title else ''
                        
                        # Extract emails
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc)
                        
                        writer.writerow([v_id, desc, ", ".join(hashtags), sound, ", ".join(emails)])
            except:
                pass

            task['progress'] = 60

            if tutto or opts.get('media', False):
                os.makedirs(os.path.join(tmp_dir, "media"), exist_ok=True)
                videos_dir = os.path.join(tmp_dir, "media", "videos")
                os.makedirs(videos_dir, exist_ok=True)
                
                try:
                    pfp = page.locator("img[class*='ImgAvatar']")
                    if pfp.count() > 0:
                        src = pfp.first.get_attribute("src")
                        if src:
                            import requests
                            r = requests.get(src)
                            with open(os.path.join(tmp_dir, "media", "profile_pic.jpg"), "wb") as f:
                                f.write(r.content)
                                
                    page.screenshot(path=os.path.join(tmp_dir, "media", "all_videos_feed.png"), full_page=True)
                except: pass
                
                # Save collected JSON data (full profile content database)
                try:
                    with open(os.path.join(tmp_dir, "media", "all_videos_data.json"), "w", encoding="utf-8") as f:
                        json.dump({"api_extracted": api_videos, "dom_extracted": dom_videos}, f, indent=4, ensure_ascii=False)
                except: pass
                
                # --- DOWNLOAD VIDEOS ---
                try:
                    import requests
                    pw_cookies = context.cookies()
                    req_cookies = {c['name']: c['value'] for c in pw_cookies}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.tiktok.com/"
                    }
                    
                    downloaded_count = 0
                    max_downloads = 1000 # Large limit to actually get "all" content if requested
                    
                    for item in api_videos:
                        if downloaded_count >= max_downloads:
                            break
                        try:
                            vid_id = item.get("id")
                            video_info = item.get("video", {})
                            play_addr = video_info.get("playAddr") or video_info.get("downloadAddr")
                            
                            if play_addr and vid_id:
                                res = requests.get(play_addr, headers=headers, cookies=req_cookies, stream=True, timeout=15)
                                if res.status_code == 200:
                                    vid_path = os.path.join(videos_dir, f"{vid_id}.mp4")
                                    with open(vid_path, "wb") as f:
                                        for chunk in res.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    downloaded_count += 1
                        except:
                            pass
                except:
                    pass
                
            task['progress'] = 80
            
            if tutto or opts.get('link', False):
                try:
                    link_el = page.locator("[data-e2e='user-link']")
                    if link_el.count() > 0:
                        href = link_el.get_attribute("href")
                        with open(os.path.join(tmp_dir, "external_links.txt"), "w", encoding="utf-8") as f:
                            f.write(str(href))
                except: pass
                
            task['progress'] = 100
            browser.close()

    def _scrape_youtube(self, task, tmp_dir):
        global core
        opts = task['options']
        tutto = opts.get('tutto', False)
        target = task['target']
        if not target.startswith('@') and not target.startswith('UC'): 
            # assume it's a handle if no @
            target = '@' + target
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            # Intercept API calls for videos and community info
            api_data = []
            def handle_response(response):
                try:
                    if "youtubei/v1/browse" in response.url or "youtubei/v1/player" in response.url:
                        data = response.json()
                        api_data.append(data)
                except: pass
            page.on("response", handle_response)
            
            url = f"https://www.youtube.com/{target}/videos" if target.startswith('@') else f"https://www.youtube.com/channel/{target}/videos"
            page.goto(url, wait_until="domcontentloaded")
            task['progress'] = 15
            time.sleep(5)
            
            # Click reject cookies if present
            try:
                page.locator("button[aria-label*='Rifiuta'], button[aria-label*='Reject']").click()
                time.sleep(2)
            except: pass
            
            if tutto or opts.get('dati', False):
                try:
                    info = {"channel": target}
                    info['title'] = page.title()
                    
                    # Try to get to "About" tab
                    about_url = url.replace('/videos', '/about')
                    page.goto(about_url, wait_until="domcontentloaded")
                    time.sleep(3)
                    
                    desc_el = page.locator("#description-container, yt-attributed-string#description")
                    if desc_el.count() > 0:
                        info['description'] = desc_el.first.inner_text()
                        
                    links_el = page.locator("#link-list-container a, yt-channel-external-link-view-model a")
                    links = []
                    for i in range(links_el.count()):
                        links.append(links_el.nth(i).get_attribute("href"))
                    info['links'] = links
                    
                    with open(os.path.join(tmp_dir, "youtube_info.json"), "w", encoding="utf-8") as f:
                        json.dump(info, f, indent=4, ensure_ascii=False)
                        
                    # Go back to videos
                    page.goto(url, wait_until="domcontentloaded")
                    time.sleep(3)
                except: pass
                
            task['progress'] = 40
            
            if tutto or opts.get('media', False):
                os.makedirs(os.path.join(tmp_dir, "media"), exist_ok=True)
                try:
                    pfp = page.locator("#channel-header-container img").first
                    if pfp.count() > 0:
                        src = pfp.get_attribute("src")
                        if src:
                            import requests
                            r = requests.get(src)
                            with open(os.path.join(tmp_dir, "media", "profile_pic.jpg"), "wb") as f:
                                f.write(r.content)
                except: pass
                
                # Scroll to get videos list
                try:
                    for _ in range(20):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)
                except: pass
                
                try:
                    videos = []
                    video_els = page.locator("ytd-rich-grid-media").all()
                    for el in video_els:
                        try:
                            title = el.locator("#video-title").inner_text()
                            link = el.locator("#video-title-link").get_attribute("href")
                            views = el.locator("#metadata-line span").first.inner_text()
                            videos.append({"title": title, "link": f"https://youtube.com{link}", "views": views})
                        except: pass
                    with open(os.path.join(tmp_dir, "media", "videos_list.json"), "w", encoding="utf-8") as f:
                        json.dump(videos, f, indent=4, ensure_ascii=False)
                except: pass
                
                try:
                    with open(os.path.join(tmp_dir, "media", "raw_api_data.json"), "w", encoding="utf-8") as f:
                        json.dump(api_data, f, indent=4, ensure_ascii=False)
                except: pass

            task['progress'] = 100
            browser.close()

    def _scrape_github(self, task, tmp_dir):
        opts = task['options']
        tutto = opts.get('tutto', False)
        target = task['target']
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            page.goto(f"https://github.com/{target}", wait_until="domcontentloaded")
            task['progress'] = 20
            time.sleep(3)
            
            if tutto or opts.get('dati', False):
                try:
                    info = {"username": target}
                    name_el = page.locator("span.p-name")
                    if name_el.count() > 0: info['name'] = name_el.first.inner_text()
                    
                    bio_el = page.locator("div.p-note")
                    if bio_el.count() > 0: info['bio'] = bio_el.first.inner_text()
                    
                    org_el = page.locator("span.p-org")
                    if org_el.count() > 0: info['organization'] = org_el.first.inner_text()
                    
                    with open(os.path.join(tmp_dir, "info.json"), "w", encoding="utf-8") as f:
                        json.dump(info, f, indent=4, ensure_ascii=False)
                except: pass
                
            task['progress'] = 40
            
            # Extract public emails from recent commits
            emails = set()
            try:
                import requests
                r = requests.get(f"https://api.github.com/users/{target}/events/public")
                if r.status_code == 200:
                    events = r.json()
                    for ev in events:
                        if ev.get("type") == "PushEvent":
                            commits = ev.get("payload", {}).get("commits", [])
                            for c in commits:
                                author = c.get("author", {})
                                email = author.get("email")
                                if email and "noreply.github.com" not in email:
                                    emails.add(email)
                                    
                if emails:
                    with open(os.path.join(tmp_dir, "extracted_emails.txt"), "w", encoding="utf-8") as f:
                        for e in emails: f.write(e + "\n")
            except: pass
            
            task['progress'] = 60
            
            if tutto or opts.get('media', False):
                os.makedirs(os.path.join(tmp_dir, "media"), exist_ok=True)
                try:
                    pfp = page.locator("img.avatar-user").first
                    if pfp.count() > 0:
                        src = pfp.get_attribute("src")
                        if src:
                            import requests
                            r = requests.get(src)
                            with open(os.path.join(tmp_dir, "media", "profile_pic.jpg"), "wb") as f:
                                f.write(r.content)
                except: pass
                
            task['progress'] = 100
            browser.close()

scrape_manager = ScrapeTaskManager()

@app.route('/api/scrape/start', methods=['POST'])
def scrape_start():
    data = request.json
    target = data.get('target')
    platform = data.get('platform')
    options = data.get('options', {})
    
    if not target or not platform:
        return jsonify({"status": "error", "message": "Target or platform missing"}), 400
        
    task_id = scrape_manager.start_task(target, platform, options)
    return jsonify({"status": "ok", "taskId": task_id})

@app.route('/api/scrape/status', methods=['POST'])
def scrape_status():
    data = request.json
    task_ids = data.get('taskIds', [])
    results = {}
    for tid in task_ids:
        if tid in scrape_manager.tasks:
            results[tid] = scrape_manager.tasks[tid]
    return jsonify({"status": "ok", "tasks": results})

@app.route('/api/scrape/download/<task_id>', methods=['GET'])
def scrape_download(task_id):
    if task_id not in scrape_manager.tasks:
        return "Task non trovato", 404
    task = scrape_manager.tasks[task_id]
    if task['status'] != 'completed' or not task['result_file']:
        return "File non ancora pronto", 400
    if not os.path.exists(task['result_file']):
        return "File rimosso o inesistente", 404
    return send_file(task['result_file'], as_attachment=True)

# --- CONFIG ---
CREDS_FILE = "credenziali_api.json"
PORT_NUMBER = 5055
LOGO_URL = "https://github.com/CScorza.png"
REV_ICON = "https://static.vecteezy.com/system/resources/previews/067/065/684/non_2x/revolut-logo-rounded-icon-transparent-background-free-png.png"
DEFAULT_CREDS = {
    "sid": "",
    "tiktok_sid": "",
    "tg_id": "",
    "tg_hash": "",
    "tg_session": "",
    "my_phone": "",
    "shodan_key": "",
    "numverify_key": "",
    "dns_history_api_key": "",
    "ct_api_enabled": True
}

AUTHOR_INFO = [
    {"label": "Telegram", "val": "@CScorzaTg", "url": "https://t.me/CScorzaTg", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111646.png", "bg": "#229ED9"},
    {"label": "Website", "val": "cscorza.github.io", "url": "https://cscorza.github.io/CScorza", "icon": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png", "bg": "#3b82f6"},
    {"label": "X (Twitter)", "val": "@CScorzaOSINT", "url": "https://x.com/CScorzaOSINT", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968830.png", "bg": "#000000"},
    {"label": "GitHub", "val": "github.com/CScorza", "url": "https://github.com/CScorza", "icon": "https://cdn-icons-png.flaticon.com/512/25/25231.png", "bg": "#333333"},
    {"label": "Email", "val": "cscorzaosint@protonmail.com", "url": "mailto:cscorzaosint@protonmail.com", "icon": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "bg": "#8B5CF6", "copy": True}
]

DONATIONS = [{"curr": "BTC", "addr": "bc1qfn9kynt7k26eaxk4tc67q2hjuzhfcmutzq2q6a"}, {"curr": "TON", "addr": "UQBtLB6m-7q8j9Y81FeccBEjccvl34Ag5tWaUD"}]

WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

SOCIAL_MAP = {
    "WhatsMyName (Social)": {"base": "", "icon": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png"},
    "Telegram": {"base": "t.me/", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111646.png"},
    "Instagram": {"base": "instagram.com/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174855.png"},
    "Facebook": {"base": "facebook.com/", "icon": "https://cdn-icons-png.flaticon.com/512/124/124010.png"},
    "Twitter/X": {"base": "x.com/", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968830.png"},
    "TikTok": {"base": "tiktok.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/3046/3046121.png"},
    "LinkedIn": {"base": "linkedin.com/in/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174857.png"},
    "GitHub": {"base": "github.com/", "icon": "https://cdn-icons-png.flaticon.com/512/25/25231.png"},
    "YouTube": {"base": "youtube.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"},
    "Pinterest": {"base": "pinterest.com/", "icon": "https://cdn-icons-png.flaticon.com/512/145/145808.png"},
    "Reddit": {"base": "reddit.com/user/", "icon": "https://cdn-icons-png.flaticon.com/512/3536/3536761.png"},
    "Twitch": {"base": "twitch.tv/", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968819.png"},
    "Discord": {"base": "discord.com/users/", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968756.png"},
    "WhatsApp": {"base": "wa.me/", "icon": "https://cdn-icons-png.flaticon.com/512/733/733585.png"},
    "Threads": {"base": "threads.net/@", "icon": "https://cdn-icons-png.flaticon.com/512/10091/10091234.png"},
    "Medium": {"base": "medium.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"},
    "Snapchat": {"base": "snapchat.com/add/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174870.png"},
    "Behance": {"base": "behance.net/", "icon": "https://cdn-icons-png.flaticon.com/512/733/733541.png"},
    "Dribbble": {"base": "dribbble.com/", "icon": "https://cdn-icons-png.flaticon.com/512/733/733544.png"},
    "Stack Overflow": {"base": "stackoverflow.com/users/", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111628.png"},
    "SoundCloud": {"base": "soundcloud.com/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174871.png"},
    "Spotify": {"base": "open.spotify.com/user/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174872.png"},
    "DeviantArt": {"base": "deviantart.com/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174842.png"},
    "Patreon": {"base": "patreon.com/", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111545.png"},
    "Mastodon": {"base": "mastodon.social/@", "icon": "https://cdn-icons-png.flaticon.com/512/2525/2525032.png"},
    "Quora": {"base": "quora.com/profile/", "icon": "https://cdn-icons-png.flaticon.com/512/3536/3536648.png"},
    "Slack": {"base": "slack.com/", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968929.png"},
    "Steam": {"base": "steamcommunity.com/id/", "icon": "https://cdn-icons-png.flaticon.com/512/733/733575.png"},
    "Vimeo": {"base": "vimeo.com/", "icon": "https://cdn-icons-png.flaticon.com/512/174/174875.png"},
    "Skype": {"base": "skype:", "icon": "https://cdn-icons-png.flaticon.com/512/174/174869.png"},
    "WeChat": {"base": "wechat.com/", "icon": "https://cdn-icons-png.flaticon.com/512/3670/3670311.png"},
    "VK": {"base": "vk.com/", "icon": "https://cdn-icons-png.flaticon.com/512/145/145813.png"},
    "OpenSea": {"base": "opensea.io/", "icon": "https://cdn-icons-png.flaticon.com/512/6124/6124991.png"},
    "ArtStation": {"base": "artstation.com/", "icon": "https://cdn-icons-png.flaticon.com/512/3670/3670189.png"},
    "Product Hunt": {"base": "producthunt.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111559.png"},
    "Hugging Face": {"base": "huggingface.co/", "icon": "https://cdn-icons-png.flaticon.com/512/11516/11516240.png"},
    "GitLab": {"base": "gitlab.com/", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968853.png"},
    "Bluesky": {"base": "bsky.app/profile/", "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Bluesky_Logo.svg/1920px-Bluesky_Logo.svg.png"},
    "Goodreads": {"base": "goodreads.com/", "icon": "https://cdn-icons-png.flaticon.com/512/3670/3670175.png"},
    "Letterboxd": {"base": "letterboxd.com/", "icon": "https://cdn-icons-png.flaticon.com/512/10091/10091216.png"},
    "Kaggle": {"base": "kaggle.com/", "icon": "https://cdn-icons-png.flaticon.com/512/3670/3670178.png"},
    "Etsy": {"base": "etsy.com/shop/", "icon": "https://cdn-icons-png.flaticon.com/512/825/825513.png"},
    "TripAdvisor": {"base": "tripadvisor.com/Profile/", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111664.png"},
    "Figma": {"base": "figma.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968705.png"},
    "Unsplash": {"base": "unsplash.com/@", "icon": "https://cdn-icons-png.flaticon.com/512/1051/1051332.png"},
    "Buy Me a Coffee": {"base": "buymeacoffee.com/", "icon": "https://cdn-icons-png.flaticon.com/512/5753/5753177.png"}
}

CRYPTO_MAP = {
    "BTC": {"regex": r"^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$", "name": "Bitcoin", "explorer": "https://mempool.space/address/", "icon": "https://assets.coingecko.com/coins/images/1/standard/bitcoin.png"},
    "ETH": {"regex": r"^0x[a-fA-F0-9]{40}$", "name": "Ethereum", "explorer": "https://etherscan.io/address/", "icon": "https://assets.coingecko.com/coins/images/279/standard/ethereum.png"},
    "BSC": {"regex": r"^0x[a-fA-F0-9]{40}$", "name": "Binance SC", "explorer": "https://bscscan.com/address/", "icon": "https://assets.coingecko.com/coins/images/825/standard/bnb-icon2_2x.png"},
    "POLYGON": {"regex": r"^0x[a-fA-F0-9]{40}$", "name": "Polygon", "explorer": "https://polygonscan.com/address/", "icon": "https://assets.coingecko.com/coins/images/4713/standard/polygon.png"},
    "AVAX": {"regex": r"^0x[a-fA-F0-9]{40}$", "name": "Avalanche", "explorer": "https://snowtrace.io/address/", "icon": "https://assets.coingecko.com/coins/images/12559/standard/Avalanche_Circle_RedWhite_Trans.png"},
    "LTC": {"regex": r"^(L|M|ltc1)[a-zA-HJ-NP-Z0-9]{26,40}$", "name": "Litecoin", "explorer": "https://blockchair.com/litecoin/address/", "icon": "https://assets.coingecko.com/coins/images/2/standard/litecoin.png"},
    "DOGE": {"regex": r"^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$", "name": "Dogecoin", "explorer": "https://blockchair.com/dogecoin/address/", "icon": "https://assets.coingecko.com/coins/images/5/standard/dogecoin.png"},
    "DASH": {"regex": r"^X[1-9A-HJ-NP-Za-km-z]{33}$", "name": "Dash", "explorer": "https://blockchair.com/dash/address/", "icon": "https://assets.coingecko.com/coins/images/19/standard/dash.png"},
    "TRX": {"regex": r"^T[A-Za-z1-9]{33}$", "name": "Tron", "explorer": "https://tronscan.org/#/address/", "icon": "https://assets.coingecko.com/coins/images/1094/standard/tron-logo.png"},
    "SOL": {"regex": r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", "name": "Solana", "explorer": "https://solscan.io/account/", "icon": "https://assets.coingecko.com/coins/images/4128/standard/solana.png"},
    "XRP": {"regex": r"^r[0-9a-zA-Z]{24,34}$", "name": "Ripple", "explorer": "https://xrpscan.com/account/", "icon": "https://assets.coingecko.com/coins/images/44/standard/xrp-symbol-white-128.png"}
}


# --- UI HTML ---
HTML_UI = r"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>CScorza Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        /* TEMA COLORI AGGIORNATO (Platinum / Cyber) */
        :root { 
            --bg: #070a13; 
            --panel: #0d1326; 
            --accent: #00e5ff; 
            --secondary: #3b82f6; 
            --text: #e2e8f0; 
            --success: #00e676; 
            --danger: #f43f5e; 
        }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; min-width: 320px; overflow: hidden; }
        ::-webkit-scrollbar { width: 8px; } ::-webkit-scrollbar-track { background: #070a13; } ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        
        #login-view { position: fixed; inset: 0; z-index: 2000; display: flex; justify-content: center; align-items: center; }
        
        /* GRIGLIA LOGIN AGGIORNATA */
        .login-card { position: relative; z-index: 1; background: rgba(13, 19, 38, 0.95); padding: 0; border-radius: 20px; border: 1px solid rgba(0, 229, 255, 0.2); width: min(1280px, 96vw); height: min(900px, 92vh); box-shadow: 0 0 60px rgba(0,0,0,0.8); backdrop-filter: blur(10px); display:grid; grid-template-columns: 1.2fr 1fr; overflow: hidden; }
        
        .login-form { padding: 40px; display: flex; flex-direction: column; justify-content: center; }
        .section-title { color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: 1.5px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; text-transform: uppercase; }
        .login-input { width: 100%; background: #070a13; border: 1px solid #1e293b; color: white; padding: 14px; margin-bottom: 15px; border-radius: 8px; font-family: monospace; box-sizing: border-box; transition: 0.3s; }
        .login-input:focus { border-color: var(--accent); outline: none; background: #0b101e; box-shadow: 0 0 10px rgba(0, 229, 255, 0.1); }
        .btn-otp { background: var(--secondary); color: white; border: none; padding: 12px; width: 100%; font-weight: bold; border-radius: 8px; cursor: pointer; margin-bottom: 15px; transition: 0.2s; }
        .btn-otp:hover { filter: brightness(1.2); }
        .action-btn { background: var(--accent); color: #000; border: none; padding: 0 20px; border-radius: 8px; font-weight: 900; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; transition: 0.2s; height: 40px; display: flex; align-items: center; justify-content: center; }
        .action-btn:hover { filter: brightness(1.1); box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }

        .author-pane { background: #0a0e1a; padding: 40px 30px; border-left: 1px solid #1e293b; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative; overflow-y: hidden; }
        .author-pane::before { content: ''; position: absolute; top:0; left:0; width:100%; height:5px; background: linear-gradient(90deg, var(--secondary), var(--accent)); }
        
        .logo-ring { width: 110px; height: 110px; border-radius: 50%; padding: 4px; background: linear-gradient(45deg, var(--secondary), var(--accent)); margin-bottom: 20px; }
        .logo-img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; border: 4px solid #0a0e1a; background: #000; }
        
        .app-title { font-size: 28px; font-weight: 900; margin: 0; color: white; letter-spacing: 2px; }
        .app-ver { color: #94a3b8; font-size: 14px; margin-bottom: 30px; font-family: monospace; font-weight: bold; text-transform: uppercase; }
        
        .auth-links { display: flex; flex-direction: column; gap: 12px; width: 100%; margin-bottom: 10px; }
        .auth-card { display: flex; align-items: center; gap: 15px; background: #0d1326; padding: 15px; border-radius: 10px; text-decoration: none; color: white; transition: all 0.3s ease; border: 1px solid transparent; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .auth-card:hover { transform: translateY(-3px) scale(1.02); border-color: rgba(0, 229, 255, 0.3); background: #131c36; box-shadow: 0 8px 15px rgba(0,0,0,0.5); }
        .auth-icon-wrap { width: 28px; height: 28px; position: relative; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .auth-icon-wrap::after { content: ""; position: absolute; left: 50%; bottom: -2px; width: 22px; height: 8px; transform: translateX(-50%); border-radius: 50%; background: radial-gradient(ellipse at center, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 75%); filter: blur(3px); opacity: 0; transition: opacity 0.3s ease; pointer-events: none; }
        .auth-icon-wrap.glow::after { opacity: 1; }
        .auth-icon { width: 28px; height: 28px; position: relative; z-index: 1; }
        .auth-text { display: flex; flex-direction: column; align-items: flex-start; }
        .auth-text h4 { margin: 0; font-size: 14px; font-weight: bold; color: white; }
        .auth-text span { font-size: 13px; font-weight: 500; font-family: monospace; color: #e2e8f0; }
        
        /* STILI PER LE DONAZIONI */
        .donation-section { width: 100%; margin-top: auto; padding-top: 15px; border-top: 1px dashed #1e293b; display: flex; flex-direction: column; gap: 10px; }
        .donation-title { color: var(--success); font-size: 11px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; display: flex; align-items: center; justify-content: center; gap: 5px;}
        .donation-card { background: rgba(0, 230, 118, 0.05); border: 1px solid rgba(0, 230, 118, 0.2); padding: 12px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; transition: 0.3s; cursor: pointer; }
        .donation-card:hover { background: rgba(0, 230, 118, 0.1); border-color: var(--success); box-shadow: 0 0 10px rgba(0, 230, 118, 0.2); }
        .donation-info { display: flex; flex-direction: column; align-items: flex-start; width: 85%; }
        .donation-curr { font-weight: bold; color: white; font-size: 12px; }
        .donation-addr { color: #94a3b8; font-family: monospace; font-size: 9.5px; margin-top: 3px; word-break: break-all; text-align: left; }
        .donation-icon { font-size: 16px; opacity: 0.8; }
        
        #dashboard { display: none; width: 100%; height: 100%; min-width: 0; min-height: 100vh; }
        #sidebar { width: clamp(240px, 22vw, 300px); min-width: 220px; background: var(--panel); border-right: 1px solid #1e293b; display: flex; flex-direction: column; padding: 20px; }
        .history-head { display: flex; justify-content: space-between; align-items: center; margin: 0 0 10px 0; flex-wrap: wrap; gap: 8px; }
        .history-head h4 { margin: 0; color: white; font-size: 12px; font-weight: 900; letter-spacing: 1px; text-transform: uppercase; }
        .hist-icons-toggle { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #94a3b8; cursor: pointer; user-select: none; }
        .hist-icons-toggle input { accent-color: var(--accent); cursor: pointer; width: 14px; height: 14px; }
        #history-list { flex: 1; overflow-y: auto; margin-bottom: 20px; border-top: 1px solid #1e293b; padding-top: 12px; display: flex; flex-direction: column; gap: 8px; min-height: 48px; }
        .hist-item { background: var(--bg); border: 1px solid #1e293b; border-radius: 10px; padding: 10px 8px 10px 10px; transition: 0.2s; }
        .hist-item:hover { border-color: rgba(0, 229, 255, 0.35); box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35); }
        .hist-item-main { display: flex; align-items: center; gap: 10px; min-width: 0; }
        .hist-thumb { width: 40px; height: 40px; border-radius: 8px; object-fit: cover; flex-shrink: 0; border: 1px solid #1e293b; background: #0b0f19; }
        .hist-thumb-placeholder { width: 40px; height: 40px; border-radius: 8px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 900; color: var(--accent); background: rgba(0, 229, 255, 0.1); border: 1px solid #1e293b; }
        .hist-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
        .hist-service { font-size: 10px; font-weight: 800; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .hist-username { font-size: 12px; color: #e2e8f0; font-family: ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .hist-remove { flex-shrink: 0; width: 28px; height: 28px; border: none; border-radius: 8px; background: rgba(244, 63, 94, 0.12); color: var(--danger); font-size: 20px; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; padding: 0; }
        .hist-remove:hover { background: var(--danger); color: white; }
        .hist-empty { font-size: 11px; color: #64748b; text-align: center; padding: 16px 8px; border: 1px dashed #1e293b; border-radius: 8px; }
        #main-area { flex: 1; min-width: 0; display: flex; flex-direction: column; background: var(--bg); position: relative; overflow: hidden; }
        #overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 900; display: none; backdrop-filter: blur(5px); }
        
        #graph-overlay { position: fixed; inset: 0; background: rgba(7, 10, 19, 0.98); z-index: 3000; display: none; flex-direction: column; }
        #graph-main-container { display: flex; flex: 1; overflow: hidden; height: 100%; }
        #graph-container { flex: 1; position: relative; }
        #node-info-panel { width: 350px; background: var(--panel); border-left: 1px solid #1e293b; padding: 20px; display: none; flex-direction: column; overflow-y: auto; z-index: 3001; }
        .node-info-row { margin-bottom: 12px; display: flex; flex-direction: column; }
        .node-info-row label { font-size: 10px; color: var(--accent); font-weight: bold; text-transform: uppercase; margin-bottom: 2px; }
        .node-info-row span { font-size: 13px; color: white; word-break: break-all; font-family: monospace; }

        #ip-graph-overlay { position: fixed; inset: 0; background: rgba(7, 10, 19, 0.98); z-index: 3100; display: none; flex-direction: column; }
        #ip-graph-main-container { display: flex; flex: 1; overflow: hidden; height: 100%; }
        #ip-graph-container { flex: 1; position: relative; }
        #ip-node-info-panel { width: 380px; background: var(--panel); border-left: 1px solid #1e293b; padding: 20px; display: none; flex-direction: column; overflow-y: auto; z-index: 3101; }

        .top-nav { background: var(--panel); padding: 0 20px; min-height: 70px; display: flex; align-items: center; gap: 14px; border-bottom: 1px solid #1e293b; }
        .header-logo-area { display: flex; align-items: center; gap: 15px; min-width: 0; flex: 0 0 auto; max-width: 260px; }
        .header-logo { width: 40px; border-radius: 50%; border: 2px solid var(--accent); }
        .header-title { font-weight: 800; font-size: 16px; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase; }
        .header-title span { color: white; }
        .top-nav-spacer { flex: 0 0 24px; }

        .nav-center { flex: 1; min-width: 0; display: flex; justify-content: flex-start; align-items: stretch; height: 100%; gap: 5px; overflow-x: auto; overflow-y: hidden; scrollbar-width: thin; }
        .nav-center::-webkit-scrollbar { height: 6px; }
        .nav-center::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 999px; }
        .nav-btn { background: transparent; border: none; color: #94a3b8; padding: 0 20px; height: 100%; cursor: pointer; font-weight: 700; font-size: 13px; border-bottom: 3px solid transparent; transition: 0.3s; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; white-space: nowrap; flex: 0 0 auto; }
        .nav-icon { display: inline-flex; align-items: center; justify-content: center; width: 16px; font-size: 14px; line-height: 1; }
        .nav-btn:hover { color: white; background: rgba(255,255,255,0.02); }
        .nav-btn.active { color: var(--accent); border-bottom-color: var(--accent); background: linear-gradient(180deg, rgba(0, 229, 255, 0.0) 0%, rgba(0, 229, 255, 0.1) 100%); }
        
        .tab-panel { display: none; padding: 25px; height: 100%; min-height: 0; overflow-y: auto; overflow-x: hidden; transition: all 0.5s ease; }
        .tab-panel.active { display: flex; flex-direction: column; animation: slideIn 0.3s; }
        
        .search-box { display: flex; align-items: stretch; gap: 10px; margin-bottom: 20px; background: var(--panel); padding: 15px 64px 15px 15px; border-radius: 12px; border: 1px solid #1e293b; position: relative; transition: all 0.5s ease; width: 100%; box-sizing: border-box; }
        .search-box.center-search { margin-top: min(20vh, 160px); max-width: 680px; margin-left: auto; margin-right: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.6); transform: none; }
        
        .main-input { flex: 1; min-width: 0; background: var(--bg); border: 1px solid #1e293b; color: white; padding: 12px; border-radius: 8px; outline: none; font-size: 14px; }
        .loader-wrap { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); width: 52px; height: 52px; display: none; align-items: center; justify-content: center; pointer-events: none; }
        .loader-wrap svg { display: block; width: 48px; height: 48px; }
        .loader-ring-track { stroke: #1e293b; }
        .loader-ring-progress { stroke: var(--accent); transition: stroke-dashoffset 0.25s ease; filter: drop-shadow(0 0 4px rgba(0, 229, 255, 0.45)); }
        .loader-pct { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; color: var(--accent); letter-spacing: -0.5px; }
        
        .res-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; padding-bottom: 40px; align-items: start; width: 100%; min-width: 0; opacity: 0; transition: opacity 0.5s ease; }
        .res-grid.show { opacity: 1; }
        .res-grid.wide { max-width: min(1200px, 100%); margin: 0 auto; grid-template-columns: minmax(0, 1fr); }

        .presence-panel { background: var(--panel); border: 1px solid #1e293b; border-radius: 10px; padding: 18px; }
        .presence-title { color: white; font-weight: 900; letter-spacing: 0.5px; text-transform: uppercase; font-size: 12px; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center; }
        .presence-sub { color:#94a3b8; font-family: monospace; font-size: 11px; }
        .presence-list { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
        .presence-item { background: var(--bg); border: 1px solid #1e293b; border-radius: 8px; padding: 10px; display:flex; align-items:center; justify-content:space-between; gap: 10px; }
        .presence-left { display:flex; flex-direction:column; gap:2px; min-width:0; }
        .presence-name { color:white; font-weight:800; font-size: 12px; text-transform: uppercase; }
        .presence-meta { color:#94a3b8; font-family: monospace; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .presence-dot { width:10px; height:10px; border-radius:999px; box-shadow: 0 0 6px currentColor; flex:0 0 auto; }
        .presence-dot.green { background: var(--success); color: var(--success); }
        .presence-dot.red { background: var(--danger); color: var(--danger); }
        .presence-dot.yellow { background: var(--secondary); color: var(--secondary); }
        
        .card { background: var(--panel); border-radius: 10px; border: 1px solid #1e293b; overflow: hidden; transition: 0.3s; position: relative; display: flex; flex-direction: column; }
        
        /* CARD IN EVIDENZA */
        .card.highlight { border: 2px solid var(--accent); box-shadow: 0 0 25px rgba(0, 229, 255, 0.25); }
        .card.inactive { opacity: 0.6; filter: grayscale(50%); order: 99; }
        .card.inactive:hover { opacity: 1; filter: grayscale(0%); }
        
        .card-header { padding: 12px 15px; display: flex; align-items: center; gap: 12px; background: rgba(255,255,255,0.02); cursor: pointer; border-bottom: 1px solid #1e293b; }
        .card.open .card-header { background: #1e293b; }
        .pfp { width: 42px; height: 42px; border-radius: 8px; object-fit: cover; background: var(--bg); border: 1px solid #1e293b; padding: 2px; }
        
        .status-dot { width: 8px; height: 8px; border-radius: 50%; position: absolute; top: 15px; right: 40px; box-shadow: 0 0 5px currentColor; }
        .s-green { background: var(--success); color: var(--success); }
        .s-red { background: var(--danger); color: var(--danger); }
        .s-yellow { background: var(--secondary); color: var(--secondary); }
        
        /* VISIBILITA' DATI SOCIAL MIGLIORATA */
        .card-body { padding: 18px; font-size: 14px; color: #e2e8f0; background: var(--bg); flex: 1; display: none; }
        .card.open .card-body { display: block; }
        
        .data-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1e293b; padding: 10px 0; align-items: flex-start; }
        .data-row label { color: var(--accent); font-weight: 800; font-size: 11px; text-transform: uppercase; width: 35%; margin-top: 2px; }
        .data-row span { color: #ffffff; text-align: right; width: 65%; word-wrap: break-word; white-space: pre-wrap; line-height: 1.5; font-weight: 500; }
        
        /* --- NUOVE CLASSI PER IL PANNELLO CRYPTO --- */
        .tx-list { margin-top: 15px; }
        .tx-list h4 { color: white; border-bottom: 1px solid #1e293b; padding-bottom: 5px; margin-bottom: 10px; font-size: 11px; text-transform: uppercase; }
        .tx-item { display: flex; justify-content: space-between; align-items: center; background: var(--bg); padding: 8px; border-radius: 6px; margin-bottom: 8px; border: 1px solid #1e293b; }
        .tx-item span { color: #94a3b8; font-family: monospace; font-size: 11px; }
        .tx-item-actions { display: flex; gap: 5px; }
        .tx-btn { border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 9px; font-weight: bold; }
        .tx-btn.copy { background: var(--success); color: #000; }
        .tx-btn.analyze { background: var(--secondary); color: #fff; }
        
        .btn-link { display: block; text-align: center; margin-top: 10px; padding: 8px; background: rgba(0, 229, 255, 0.1); color: var(--accent); text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 11px; transition: 0.2s; cursor: pointer; border: none; width: 100%; box-sizing: border-box; }
        .btn-link:hover { background: rgba(0, 229, 255, 0.2); }
        .btn-add-report { width: 100%; background: var(--success); color: #000; border: none; padding: 8px; margin-top: 5px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 10px; box-sizing: border-box; transition: 0.2s; }
        .btn-add-report:hover { filter: brightness(1.2); }

        .graph-nav { padding: 15px; background: var(--panel); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; }

        #tg-monitor-modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--panel); border: 1px solid var(--accent); padding: 20px; border-radius: 12px; z-index: 10000; width: 600px; max-width: 90vw; max-height: 80vh; flex-direction: column; text-align: left; box-shadow: 0 0 30px rgba(0, 229, 255, 0.4); }
        .tg-modal-header { display: flex; align-items: center; gap: 15px; border-bottom: 1px solid #1e293b; padding-bottom: 15px; margin-bottom: 15px; }
        .tg-modal-header img { width: 80px; height: 80px; border-radius: 50%; border: 2px solid var(--accent); }
        .tg-modal-info h3 { margin: 0; color: white; font-size: 20px; }
        .tg-modal-info p { margin: 5px 0 0 0; color: var(--secondary); font-size: 13px; }
        #tg-status-indicator { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; margin-top: 8px; }
        .tg-online { background: rgba(0, 255, 0, 0.2); color: #0f0; }
        .tg-offline { background: rgba(255, 0, 0, 0.2); color: #f00; }
        .tg-standby { background: rgba(255, 165, 0, 0.2); color: #ffa500; }
        #tg-log-container { flex: 1; overflow-y: auto; background: var(--bg); padding: 10px; border-radius: 6px; border: 1px solid #1e293b; font-family: monospace; font-size: 12px; color: #cbd5e1; margin-bottom: 15px; min-height: 200px; }
        #tg-log-container div { margin-bottom: 5px; }
        #tg-log-container .log-alert { color: var(--danger); font-weight: bold; }
        #tg-log-container .log-online { color: #0f0; }
        #tg-log-container .log-offline { color: #f00; }
        .tg-modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
        #tg-monitor-close { position: absolute; top: 15px; right: 20px; cursor: pointer; color: white; font-size: 20px; }
        .hist-tg-status { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-left: 5px; }
        .hist-tg-active { background: #f00; box-shadow: 0 0 5px #f00; animation: blink 1.5s infinite; }
        .hist-tg-done { background: #0f0; box-shadow: 0 0 5px #0f0; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

        @media (max-width: 1180px) {
            .login-card { grid-template-columns: 1fr; height: min(940px, 94vh); }
            .author-pane { display: none; }
            #dashboard { flex-direction: column; }
            #sidebar { width: 100%; min-width: 0; max-height: 230px; border-right: none; border-bottom: 1px solid #1e293b; }
            .top-nav { padding: 10px 14px; }
            .header-logo-area { max-width: 180px; }
            .top-nav-spacer { display: none; }
        }

        @media (max-width: 820px) {
            body { overflow: auto; }
            .tab-panel { padding: 16px; }
            .search-box { padding: 12px 12px 70px 12px; flex-wrap: wrap; }
            .search-box.center-search { max-width: 100%; margin-top: 32px; }
            .action-btn { width: 100%; min-height: 42px; }
            .loader-wrap { top: auto; bottom: 10px; right: 10px; transform: none; }
            .res-grid { grid-template-columns: minmax(0, 1fr); }
            .data-row { flex-direction: column; gap: 6px; }
            .data-row label, .data-row span { width: 100%; text-align: left; }
            .tg-modal-header { flex-direction: column; align-items: flex-start; }
        }
        </style></head>
<body>
    <div id="overlay" onclick="closeAllCards()"></div>
    
    <div id="tg-monitor-modal" style="display:none;">
        <div id="tg-monitor-close" onclick="closeTgMonitor()">X</div>
        <div class="tg-modal-header">
            <img id="tg-monitor-pfp" src="" alt="PFP">
            <div class="tg-modal-info">
                <h3 id="tg-monitor-name">Nome Utente</h3>
                <p id="tg-monitor-desc">Dettagli target</p>
                <div id="tg-status-indicator" class="tg-offline">Status: Sconosciuto</div>
                <div id="tg-last-seen" style="margin-top:5px; color:var(--accent); font-size: 12px;">Ultimo accesso: ---</div>
            </div>
        </div>
        <h4 style="margin: 0 0 10px 0; color: white; font-size: 14px;">Event Log & Intelligence</h4>
        <div id="tg-log-container"></div>
        <div class="tg-modal-actions">
            <button class="action-btn" id="tg-btn-stop" onclick="stopTgMonitor()" style="background:var(--danger); color:white; display:none;">FERMA MONITORAGGIO</button>
            <button class="action-btn" id="tg-btn-report" onclick="downloadTgReport()" style="background:var(--success); color:#000;"> SCARICA REPORT INTELLIGENCE</button>
        </div>
        </div>

        <div id="scrape-modal" style="display:none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--panel); border: 1px solid var(--accent); padding: 20px; border-radius: 12px; z-index: 10000; width: 400px; max-width: 90vw; flex-direction: column; text-align: left; box-shadow: 0 0 30px rgba(0, 229, 255, 0.4);">
        <div style="position: absolute; top: 10px; right: 15px; cursor: pointer; font-size: 20px; color: var(--accent);" onclick="closeScrapePrompt()">X</div>
        <h3 style="margin-top:0; color:var(--accent);">Opzioni Download</h3>
        <p id="scrape-target-info" style="color:white; margin-bottom:15px; font-size:14px;"></p>

        <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:20px; color: white;">
            <label><input type="checkbox" id="scrape-opt-dati" value="dati"> Solo Dati</label>
            <label><input type="checkbox" id="scrape-opt-media" value="media"> Solo Media</label>
            <label><input type="checkbox" id="scrape-opt-link" value="link"> Solo Link</label>
            <label><input type="checkbox" id="scrape-opt-follower" value="follower"> Solo Follower</label>
            <label><input type="checkbox" id="scrape-opt-following" value="following"> Solo Following</label>
            <label><input type="checkbox" id="scrape-opt-tutto" value="tutto" checked> Scarica Tutto</label>
        </div>

        <button class="action-btn" onclick="startScraping()" style="background:var(--accent); color:#000; font-weight:bold; border:none; padding:10px; border-radius:5px; cursor:pointer; font-family:'Fira Code', monospace; width:100%;">AVVIA</button>
        </div>

        <img id="hover-zoom-img" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); max-width:85vw; max-height:85vh; z-index:9999; border-radius:15px; box-shadow: 0 0 0 100vmax rgba(0,0,0,0.85), 0 0 50px rgba(0,229,255,0.4); pointer-events:none; object-fit:contain;">    
    <div id="graph-overlay">
        <div class="graph-nav">
            <div style="display: flex; flex-direction: column;">
                <div style="font-weight:bold; color:var(--accent);"> ANALISI VISUALE NETWORK</div>
                <div id="graph-address-path" style="color: #94a3b8; font-family: monospace; font-size: 11px; margin-top: 5px;"></div>
            </div>
            <button class="action-btn" onclick="closeGraph()" style="background:var(--danger); color:white; height:30px;">CHIUDI X</button>
        </div>
        <div id="graph-main-container">
            <div id="graph-container"></div>
            <div id="node-info-panel">
                <h3 style="color:var(--accent); margin-top: 0;">Analisi Nodo</h3>
                <div id="node-details-content"></div>
                <canvas id="node-balance-chart" style="margin-top:20px; max-height: 200px;"></canvas>
            </div>
        </div>
    </div>

    <div id="ip-graph-overlay">
        <div class="graph-nav">
            <div style="display: flex; flex-direction: column;">
                <div style="font-weight:bold; color:var(--accent);"> IP NETWORK (DOMINIO & IP SERVICES)</div>
                <div id="ip-graph-domain" style="color: #94a3b8; font-family: monospace; font-size: 11px; margin-top: 5px;"></div>
            </div>
            <button class="action-btn" onclick="closeIpGraph()" style="background:var(--danger); color:white; height:30px;">CHIUDI X</button>
        </div>
        <div id="ip-graph-main-container">
            <div id="ip-graph-container"></div>
            <div id="ip-node-info-panel">
                <h3 style="color:var(--accent); margin-top: 0;">Dettagli IP</h3>
                <div id="ip-node-details-content"></div>
            </div>
        </div>
    </div>
    
    <div id="login-view">
        <div class="login-card">
            <div class="login-form">
                <div class="section-title"> Instagram Session</div>
                <input type="password" id="sid" class="login-input" value="{{creds.sid}}" placeholder="SessionID Cookie...">
                <div class="section-title" style="margin-top:20px; color:var(--secondary)"> TikTok Session</div>
                <input type="password" id="tiktok_sid" class="login-input" value="{{creds.tiktok_sid}}" placeholder="TikTok sessionid...">
                <div class="section-title" style="margin-top:20px; color:var(--secondary)"> Telegram Live</div>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="tg_id" class="login-input" value="{{creds.tg_id}}" placeholder="API ID" style="flex:1">
                    <input type="password" id="tg_hash" class="login-input" value="{{creds.tg_hash}}" placeholder="API HASH" style="flex:1">
                </div>
                <input type="text" id="phone" class="login-input" value="{{creds.my_phone}}" placeholder="+39...">
                <button id="btn-send-code" onclick="sendTgCode()" class="btn-otp">RICEVI CODICE OTP</button>
                <div id="otp-area" style="display:none; border:1px dashed var(--secondary); padding:10px; border-radius:8px; margin-bottom:10px; background:rgba(59, 130, 246, 0.1);">
                    <input type="text" id="otp_code" class="login-input" placeholder="Codice Telegram..." style="text-align:center;">
                    <button onclick="verifyTgCode()" class="action-btn" style="background:var(--secondary); color:white; width:100%;">CONFERMA</button>
                </div>
                <div class="section-title" style="margin-top:20px; color:var(--success)"> Shodan API</div>
                <input type="password" id="shodan_key" class="login-input" value="{{creds.shodan_key}}" placeholder="Shodan API Key (Basic)...">
                
                <button onclick="doLogin()" class="action-btn" style="margin-top:auto; width:100%;">ENTRA NELLA DASHBOARD</button>
            </div>
            
            <div class="author-pane">
                <div class="logo-ring"><img src="{{logo_url}}" class="logo-img"></div>
                <h1 class="app-title">CScorza Intelligence</h1>
                <div class="app-ver">IntelOSINT v.1</div>
                
                <div class="auth-links">
                    {% for c in author_info %}
                    <div class="auth-card" onclick="window.open('{{c.url}}', '_blank')" style="border-left: 4px solid {{c.bg}}">
                        <div class="auth-icon-wrap {{ 'glow' if (c.label == 'Website' or 'Twitter' in c.label or c.label == 'GitHub') else '' }}">
                            <img src="{{c.icon}}" class="auth-icon" alt="{{c.label}}">
                        </div>
                        <div class="auth-text">
                            <h4>{{c.label}}</h4>
                            <span style="color:white">{{c.val}}</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="donation-section">
                    <div class="donation-title">Supporta il Progetto</div>
                    {% for d in donations %}
                    <div class="donation-card" onclick="copyText('{{d.addr}}')" title="Clicca per copiare l'indirizzo">
                        <div class="donation-info">
                            <span class="donation-curr">Donazione in {{d.curr}}</span>
                            <span class="donation-addr">{{d.addr}}</span>
                        </div>
                        <div class="donation-icon">-></div>
                    </div>
                    {% endfor %}
                </div>

            </div>
        </div>
    </div>

    <div id="dashboard">
        <div id="sidebar">
            <div class="history-head">
                <h4>Target history</h4>
                <label class="hist-icons-toggle" title="Mostra o nascondi le icone nella lista">
                    <input type="checkbox" id="hist-show-icons" checked> Icone
                </label>
            </div>
            <div id="history-list"></div>
            <button class="action-btn" onclick="location.reload()" style="background:#1e293b; color:white; width:100%; margin-bottom:10px;"> HOME / LOGOUT</button>
            <button onclick="exportReport()" class="action-btn" style="width:100%; background:var(--success); color:#000;"> GENERA REPORT PDF</button>
        </div>
        <div id="main-area">
            <div class="top-nav">
                <div class="header-logo-area"><img src="{{logo_url}}" class="header-logo"><div class="header-title">CScorza <span style="color:var(--accent)">IntelOSINT</span></div></div>
                <div class="nav-center">
                    <button class="nav-btn active" onclick="setTab('social', event)"><span class="nav-icon">👥</span> Social</button>
                    <button class="nav-btn" onclick="setTab('webdork', event)"><span class="nav-icon">🕸</span> WEB Dork</button>
                    <button class="nav-btn" onclick="setTab('messaging', event)"><span class="nav-icon">📞</span> Phone</button>
                    <button class="nav-btn" onclick="setTab('gdrive', event)"><span class="nav-icon">☁️</span> Doc GDrive</button>
                    <button class="nav-btn" onclick="setTab('finance', event)"><span class="nav-icon">💱</span> Financial</button>
                    <button class="nav-btn" onclick="setTab('domain', event)"><span class="nav-icon">🌐</span> Domain</button>
                </div>
                <div class="top-nav-spacer"></div> 
            </div>

            <div id="tab-social" class="tab-panel active">
                <div class="search-box center-search" id="sb-social">
                    <input type="text" id="input-social" class="main-input" placeholder="Username (es. cscorza) o Nome (es. Mario Rossi)..." onkeypress="if(event.key === 'Enter') runSearch('global', 'input-social')">
                    <button class="action-btn" onclick="runSearch('global', 'input-social')">Global Scan</button>
                    <div class="loader-wrap" id="loader-social" aria-hidden="true">
                        <svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true">
                            <circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/>
                            <circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/>
                        </svg>
                        <span class="loader-pct" id="loader-social-pct">0%</span>
                    </div>
                </div>
                <div id="res-social" class="res-grid"></div>
            </div>

            <div id="tab-webdork" class="tab-panel">
                <div class="search-box center-search" id="sb-webdork">
                    <input type="text" id="input-webdork" class="main-input" placeholder="Parole chiave, email, dorks..." onkeypress="if(event.key === 'Enter') runDorkSearch()">
                    <button class="action-btn" onclick="runDorkSearch()" style="background:var(--accent); color:white;">Dork Search</button>
                    <div class="loader-wrap" id="loader-webdork" aria-hidden="true">
                        <svg width="48" height="48" viewBox="0 0 48 48"><circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/><circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/></svg>
                        <span class="loader-pct" id="loader-webdork-pct">0%</span>
                    </div>
                </div>
                
                <div id="dork-preset-container" style="display:flex; justify-content:center; margin-bottom:20px;">
                    <select id="dork-presets" class="main-input" style="max-width:600px; background:#0d1326; border:1px solid var(--accent); color:var(--accent); font-weight:bold; cursor:pointer;" onchange="if(this.value) document.getElementById('input-webdork').value = this.value;">
                        <option value=""> Filtri Rapidi: Seleziona una Dork Preimpostata...</option>
                        <option value='intitle:"index of" "passwords"'> Directory Listing: Passwords</option>
                        <option value='ext:sql intext:password | pass | pwd'> Database Leaks: File SQL</option>
                        <option value='ext:log "software" OR "server"'> File di Log Esposti</option>
                        <option value='inurl:admin inurl:login'> Pannelli di Amministrazione</option>
                        <option value='ext:pdf intext:"confidential" OR "strictly confidential"'> Documenti Confidenziali (PDF)</option>
                        <option value='inurl:wp-config.txt OR inurl:env'>Config File (WP/ENV)</option>
                        <option value='site:pastebin.com "password"'> Pastebin: Passwords</option>
                        <option value='site:t.me/joinchat/'> Canali/Gruppi Telegram Nascosti</option>
                        <option value='intitle:"webcamXP 5"'> Webcam non protette (WebcamXP)</option>
                    </select>
                </div>

                <div id="dork-filters" style="display:none; justify-content:center; gap:10px; margin-bottom:20px; flex-wrap:wrap;">
                    <button class="action-btn dork-filter" data-engine="All" data-color="#ffffff" onclick="setDorkFilter('All')" style="background:#1e293b; color:#ffffff; border:1px solid #ffffff; opacity:1; box-shadow:0 0 10px #ffffff;">Tutti</button>
                    <button class="action-btn dork-filter" data-engine="Google" data-color="#4285F4" onclick="setDorkFilter('Google')" style="background:#1e293b; color:#4285F4; border:1px solid #4285F4; opacity:0.5;">Google</button>
                    <button class="action-btn dork-filter" data-engine="Yandex" data-color="#FFCC00" onclick="setDorkFilter('Yandex')" style="background:#1e293b; color:#FFCC00; border:1px solid #FFCC00; opacity:0.5;">Yandex</button>
                </div>
                
                <div id="res-webdork" class="res-grid wide"></div>
            </div>

            <div id="tab-finance" class="tab-panel">
                <div class="search-box center-search" id="sb-finance">
                    <input type="text" id="input-fin" class="main-input" placeholder="Wallet Crypto, Revolut Tag, PayPal..." onkeypress="if(event.key === 'Enter') runSearch('finance', 'input-fin')">
                    <button class="action-btn" onclick="runSearch('finance', 'input-fin')" style="background:var(--secondary); color:white;">Scan</button>
                    <div class="loader-wrap" id="loader-finance" aria-hidden="true">
                        <svg width="48" height="48" viewBox="0 0 48 48"><circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/><circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/></svg>
                        <span class="loader-pct" id="loader-finance-pct">0%</span>
                    </div>
                </div>
                <div id="res-finance" class="res-grid wide"></div>
            </div>
            
            <div id="tab-messaging" class="tab-panel">
                 <div class="search-box center-search" id="sb-messaging"><input type="text" id="input-msg" class="main-input" placeholder="Numero (+39...)" onkeypress="if(event.key === 'Enter') runSearch('messaging', 'input-msg')"><button class="action-btn" onclick="runSearch('messaging', 'input-msg')">Scan</button><div class="loader-wrap" id="loader-messaging" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 48 48"><circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/><circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/></svg><span class="loader-pct" id="loader-messaging-pct">0%</span></div></div>
                <div id="res-messaging" class="res-grid wide"></div>
            </div>

            <div id="tab-gdrive" class="tab-panel">
                 <div class="search-box center-search" id="sb-gdrive"><input type="text" id="input-gdrive" class="main-input" placeholder="Link Google Docs / Sheets / Drive pubblico..." onkeypress="if(event.key === 'Enter') runSearch('gdrive', 'input-gdrive')"><button class="action-btn" onclick="runSearch('gdrive', 'input-gdrive')" style="background:#34a853; color:white;">Analizza</button><div class="loader-wrap" id="loader-gdrive" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 48 48"><circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/><circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/></svg><span class="loader-pct" id="loader-gdrive-pct">0%</span></div></div>
                <div id="res-gdrive" class="res-grid wide"></div>
            </div>

            <div id="tab-domain" class="tab-panel">
                 <div class="search-box center-search" id="sb-domain"><input type="text" id="input-domain" class="main-input" placeholder="Domain.com..." onkeypress="if(event.key === 'Enter') runSearch('domain', 'input-domain')"><button class="action-btn" onclick="runSearch('domain', 'input-domain')">WHOIS</button><div class="loader-wrap" id="loader-domain" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 48 48"><circle class="loader-ring-track" cx="24" cy="24" r="20" fill="none" stroke-width="3"/><circle class="loader-ring-progress" cx="24" cy="24" r="20" fill="none" stroke-width="3" stroke-linecap="round" transform="rotate(-90 24 24)" stroke-dasharray="125.664" stroke-dashoffset="125.664" data-c="125.664"/></svg><span class="loader-pct" id="loader-domain-pct">0%</span></div></div>
                <div id="res-domain" class="res-grid wide"></div>
            </div>
        </div>
    </div>

    <script>
        const socialIcons = {{social_map|tojson}};
        const cryptoIconsMap = {{crypto_map|tojson}};
        let historyDB = [];
        let network = null;
        let sideChart = null;
        
        // --- NUOVE VARIABILI PER IL GRAFICO ---
        let graphNodes = null;
        let graphEdges = null;
        let currentJumps = 0;
        const MAX_JUMPS = 3;

        function copyText(text) { navigator.clipboard.writeText(text).then(() => alert("Copiato!")); }

        function setRingProgress(loaderId, pct) {
            const wrap = document.getElementById(loaderId);
            if (!wrap) return;
            const pctEl = wrap.querySelector('.loader-pct');
            const ring = wrap.querySelector('.loader-ring-progress');
            const p = Math.min(100, Math.max(0, Math.round(pct)));
            if (pctEl) pctEl.textContent = p + '%';
            if (ring) {
                const C = parseFloat(ring.getAttribute('data-c')) || 125.664;
                ring.style.strokeDashoffset = String(C * (1 - p / 100));
            }
        }

        function showLoaderRing(loaderId) {
            const wrap = document.getElementById(loaderId);
            if (!wrap) return;
            setRingProgress(loaderId, 0);
            wrap.style.display = 'flex';
        }

        function hideLoaderRing(loaderId) {
            const wrap = document.getElementById(loaderId);
            if (!wrap) return;
            wrap.style.display = 'none';
            setRingProgress(loaderId, 0);
        }

        async function renderCardsOneByOne(res, gridId) {
            if (res === null || res === undefined) return;
            const list = Array.isArray(res) ? res : [res];
            for (let i = 0; i < list.length; i++) {
                if (!list[i]) continue;
                renderCard(list[i], gridId);
                await new Promise(function(r) { requestAnimationFrame(r); });
            }
        }

        function setTab(name, evt) {
            document.querySelectorAll('.tab-panel').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
            const panel = document.getElementById('tab-' + name);
            if (panel) {
                panel.classList.add('active');
                panel.scrollTop = 0;
            }
            if (evt && evt.currentTarget) {
                evt.currentTarget.classList.add('active');
            }
        }

        async function doLogin() {
            await fetch('/api/save_creds', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
                sid: document.getElementById('sid').value, tiktok_sid: document.getElementById('tiktok_sid').value, tg_id: document.getElementById('tg_id').value,
                tg_hash: document.getElementById('tg_hash').value, my_phone: document.getElementById('phone').value,
                shodan_key: document.getElementById('shodan_key').value
            })});
            document.getElementById('login-view').style.display='none';
            document.getElementById('dashboard').style.display='flex';
        }

        let allDorkResults = [];
        let currentDorkFilter = 'All';

        function setDorkFilter(engine) {
            currentDorkFilter = engine;
            document.querySelectorAll('.dork-filter').forEach(btn => {
                if (btn.dataset.engine === engine) {
                    btn.style.opacity = '1';
                    btn.style.boxShadow = '0 0 10px ' + btn.dataset.color;
                } else {
                    btn.style.opacity = '0.5';
                    btn.style.boxShadow = 'none';
                }
            });
            renderDorkResults();
        }

        async function runDorkSearch() {
            const t = document.getElementById('input-webdork').value.trim(); 
            if(!t) return;
            
            document.getElementById('sb-webdork').classList.remove('center-search');
            document.getElementById('res-webdork').classList.remove('show');
            document.getElementById('dork-filters').style.display = 'none';
            showLoaderRing('loader-webdork');

            const container = document.getElementById('res-webdork');
            container.innerHTML = '';
            container.classList.add('show');

            try {
                const req = await fetch('/api/web_dork', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: t})
                });
                const data = await req.json();
                hideLoaderRing('loader-webdork');
                
                if(data.results && data.results.length > 0) {
                    allDorkResults = data.results;
                    document.getElementById('dork-filters').style.display = 'flex';
                    setDorkFilter('All');
                } else {
                    allDorkResults = [];
                    container.innerHTML = '<div style="text-align:center; width:100%; color:#a1a1aa; padding:20px;">Nessun risultato trovato.</div>';
                }
            } catch(e) {
                hideLoaderRing('loader-webdork');
                container.innerHTML = '<div style="text-align:center; width:100%; color:var(--danger); padding:20px;">Errore durante la ricerca WEB Dork.</div>';
            }
        }

        function renderDorkResults() {
            const container = document.getElementById('res-webdork');
            container.innerHTML = '';
            container.style.display = 'block'; 

            const filtered = currentDorkFilter === 'All' ? allDorkResults : allDorkResults.filter(r => r.engine === currentDorkFilter);

            if(filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; width:100%; color:#a1a1aa; padding:20px;">Nessun risultato per questo motore di ricerca.</div>';
                return;
            }

            filtered.forEach(res => {
                const engineColor = {
                    'Google': '#4285F4', 'Yandex': '#FFCC00'
                }[res.engine] || '#64748b';
                
                const item = document.createElement('div');
                item.className = 'fade-in';
                item.style.cssText = 'margin-bottom: 25px; padding: 15px; background: linear-gradient(90deg, rgba(13,19,38,1) 0%, rgba(13,19,38,0.4) 100%); border-radius: 8px; border-left: 5px solid ' + engineColor + '; box-shadow: 0 4px 10px rgba(0,0,0,0.5);';
                item.innerHTML = `
                    <div style="font-size:12px; color:${engineColor}; font-weight:bold; margin-bottom:5px; text-transform:uppercase; letter-spacing:1px; display:flex; align-items:center; gap:8px;">
                        <span style="background:${engineColor}20; padding:3px 8px; border-radius:4px;"> ${res.engine}</span> 
                        <span style="color:#64748b; font-weight:normal; text-transform:none; font-family:monospace; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${res.url}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <a href="${res.url}" target="_blank" style="color:#60a5fa; font-size:18px; text-decoration:none; font-weight:600; display:inline-block; transition:0.2s;" onmouseover="this.style.color='${engineColor}'" onmouseout="this.style.color='#60a5fa'">
                            ${res.title}
                        </a>
                    </div>
                    <div style="font-size:14px; color:#e2e8f0; line-height:1.6;">
                        ${res.snippet || 'Nessuna anteprima disponibile dal motore di ricerca.'}
                    </div>
                `;
                container.appendChild(item);
            });
        }

        async function runSearch(mode, inputId) {
            const t = document.getElementById(inputId).value.trim(); if(!t) return;
            const loaderId = 'loader-'+ (mode==='global'?'social':mode);
            const gridId = 'res-' + (mode==='global'?'social':mode);
            const searchBoxId = 'sb-' + (mode==='global'?'social':mode);
            
            document.getElementById(searchBoxId).classList.remove('center-search');
            document.getElementById(gridId).classList.remove('show');
            showLoaderRing(loaderId);
            
            const container = document.getElementById(gridId);
            container.innerHTML = ''; // Pulisce i risultati precedenti
            container.classList.add('show'); // Mostra la griglia per veder apparire le card

            if(mode === 'global') {
                const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t);
                const platforms = Object.keys(socialIcons);
                let totalJobs = platforms.length;
                if (isEmail) totalJobs += 1;
                let completedRequests = 0;

                function bumpProgress() {
                    completedRequests++;
                    const pct = totalJobs ? Math.min(100, Math.round((completedRequests / totalJobs) * 100)) : 100;
                    setRingProgress(loaderId, pct);
                    if (completedRequests >= totalJobs) hideLoaderRing(loaderId);
                }

                if (isEmail) {
                    fetch('/api/search', {
                        method:'POST',
                        headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({target:t, platform:'holehe'})
                    })
                    .then(r => r.json())
                    .then(async function(res) { await renderCardsOneByOne(res, gridId); })
                    .catch(err => console.error('Errore Holehe:', err))
                    .finally(bumpProgress);
                }

                platforms.forEach(p => {
                    fetch('/api/search', {
                        method:'POST',
                        headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({target:t, platform:p})
                    })
                    .then(r => r.json())
                    .then(async function(res) { await renderCardsOneByOne(res, gridId); })
                    .catch(err => console.error('Errore su ' + p + ':', err))
                    .finally(bumpProgress);
                });
                
            } else {
                setRingProgress(loaderId, 5);
                try {
                    const r = await fetch('/api/search', {
                        method:'POST',
                        headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({target:t, platform:mode})
                    });
                    setRingProgress(loaderId, 85);
                    const d = await r.json();
                    if (mode === 'messaging' && Array.isArray(d)) {
                        const base = d.find(x => x && x.type === 'Messaging');
                        const ign = d.filter(x => x && typeof x.type === 'string' && x.type.startsWith('Ignorant:'));

                        if (base) await renderCardsOneByOne(base, gridId);
                        if (ign.length > 0) renderPhonePresencePanel(t, ign, gridId);
                    } else {
                        await renderCardsOneByOne(d, gridId);
                    }
                } catch(e) {
                    console.error("Errore ricerca singola:", e);
                }
                setRingProgress(loaderId, 100);
                hideLoaderRing(loaderId);
            }
        }

        function renderPhonePresencePanel(phone, ignorantResults, containerId) {
            const div = document.createElement('div');
            div.className = 'presence-panel';

            const items = (ignorantResults || []).map(r => {
                const svc = (r.type || '').replace('Ignorant:', '').trim() || 'unknown';
                let state = 'red';
                if (r.status_code === 200) state = 'green';
                else if (r.status_code === 206) state = 'yellow';
                const metaParts = [];
                if (r.info && r.info.Domain) metaParts.push(r.info.Domain);
                if (r.info && r.info.Method) metaParts.push(r.info.Method);
                if (r.info && r.info.Status) metaParts.push(r.info.Status);
                return { svc, state, meta: metaParts.join(' | ') };
            });

            div.innerHTML = `
                <div class="presence-title">
                    <span>Presenza numero sui servizi</span>
                    <span class="presence-sub">${phone}</span>
                </div>
                <div class="presence-list">
                    ${items.map(i => `
                        <div class="presence-item">
                            <div class="presence-left">
                                <div class="presence-name">${i.svc}</div>
                                <div class="presence-meta">${i.meta}</div>
                            </div>
                            <div class="presence-dot ${i.state}"></div>
                        </div>
                    `).join('')}
                </div>
            `;

            document.getElementById(containerId).appendChild(div);
        }
        
        function downloadCSV(entityId) {
            window.location.href = `/api/tg/export_participants?entity=${entityId}`;
        }

        function renderCard(d, containerId) {
            const uniqueId = 'chart_' + Math.random().toString(36).substr(2, 9);
            
            let dotColor = 's-yellow';
            let highlightClass = '';
            const socialPlatforms = Object.keys(socialIcons).reduce((acc, item) => { acc[item] = true; return acc; }, {});
            const isSocial = !!socialPlatforms[d.type];
            const isFoundFlag = d.__found === true;
            const statusCodeRaw = Number(d.status_code);
            const statusCode = Number.isFinite(statusCodeRaw) ? statusCodeRaw : 200;
            const signalKeys = [
                " ID Numerico", "Nome", "Nome Profilo", " Utente", " Canale",
                " Bio", " Followers", " Follower", "Karma", "Karma Totale", "Handle", "ID"
            ];
            let hasStrongSignal = false;
            if (d.info && typeof d.info === 'object') {
                for (let i = 0; i < signalKeys.length; i++) {
                    const k = signalKeys[i];
                    if (Object.prototype.hasOwnProperty.call(d.info, k) && d.info[k] && String(d.info[k]).trim() !== "") {
                        hasStrongSignal = true;
                        break;
                    }
                }
            }

            const statusText = d.info && d.info.Status ? String(d.info.Status).toLowerCase() : "";
            const isNegative = (text) => (
                text.includes(" non trovato") ||
                text.includes("non trovato") ||
                text.includes("non attivo") ||
                text.includes("richiede login") ||
                text.includes("non valido") ||
                text.includes("accesso negato") ||
                text.includes(" errore") ||
                text.includes("rate limit") ||
                text.includes("inaccessibile")
            );

            if (isSocial && [400, 401, 403, 404].includes(statusCode)) {
                dotColor = 's-yellow';
            } else if (statusCode >= 300 && statusCode < 400) {
                dotColor = 's-yellow';
            } else if (statusCode >= 500 || statusCode === 408) {
                dotColor = 's-red';
            } else if (statusCode === 206) {
                dotColor = 's-yellow';
            } else if (statusCode === 200) {
                if (isSocial && !isFoundFlag && !hasStrongSignal) {
                    dotColor = 's-yellow';
                } else {
                    dotColor = 's-green';
                }
                if (isNegative(statusText) || statusText.includes("partial") || statusText.includes("muro anti-bot") || statusText.includes("richiede login")) {
                    dotColor = 's-yellow';
                }
            } else {
                dotColor = 's-red';
            }

            if ((isFoundFlag || hasStrongSignal) && dotColor !== 's-red') {
                highlightClass = 'highlight';
            } else if (!d.main_img || String(d.main_img).startsWith("data:")) {
                dotColor = 's-yellow';
            }

            if (isSocial && !isFoundFlag && dotColor === 's-red' && statusCode !== 500) {
                dotColor = 's-yellow';
            }

            if (d.main_img && socialIcons[d.type] && d.main_img !== socialIcons[d.type].icon && !String(d.main_img).includes('flaticon.com') && statusCode >= 500) {
                dotColor = 's-yellow';
            }
            
            const inactiveClass = dotColor === 's-red' ? 'inactive' : '';
            const div = document.createElement('div'); div.className = `card ${inactiveClass} ${highlightClass}`;
            
            let rows = ''; for(let k in d.info) { if(!k.startsWith('__')) rows += `<div class="data-row"><label>${k}</label><span>${d.info[k]}</span></div>`; }
            
            let extra = '';
            if (d.graph_data && d.graph_data.length > 0) extra += `<canvas id="${uniqueId}"></canvas>`;
            
            let displayTitle = d.username;
            if (cryptoIconsMap[d.type] || d.type === 'Bitcoin' || d.type === 'Ethereum' || d.type === 'Binance SC' || d.type === 'Polygon' || d.type === 'Avalanche' || d.type === 'Litecoin' || d.type === 'Dogecoin' || d.type === 'Dash' || d.type === 'Tron' || d.type === 'Solana' || d.type === 'Ripple') {
                extra += `<button class="btn-link" onclick="openGraph('${d.username}')" style="background:var(--secondary); color:white;">ANALISI NETWORK </button>`;
                if (displayTitle.length > 15) {
                    displayTitle = displayTitle.substring(0, 6) + "..." + displayTitle.substring(displayTitle.length - 4);
                }
            } else {
                displayTitle = displayTitle.substring(0,25);
            }
            
            if (d.type === 'Telegram' && d.info.Tipologia === 'Canale/Gruppo') {
                extra += `<button class="btn-link" onclick="downloadCSV('${d.info['ID Numerico']}')" style="background:var(--accent); color:#000;"> SCARICA PARTECIPANTI (CSV)</button>`;
            } else if (d.type === 'Telegram' && d.info['ID Numerico']) {
                const tgUid = String(d.info['ID Numerico']).replace(/'/g, "\\'");
                const tgName = String(d.info[' Nome'] || d.username).replace(/'/g, "\\'");
                const tgPfp = d.main_img;
                extra += `
                <div style="margin-top:10px; background: rgba(0, 229, 255, 0.1); padding: 8px; border-radius: 6px;">
                    <select id="tg-duration-${tgUid}" style="width:100%; padding:5px; background:var(--panel); color:white; border:1px solid var(--accent); border-radius:4px; margin-bottom:5px;">
                        <option value="1 Ora">1 Ora</option>
                        <option value="6 Ore">6 Ore</option>
                        <option value="1 Giorno">1 Giorno</option>
                        <option value="3 Giorni">3 Giorni</option>
                        <option value="1 Settimana">1 Settimana</option>
                    </select>
                    <button class="btn-link" onclick="startTgMonitor('${tgUid}', '${tgName}', '${tgPfp}', document.getElementById('tg-duration-${tgUid}').value)" style="background:#0088cc; color:white; margin-top:0;"> AVVIA MONITORAGGIO TG</button>
                </div>`;
            }

            if (d.type === 'Instagram' || d.type === 'Telegram' || d.type === 'TikTok') {
                const uniqueScrapeId = 'scrape_' + Math.random().toString(36).substr(2, 9);
                window.cardDataMap = window.cardDataMap || {};
                window.cardDataMap[uniqueScrapeId] = d;
                extra += `<button class="btn-link" onclick="openScrapePrompt('${uniqueScrapeId}')" style="background:var(--danger); color:white; border: 1px solid #f43f5e;"> SCARICA CONTENUTI</button>`;
            }
            if (d.type === 'Messaging') {
                const tgLink = (d.info && d.info.__tg_link) ? d.info.__tg_link : '';
                const waLink = (d.info && d.info.__wa_link) ? d.info.__wa_link : '';
                if (tgLink) {
                    extra += `<a href="${tgLink}" target="_blank" class="btn-link" style="background:#0088cc; color:white;">APRI TELEGRAM</a>`;
                }
                if (waLink) {
                    extra += `<a href="${waLink}" target="_blank" class="btn-link" style="background:#25d366; color:#04150f;">APRI WHATSAPP</a>`;
                }
            }
            if (d.ip_graph_target) extra += `<button class="btn-link" onclick="openIpGraph('${d.ip_graph_target}')" style="background:var(--secondary); color:white;"> IP NETWORK</button>`;
            if (d.url) extra += `<a href="${d.url}" target="_blank" class="btn-link">APRI LINK</a>`;
            extra += `<button type="button" class="btn-add-report">AGGIUNGI AL REPORT</button>`;

            // HOVER ZOOM: Aggiunto onmouseenter e onmouseleave all'immagine
            div.innerHTML = `
                <div class="status-dot ${dotColor}"></div>
                <div class="card-header" onclick="this.parentElement.classList.toggle('open')">
                    <img src="${d.main_img}" class="pfp" onmouseenter="document.getElementById('hover-zoom-img').src=this.src; document.getElementById('hover-zoom-img').style.display='block';" onmouseleave="document.getElementById('hover-zoom-img').style.display='none';">
                    <div><h4 style="margin:0; color:white;">${displayTitle}</h4><small>${d.type}</small></div>
                </div>
                <div class="card-body">${rows}${extra}</div>`;
            document.getElementById(containerId).appendChild(div);
            const addRep = div.querySelector('.btn-add-report');
            if (addRep) addRep.addEventListener('click', function() { addToHistory(d); });

            if (d.graph_data && d.graph_data.length > 0) {
                new Chart(document.getElementById(uniqueId).getContext('2d'), {
                    type: 'line', data: { labels: d.graph_data.map(p => p.t), datasets: [{ label: 'Balance', data: d.graph_data.map(p => p.y), borderColor: '#00e5ff', backgroundColor: 'rgba(0, 229, 255, 0.1)', fill: true }] },
                    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { grid: { color: '#1e293b' } } } }
                });
            }
            
            // Ho rimosso l'apertura automatica. Ora dovrai sempre cliccare per espandere le card!
        }

        async function openGraph(address) {
            document.getElementById('graph-overlay').style.display = 'flex';
            document.getElementById('node-info-panel').style.display = 'none';
            
            currentJumps = 0;
            document.getElementById('graph-address-path').innerHTML = `Target Iniziale: <span style="color:var(--accent)">${address}</span>`;
            
            const r = await fetch('/api/crypto_graph', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({address:address})});
            const data = await r.json();
            
            graphNodes = new vis.DataSet(data.nodes);
            graphEdges = new vis.DataSet(data.edges);
            const container = document.getElementById('graph-container');
            const options = {
                nodes: { shape: 'circularImage', borderWidth: 2, color: { border: '#00e5ff', background: '#0b0f19' }, size: 25, font: { color: '#ffffff', size: 10, vadjust: 30 } },
                edges: { color: '#3b82f6', arrows: 'to' },
                physics: { stabilization: false, barnesHut: { gravitationalConstant: -8000 } }
            };
            network = new vis.Network(container, {nodes: graphNodes, edges: graphEdges}, options);
            network.on("click", (p) => { if(p.nodes.length > 0) showNodeDetails(p.nodes[0]); });
        }

        let ipNetwork = null;
        let ipGraphNodes = null;
        let ipGraphEdges = null;

        function closeIpGraph() {
            document.getElementById('ip-graph-overlay').style.display = 'none';
            document.getElementById('ip-node-info-panel').style.display = 'none';
            ipNetwork = null; ipGraphNodes = null; ipGraphEdges = null;
        }

        async function openIpGraph(domain) {
            document.getElementById('ip-graph-overlay').style.display = 'flex';
            document.getElementById('ip-node-info-panel').style.display = 'none';
            document.getElementById('ip-graph-domain').innerHTML = `Target: <span style="color:var(--accent)">${domain}</span>`;

            const r = await fetch('/api/ip_graph', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain})});
            const data = await r.json();

            ipGraphNodes = new vis.DataSet(data.nodes || []);
            ipGraphEdges = new vis.DataSet(data.edges || []);

            const container = document.getElementById('ip-graph-container');
            const options = {
                nodes: { borderWidth: 2, font: { color: '#ffffff', size: 12 }, shadow: false },
                edges: { color: '#3b82f6', arrows: 'to', smooth: { type: 'dynamic' } },
                physics: { stabilization: false, barnesHut: { gravitationalConstant: -9000 } }
            };

            ipNetwork = new vis.Network(container, {nodes: ipGraphNodes, edges: ipGraphEdges}, options);
            ipNetwork.on("click", (p) => { if(p.nodes.length > 0) showIpNodeDetails(p.nodes[0]); });
        }

        async function showIpNodeDetails(nodeId) {
            const panel = document.getElementById('ip-node-info-panel');
            const content = document.getElementById('ip-node-details-content');
            panel.style.display = 'flex';

            if (!nodeId.startsWith('ip:')) {
                content.innerHTML = `<div style="padding:10px; background:var(--bg); border-radius:8px; border:1px solid #1e293b; color:#94a3b8; font-family:monospace;">Nodo: ${nodeId}</div>`;
                return;
            }

            const ip = nodeId.substring(3);
            content.innerHTML = `<p style="color:var(--accent)">Analisi IP in corso...</p>`;

            const r = await fetch('/api/ip_whois', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ip})});
            const data = await r.json();

            let html = `<div style="margin-bottom:15px; padding:10px; background:var(--bg); border-radius:8px; border:1px dashed var(--accent); text-align:center;">
                            <strong style="color:white; font-size:14px; font-family:monospace;">${ip}</strong>
                            <br><button class="tx-btn copy" style="margin-top:8px; width:100%; padding:8px;" onclick="copyText('${ip}')"> COPIA IP</button>
                        </div>`;

            if (data && data.rdap) {
                for (let k in data.rdap) {
                    html += `<div class="node-info-row"><label>${k}</label><span>${data.rdap[k]}</span></div>`;
                }
            }

            if (data && data.reverse_dns && data.reverse_dns.length > 0) {
                html += `<div class="node-info-row"><label>Reverse DNS</label><span>${data.reverse_dns.join(', ')}</span></div>`;
            }

            if (data && data.services && data.services.length > 0) {
                html += `<div class="tx-list"><h4 style="color:var(--success);"> SERVIZI (porte comuni)</h4>`;
                data.services.forEach(s => {
                    html += `<div class="tx-item"><span>${s.service} : ${s.port}</span><div class="tx-item-actions"><button class="tx-btn copy" onclick="copyText('${ip}:${s.port}')">COPIA</button></div></div>`;
                });
                html += `</div>`;
            } else {
                html += `<div class="node-info-row"><label>Servizi</label><span>Nessun servizio comune aperto</span></div>`;
            }

            content.innerHTML = html;
        }

        async function expandGraph(peerAddress) {
            if (currentJumps >= MAX_JUMPS) {
                alert("Limite massimo raggiunto: puoi effettuare al massimo 3 salti dal wallet iniziale per evitare sovraccarichi.");
                return;
            }
            
            currentJumps++;
            document.getElementById('graph-address-path').innerHTML += `<br>Salto ${currentJumps}: <span style="color:var(--success)">${peerAddress}</span>`;
            document.getElementById('node-details-content').innerHTML = '<p style="color:var(--accent)">Espansione della rete in corso...</p>';
            
            const r = await fetch('/api/crypto_graph', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({address:peerAddress})});
            const data = await r.json();
            
            data.nodes.forEach(n => {
                if (!graphNodes.get(n.id)) graphNodes.add(n);
            });
            
            data.edges.forEach(e => {
                let exist = graphEdges.get({ filter: function (item) { return item.from === e.from && item.to === e.to; } });
                if (exist.length === 0) graphEdges.add(e);
            });
            
            showNodeDetails(peerAddress);
        }

        async function showNodeDetails(address) {
            const panel = document.getElementById('node-info-panel');
            const content = document.getElementById('node-details-content');
            panel.style.display = 'flex';
            content.innerHTML = '<p style="color:var(--accent)">Analisi on-chain in corso...</p>';

            const rInfo = await fetch('/api/search', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({target:address, platform:'finance'})});
            const dataInfo = await rInfo.json();
            const d = Array.isArray(dataInfo) ? dataInfo[0] : dataInfo;
            
            const rGraph = await fetch('/api/crypto_graph', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({address:address})});
            const graphData = await rGraph.json();

            if(d && d.info) {
                const shortAddr = address.length > 10 ? address.substring(0,6) + '...' + address.substring(address.length-4) : address;
                let html = `<div style="margin-bottom:15px; padding:10px; background:var(--bg); border-radius:8px; border:1px dashed var(--accent); text-align:center;">
                                <strong style="color:white; font-size:14px; font-family:monospace;">${shortAddr}</strong>
                                <br><button class="tx-btn copy" style="margin-top:8px; width:100%; padding:8px;" onclick="copyText('${address}')"> COPIA INDIRIZZO INTERO</button>
                            </div>`;
                            
                for(let k in d.info) { if(!k.startsWith('__')) html += `<div class="node-info-row"><label>${k}</label><span>${d.info[k]}</span></div>`; }

                if(graphData.in_nodes && graphData.in_nodes.length > 0) {
                    html += `<div class="tx-list"><h4 style="color:var(--success);">TRANSAZIONI IN INGRESSO</h4>`;
                    graphData.in_nodes.forEach(peer => {
                        const shortPeer = peer.length > 10 ? peer.substring(0,6) + '...' + peer.substring(peer.length-4) : peer;
                        html += `<div class="tx-item">
                                    <span>${shortPeer}</span>
                                    <div class="tx-item-actions">
                                        <button class="tx-btn copy" onclick="copyText('${peer}')">COPIA</button>
                                        <button class="tx-btn analyze" onclick="expandGraph('${peer}')">ANALIZZA</button>
                                    </div>
                                 </div>`;
                    });
                    html += `</div>`;
                }

                if(graphData.out_nodes && graphData.out_nodes.length > 0) {
                    html += `<div class="tx-list"><h4 style="color:var(--danger);">TRANSAZIONI IN USCITA</h4>`;
                    graphData.out_nodes.forEach(peer => {
                        const shortPeer = peer.length > 10 ? peer.substring(0,6) + '...' + peer.substring(peer.length-4) : peer;
                        html += `<div class="tx-item">
                                    <span>${shortPeer}</span>
                                    <div class="tx-item-actions">
                                        <button class="tx-btn copy" onclick="copyText('${peer}')">COPIA</button>
                                        <button class="tx-btn analyze" onclick="expandGraph('${peer}')">ANALIZZA</button>
                                    </div>
                                 </div>`;
                    });
                    html += `</div>`;
                }

                content.innerHTML = html;

                if(sideChart) sideChart.destroy();
                if(d.graph_data && d.graph_data.length > 0) {
                    sideChart = new Chart(document.getElementById('node-balance-chart').getContext('2d'), {
                        type: 'line', data: { labels: d.graph_data.map(p => p.t), datasets: [{ label: 'Balance', data: d.graph_data.map(p => p.y), borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3 }] },
                        options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { grid: { color: '#1e293b' } } } }
                    });
                }
            }
        }

        function closeGraph() { 
            document.getElementById('graph-overlay').style.display = 'none'; 
            document.getElementById('graph-address-path').innerHTML = ''; // Resetta lo storico visivo
            currentJumps = 0; // Resetta il contatore dei salti
            if(network) network.destroy(); 
        }

        function escapeHtml(s) {
            if (s === null || s === undefined) return '';
            return String(s)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        let tgMonitorInterval = null;
        let currentTgTarget = null;

        function checkAndAddToHistoryTg(entityId, name, pfp) {
            let exists = historyDB.find(h => h.info && h.info['ID Numerico'] === entityId);
            if (!exists) {
                const newData = {
                    username: name,
                    type: 'Telegram',
                    info: { 'ID Numerico': entityId, ' Nome': name },
                    main_img: pfp,
                    status_code: 200
                };
                addToHistory(newData);
            }
        }

        function startTgMonitor(entityId, name, pfp, duration) {
            checkAndAddToHistoryTg(entityId, name, pfp);
            openTgModal(entityId, name, pfp, "Durata: " + duration);
            
            document.getElementById('tg-status-indicator').className = 'tg-standby';
            document.getElementById('tg-status-indicator').textContent = 'Inizializzazione...';
            document.getElementById('tg-btn-stop').style.display = 'block';

            fetch('/api/tg/start_monitoring', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: entityId, duration: duration })
            }).then(r => r.json()).then(res => {
                if (res.status === 'ok') {
                    pollTgMonitor(entityId);
                    tgMonitorInterval = setInterval(() => pollTgMonitor(entityId), 5000);
                } else {
                    alert("Errore avvio monitoraggio: " + res.error);
                    closeTgMonitor();
                }
            });
        }

        function openTgModal(entityId, name, pfp, desc) {
            currentTgTarget = entityId;
            document.getElementById('overlay').style.display = 'block';
            document.getElementById('tg-monitor-modal').style.display = 'flex';
            document.getElementById('tg-monitor-pfp').src = pfp;
            document.getElementById('tg-monitor-name').textContent = name;
            document.getElementById('tg-monitor-desc').textContent = "ID: " + entityId + " | " + desc;
            document.getElementById('tg-log-container').innerHTML = '';
        }

        function openTgMonitorHistory(entityId, name, pfp) {
            openTgModal(entityId, name, pfp, "StandBy History");
            document.getElementById('tg-status-indicator').className = 'tg-standby';
            document.getElementById('tg-status-indicator').textContent = 'Verifica stato...';
            document.getElementById('tg-btn-stop').style.display = 'none';
            pollTgMonitor(entityId);
            tgMonitorInterval = setInterval(() => pollTgMonitor(entityId), 5000);
        }

        function updateTgLogs(entityId) {
            fetch('/api/tg/get_intelligence_logs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: entityId })
            }).then(r => r.json()).then(res => {
                if (res.status === 'ok') {
                    const logContainer = document.getElementById('tg-log-container');
                    let html = '';
                    res.logs.forEach(line => {
                        let cssClass = '';
                        if (line.includes('ONLINE')) cssClass = 'log-online';
                        else if (line.includes('OFFLINE')) cssClass = 'log-offline';
                        else if (line.includes('[ALERT]')) cssClass = 'log-alert';
                        html += `<div class="${cssClass}">${escapeHtml(line)}</div>`;
                    });
                    logContainer.innerHTML = html;
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            });
        }

        function pollTgMonitor(entityId) {
            updateTgLogs(entityId);
            fetch('/api/tg/check_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: entityId })
            }).then(r => r.json()).then(res => {
                const ind = document.getElementById('tg-status-indicator');
                if (res.status === 'ok') {
                    const isOnline = res.data.online;
                    ind.className = isOnline ? 'tg-online' : 'tg-offline';
                    ind.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
                    document.getElementById('tg-last-seen').textContent = "Ultimo accesso: " + res.data.last_seen;
                    document.getElementById('tg-btn-stop').style.display = 'block';
                    updateHistoryTgStatus(entityId, true);
                } else if (res.status === 'stopped') {
                    ind.className = 'tg-standby';
                    ind.textContent = 'Monitoraggio Terminato / StandBy';
                    document.getElementById('tg-btn-stop').style.display = 'none';
                    if (tgMonitorInterval) {
                        clearInterval(tgMonitorInterval);
                        tgMonitorInterval = null;
                        // One last log update
                        updateTgLogs(entityId);
                    }
                    updateHistoryTgStatus(entityId, false);
                }
            }).catch(e => console.error(e));
        }

        function stopTgMonitor() {
            if (!currentTgTarget) return;
            fetch('/api/tg/stop_monitoring', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: currentTgTarget })
            }).then(r => r.json()).then(res => {
                if (res.status === 'ok') {
                    pollTgMonitor(currentTgTarget); // Force update to stopped state
                }
            });
        }

        function downloadTgReport() {
            if (!currentTgTarget) return;
            window.location.href = `/api/tg/export_report?target=${currentTgTarget}`;
        }

        function closeTgMonitor() {
            document.getElementById('overlay').style.display = 'none';
            document.getElementById('tg-monitor-modal').style.display = 'none';
            if (tgMonitorInterval) {
                clearInterval(tgMonitorInterval);
                tgMonitorInterval = null;
            }
            currentTgTarget = null;
        }

function escapeAttr(s) {
            return escapeHtml(s).replace(/'/g, '&#39;');
        }

        let activeScrapeTarget = null;
        let activeScrapePlatform = null;
        let activeScrapeData = null;

        function openScrapePrompt(scrapeId) {
            if(scrapeId && window.cardDataMap && window.cardDataMap[scrapeId]) {
                activeScrapeData = window.cardDataMap[scrapeId];
                activeScrapeTarget = activeScrapeData.username;
                activeScrapePlatform = activeScrapeData.type;
            } else {
                activeScrapeData = null;
                activeScrapeTarget = null;
                activeScrapePlatform = null;
                return;
            }
            document.getElementById('scrape-target-info').innerText = activeScrapePlatform + ': ' + activeScrapeTarget;
            document.getElementById('scrape-modal').style.display = 'flex';
        }

        function closeScrapePrompt() {
            document.getElementById('scrape-modal').style.display = 'none';
        }

        async function startScraping() {
            if(!activeScrapeTarget) return;
            const options = {
                dati: document.getElementById('scrape-opt-dati').checked,
                media: document.getElementById('scrape-opt-media').checked,
                link: document.getElementById('scrape-opt-link').checked,
                follower: document.getElementById('scrape-opt-follower').checked,
                following: document.getElementById('scrape-opt-following').checked,
                tutto: document.getElementById('scrape-opt-tutto').checked
            };
            const btn = document.querySelector('#scrape-modal button');
            const oldText = btn.innerText;
            btn.innerText = "AVVIO IN CORSO...";
            try {
                const res = await fetch('/api/scrape/start', {
                    method: 'POST',
                    headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({target: activeScrapeTarget, platform: activeScrapePlatform, options: options})
                });
                const data = await res.json();
                if(data.status === 'ok') {
                    let histItem = historyDB.find(h => h.username === activeScrapeTarget && h.type === activeScrapePlatform);
                    if(!histItem && activeScrapeData) {
                        console.log("Aggiunta automatica al report:", activeScrapeData);
                        addToHistory(activeScrapeData);
                        histItem = historyDB.find(h => h.username === activeScrapeTarget && h.type === activeScrapePlatform);
                    }
                    if(histItem) {
                        histItem.scrapeTaskId = data.taskId;
                        histItem.scrapeStatus = 'running';
                        histItem.scrapeProgress = 0;
                        saveHistoryToStorage();
                        renderHistoryList();
                    } else {
                        alert("Non è stato possibile aggiungere il target al report. activeScrapeData era: " + (activeScrapeData ? "presente" : "assente"));
                    }
                    closeScrapePrompt();
                } else {
                    alert("Errore avvio scrape: " + data.message);
                }
            } catch(e) {
                alert("Errore di rete");
            }
            btn.innerText = oldText;
        }

        setInterval(async () => {
            const activeTasks = historyDB.filter(h => h.scrapeTaskId && h.scrapeStatus === 'running').map(h => h.scrapeTaskId);
            if(activeTasks.length > 0) {
                try {
                    const res = await fetch('/api/scrape/status', {
                        method: 'POST',
                        headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({taskIds: activeTasks})
                    });
                    const data = await res.json();
                    if(data.status === 'ok' && data.tasks) {
                        let updated = false;
                        for(let t of historyDB) {
                            if(t.scrapeTaskId && data.tasks[t.scrapeTaskId]) {
                                const tinfo = data.tasks[t.scrapeTaskId];
                                if(t.scrapeProgress !== tinfo.progress || t.scrapeStatus !== tinfo.status) {
                                    t.scrapeProgress = tinfo.progress;
                                    t.scrapeStatus = tinfo.status;
                                    updated = true;
                                }
                            }
                        }
                        if(updated) {
                            saveHistoryToStorage();
                            renderHistoryList();
                        }
                    }
                } catch(e){}
            }
        }, 3000);

        function saveHistoryToStorage() {
            try {
                localStorage.setItem('cscorza_target_history', JSON.stringify(historyDB));
            } catch (e) {}
        }

        function renderHistoryList() {
            const list = document.getElementById('history-list');
            if (!list) return;
            const cb = document.getElementById('hist-show-icons');
            const showIcons = cb ? cb.checked : true;
            list.innerHTML = '';
            if (!historyDB.length) {
                list.innerHTML = '<div class="hist-empty">Nessun target nel report.<br>Usa <strong>AGGIUNGI AL REPORT</strong> sulle card.</div>';
                return;
            }
            for (let i = historyDB.length - 1; i >= 0; i--) {
                const entry = historyDB[i];
                if (!entry.histId) {
                    entry.histId = 'mig-' + i + '-' + Date.now();
                    saveHistoryToStorage();
                }
                const histId = entry.histId;
                const fb = socialIcons[entry.type] ? socialIcons[entry.type].icon : '';
                const iconUrl = (entry.main_img && String(entry.main_img).trim()) ? entry.main_img : fb;
                const typeName = escapeHtml(String(entry.type || 'Unknown'));
                const userRaw = escapeHtml(String(entry.username != null ? entry.username : ''));
                const row = document.createElement('div');
                row.className = 'hist-item';
                let thumbBlock;
                if (showIcons && iconUrl) {
                    thumbBlock = '<img class="hist-thumb" src="' + escapeAttr(iconUrl) + '" alt="" loading="lazy" referrerpolicy="no-referrer">';
                } else {
                    const ch = (entry.type || '?').toString().charAt(0).toUpperCase();
                    thumbBlock = '<div class="hist-thumb-placeholder">' + escapeHtml(ch) + '</div>';
                }
                row.innerHTML = '<div class="hist-item-main">' + thumbBlock +
                    '<div class="hist-text"><div class="hist-service">' + typeName + '</div>' +
                    '<div class="hist-username" title="' + userRaw + '">' + userRaw + '</div></div>' +
                    '<button type="button" class="hist-remove" title="Rimuovi" aria-label="Rimuovi">X</button></div>';
                    
                if (entry.scrapeTaskId) {
                    const s = entry.scrapeStatus || 'pending';
                    const p = entry.scrapeProgress || 0;
                    let dotColor = s === 'completed' ? 'var(--success)' : (s === 'failed' ? 'var(--danger)' : 'var(--danger)');
                    if(s === 'running') dotColor = 'var(--danger)'; // Red dot when downloading
                    
                    let extraUI = `<div style="margin-top: 8px; font-size: 10px; display: flex; align-items: center; gap: 5px;">
                        <div style="width:8px; height:8px; border-radius:50%; background:${dotColor}; box-shadow: 0 0 5px ${dotColor};"></div>
                        <div style="color:var(--accent); flex:1;">Scrape: ${p}%</div>
                    </div>`;
                    
                    if (s === 'running') {
                        extraUI += `<div style="height:4px; background:#1e293b; border-radius:2px; margin-top:4px; overflow:hidden;">
                                        <div style="height:100%; width:${p}%; background:var(--danger); transition:0.3s;"></div>
                                    </div>`;
                    } else if (s === 'completed') {
                        extraUI += `<a href="/api/scrape/download/${entry.scrapeTaskId}" target="_blank" style="display:block; margin-top:5px; text-align:center; background:var(--success); color:#000; text-decoration:none; padding:4px; border-radius:4px; font-weight:bold; font-size:10px;"> SALVA ZIP</a>`;
                    } else if (s === 'failed') {
                        extraUI += `<div style="color:var(--danger); margin-top:4px;">Errore nello scaricamento</div>`;
                    }
                    row.innerHTML += extraUI;
                }
                
                row.querySelector('.hist-remove').addEventListener('click', function(ev) {
                    ev.stopPropagation();
                    removeFromHistory(histId);
                });
                list.appendChild(row);
            }
        }

        function removeFromHistory(histId) {
            historyDB = historyDB.filter(function(e) { return e.histId !== histId; });
            saveHistoryToStorage();
            renderHistoryList();
        }

        function addToHistory(data) {
            let copy;
            try {
                copy = JSON.parse(JSON.stringify(data));
            } catch (e) {
                copy = Object.assign({}, data);
            }
            copy.histId = (typeof crypto !== 'undefined' && crypto.randomUUID)
                ? crypto.randomUUID()
                : ('h' + Date.now() + '-' + Math.random().toString(36).slice(2));
            historyDB.push(copy);
            saveHistoryToStorage();
            renderHistoryList();
        }

        async function exportReport() { const r = await fetch('/api/export', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({data:historyDB})}); const b = await r.blob(); const u = window.URL.createObjectURL(b); const a = document.createElement('a'); a.href=u; a.download='Report_CSCORZA.pdf'; a.click(); }

        (function initTargetHistory() {
            try {
                const raw = localStorage.getItem('cscorza_target_history');
                if (raw) {
                    historyDB = JSON.parse(raw);
                    historyDB.forEach(function(e, i) {
                        if (!e.histId) e.histId = 'legacy-' + i + '-' + Date.now();
                    });
                    saveHistoryToStorage();
                }
            } catch (e) {}
            const cb = document.getElementById('hist-show-icons');
            const savedShow = localStorage.getItem('cscorza_hist_show_icons');
            if (cb && savedShow !== null) cb.checked = savedShow === '1';
            if (cb) {
                cb.addEventListener('change', function() {
                    localStorage.setItem('cscorza_hist_show_icons', cb.checked ? '1' : '0');
                    renderHistoryList();
                });
            }
            renderHistoryList();
        })();
        
        async function sendTgCode() { const r = await fetch('/api/tg/send_code', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({tg_id:document.getElementById('tg_id').value, tg_hash:document.getElementById('tg_hash').value, phone:document.getElementById('phone').value})}); if((await r.json()).status === 'ok') { document.getElementById('btn-send-code').style.display='none'; document.getElementById('otp-area').style.display='block'; } }
        async function verifyTgCode() { const r = await fetch('/api/tg/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code:document.getElementById('otp_code').value})}); if((await r.json()).status === 'ok') alert("Successo!"); }
        
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---
class OSINTCore:
    def __init__(self):
        self.creds = DEFAULT_CREDS.copy()
        if os.path.exists(CREDS_FILE):
            try:
                with open(CREDS_FILE, "r") as f: self.creds.update(json.load(f))
            except: pass
    
    def save_creds(self, d):
        self.creds.update(d)
        Path(CREDS_FILE).write_text(json.dumps(self.creds, indent=4))

    def _human_bytes(self, size_bytes):
        try:
            size = int(size_bytes)
        except (TypeError, ValueError):
            return str(size_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.2f} {unit}"
            value /= 1024

    def _drive_resource_type(self, mime_type, title):
        if not mime_type:
            return "Risorsa"
        mt = mime_type.lower()
        if "vnd.google-apps.folder" in mt:
            return "Cartella"
        mapping = {
            "vnd.google-apps.document": "Documento Google",
            "vnd.google-apps.spreadsheet": "Foglio Google",
            "vnd.google-apps.presentation": "Presentazione Google",
            "vnd.google-apps.form": "Modulo Google",
            "vnd.google-apps.drawing": "Disegno Google",
            "vnd.google-apps.script": "Script Google",
            "vnd.google-apps.site": "Sito Google",
        }
        for key, val in mapping.items():
            if key in mt:
                return val
        if mt.startswith("application/vnd.google-apps"):
            return "Google Workspace"
        if title and "." in title:
            ext = os.path.splitext(title)[1].upper().replace(".", "")
            return f"File {ext}"
        return "File"

    def _drive_public_permissions(self, permissions):
        if not permissions:
            return []
        return [
            f"{p.get('id')}:{p.get('role')}"
            for p in permissions
            if p.get("id") in ("anyone", "anyoneWithLink", "domain")
        ]

    def _collect_drive_id_candidates(self, target):
        target = (target or "").strip()
        if not target:
            return []

        parsed = urllib.parse.urlparse(target)
        parsed_path = (parsed.path or "").strip("/")
        path_parts = [p for p in parsed_path.split("/") if p]

        def _clean_id(raw):
            if not raw:
                return ""
            raw = (raw or "").strip().strip(" <>\"'")
            if re.fullmatch(r"[A-Za-z0-9_-]{10,}", raw):
                return raw
            return ""

        candidates = []
        qs = urllib.parse.parse_qs((parsed.query or ""), keep_blank_values=False)
        for k in ("id", "fileId", "docid", "file_id"):
            for v in qs.get(k, []):
                cid = _clean_id(v)
                if cid:
                    candidates.append(cid)

        patterns = [
            r"/d/([A-Za-z0-9_-]{10,})",
            r"/folders/([A-Za-z0-9_-]{10,})",
            r"/file/d/([A-Za-z0-9_-]{10,})",
            r"/drive/folders/([A-Za-z0-9_-]{10,})",
            r"/drive/u/\\d+/folders/([A-Za-z0-9_-]{10,})",
            r"/document/d/([A-Za-z0-9_-]{10,})",
            r"/spreadsheets/d/([A-Za-z0-9_-]{10,})",
            r"/presentation/d/([A-Za-z0-9_-]{10,})",
            r"/forms/d/([A-Za-z0-9_-]{10,})",
            r"/drawings/d/([A-Za-z0-9_-]{10,})",
            r"/document/u/\\d+/d/([A-Za-z0-9_-]{10,})",
            r"/open\\?[^#]*id=([A-Za-z0-9_-]{10,})",
            r"/uc\\?[^#]*id=([A-Za-z0-9_-]{10,})",
            r"/docs.google.com/[a-zA-Z0-9_-]+/d/e/([A-Za-z0-9_-]{10,})",
            r"/docs.google.com/spreadsheets/d/e/([A-Za-z0-9_-]{10,})"
        ]
        for pat in patterns:
            m = re.search(pat, target, flags=re.IGNORECASE)
            if m:
                cid = _clean_id(m.group(1))
                if not cid and len(m.groups()) > 1:
                    cid = _clean_id(m.group(2))
                if cid:
                    candidates.append(cid)

        for p in path_parts:
            cid = _clean_id(p)
            if cid:
                candidates.append(cid)

        if not candidates:
            for p in target.split("?")[0].split("/"):
                cid = _clean_id(p)
                if cid:
                    candidates.append(cid)
        return candidates

    def _drive_variant_urls(self, doc_id):
        return {
            "Viewer": f"https://drive.google.com/file/d/{doc_id}/view",
            "Viewer Alt": f"https://drive.google.com/file/d/{doc_id}/view?usp=sharing",
            "Viewer Docs": f"https://docs.google.com/document/d/{doc_id}/edit",
            "Viewer Sheet": f"https://docs.google.com/spreadsheets/d/{doc_id}/edit",
            "Folder View": f"https://drive.google.com/drive/folders/{doc_id}",
            "Open": f"https://drive.google.com/open?id={doc_id}",
            "Raw/Download": f"https://drive.google.com/uc?export=download&id={doc_id}"
        }

    def _drive_probe_variant(self, doc_id):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }
        for label, v_url in self._drive_variant_urls(doc_id).items():
            try:
                r = requests.get(v_url, headers=headers, timeout=10, allow_redirects=True)
                if r.status_code not in (200, 301, 302, 307, 308):
                    continue
                text = (r.text or "").strip()
                if not text or "404" in text[:220].upper():
                    continue
                soup = BeautifulSoup(text, "html.parser")
                title = ""
                og_title = soup.find("meta", attrs={"property": "og:title"})
                if og_title and og_title.get("content"):
                    title = og_title.get("content").strip()
                if not title and soup.title and soup.title.text:
                    title = soup.title.text.strip()
                if title:
                    return {
                        "status": r.status_code,
                        "title": title,
                        "url": r.url or v_url,
                        "source": label,
                    }
            except Exception:
                continue
        return {}

    def analyze_gdrive_doc(self, doc_link):
        target = (doc_link or "").strip()
        target_norm = target.lower()
        candidates = self._collect_drive_id_candidates(target)

        doc_id = candidates[0] if candidates else ""
        if not doc_id:
            return {
                "username": target or "Google Doc",
                "type": "Doc GDrive",
                "info": {
                    "Status": "Document ID non trovato",
                    "Suggerimento": "Inserisci un link Google Docs/Sheets/Drive pubblico contenente un ID valido."
                },
                "main_img": "https://ssl.gstatic.com/docs/doclist/images/drive_2022q3_32dp.png",
                "status_code": 404,
                "url": target
            }

        url = (
            f"https://clients6.google.com/drive/v2beta/files/{doc_id}"
            "?fields=alternateLink%2CcopyRequiresWriterPermission%2CcreatedDate%2Cdescription%2CdriveId%2CfileSize%2CiconLink%2Cid"
            "%2Clabels(starred%2Ctrashed)%2ClastViewedByMeDate%2CmodifiedDate%2Cshared%2CteamDriveId"
            "%2CuserPermission(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)"
            "%2Cpermissions(id%2Cname%2CemailAddress%2Cdomain%2Crole%2CadditionalRoles%2CphotoLink%2Ctype%2CwithLink)"
            "%2Cparents(id)%2Ccapabilities(canMoveItemWithinDrive%2CcanMoveItemOutOfDrive%2CcanMoveItemOutOfTeamDrive"
            "%2CcanAddChildren%2CcanEdit%2CcanDownload%2CcanComment%2CcanMoveChildrenWithinDrive%2CcanRename%2CcanRemoveChildren"
            "%2CcanMoveItemIntoTeamDrive)%2Ckind&supportsTeamDrives=true&enforceSingleParent=true"
            "&key=AIzaSyC1eQ1xj69IdTMeii5r7brs3R90eck-m7k"
        )
        headers = {"X-Origin": "https://drive.google.com"}
        drive_icon = "https://ssl.gstatic.com/docs/doclist/images/drive_2022q3_32dp.png"

        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200 or "File not found" in r.text:
                probe = self._drive_probe_variant(doc_id)
                if probe.get("title"):
                    return {
                        "username": doc_id,
                        "type": "Doc GDrive",
                        "info": {
                            "Status": "Risorsa pubblica rilevata da pagina Google Drive",
                            "Nome file": probe.get("title", "N/D"),
                            "Fonte variante": probe.get("source", "N/D"),
                            "Metodo": "viewer fallback",
                            "URL rilevato": probe.get("url", target),
                            "HTTP Status": str(probe.get("status", r.status_code))
                        },
                        "main_img": drive_icon,
                        "status_code": 206,
                        "url": probe.get("url", target)
                    }
                return {
                    "username": doc_id,
                    "type": "Doc GDrive",
                    "info": {
                        "Status": "File non trovato, non pubblico o ID non valido",
                        "Document ID": doc_id
                    },
                    "main_img": drive_icon,
                    "status_code": 404,
                    "url": target
                }

            data = r.json()
            resource_type = self._drive_resource_type(data.get("mimeType"), data.get("title"))
            info = {
                "Status": "Documento pubblico trovato",
                "Document ID": doc_id,
                "Tipo risorsa": resource_type,
                "Nome file": data.get("title") or data.get("name") or "N/D",
            }

            created_date = data.get("createdDate")
            modified_date = data.get("modifiedDate")
            if created_date:
                try:
                    dt = datetime.strptime(created_date, '%Y-%m-%dT%H:%M:%S.%fz')
                    info["Creato il (UTC)"] = dt.strftime('%Y/%m/%d %H:%M:%S')
                except Exception:
                    info["Creato il"] = str(created_date)
            if modified_date:
                try:
                    dt = datetime.strptime(modified_date, '%Y-%m-%dT%H:%M:%S.%fz')
                    info["Ultima modifica (UTC)"] = dt.strftime('%Y/%m/%d %H:%M:%S')
                except Exception:
                    info["Ultima modifica"] = str(modified_date)

            if data.get("description"):
                info["Descrizione"] = str(data.get("description"))[:250]
            if data.get("fileSize"):
                info["Dimensione file"] = self._human_bytes(data.get("fileSize"))
            if data.get("shared") is not None:
                info["Condiviso"] = "Sì" if data.get("shared") else "No"
            if data.get("copyRequiresWriterPermission") is not None:
                info["Copia richiede writer"] = "Sì" if data.get("copyRequiresWriterPermission") else "No"
            if data.get("mimeType"):
                info["MimeType"] = data.get("mimeType")
            if data.get("labels"):
                lbl = data.get("labels") or {}
                if lbl.get("starred") is not None:
                    info["In Evidenza"] = "Sì" if lbl.get("starred") else "No"
                if lbl.get("trashed") is not None:
                    info["Nel Cestino"] = "Sì" if lbl.get("trashed") else "No"

            user_permissions = []
            up = data.get("userPermission") or {}
            if up.get("id") == "me":
                if up.get("role"):
                    user_permissions.append(up["role"])
                if up.get("additionalRoles"):
                    user_permissions.extend(up.get("additionalRoles") or [])

            public_permissions = []
            owner = None
            for permission in data.get("permissions", []) or []:
                if permission.get("id") in ["anyoneWithLink", "anyone"]:
                    if permission.get("role"):
                        public_permissions.append(permission["role"])
                    if permission.get("additionalRoles"):
                        public_permissions.extend(permission.get("additionalRoles") or [])
                elif permission.get("role") == "owner":
                    owner = permission

            public_hints = self._drive_public_permissions(data.get("permissions", []) or [])
            info["Permessi pubblici"] = ", ".join(public_permissions) if public_permissions else (", ".join(public_hints) or "Nessun permesso pubblico esplicito")
            info["Visibilità"] = "Pubblica" if public_permissions else "Privata / non esplicitamente pubblica"
            if user_permissions and public_permissions != user_permissions:
                info["Permessi speciali utente"] = ", ".join(user_permissions)

            if owner:
                info["Owner Nome"] = owner.get("name", "N/D")
                info["Owner Email"] = owner.get("emailAddress", "N/D")
                if owner.get("emailAddress") and "@" in owner.get("emailAddress"):
                    info["Owner Domain"] = owner.get("emailAddress").split("@", 1)[1]
                info["Owner Google ID"] = owner.get("id", "N/D")

            capabilities = data.get("capabilities") or {}
            enabled_caps = [k for k, v in capabilities.items() if v]
            if enabled_caps:
                info["Capabilities"] = ", ".join(enabled_caps[:10])
                info["Canale viewer"] = "file" if "folder" not in resource_type.lower() else "folder"

            return {
                "username": doc_id,
                "type": "Doc GDrive",
                "info": info,
                "main_img": data.get("iconLink") or drive_icon,
                "status_code": 200,
                "url": data.get("alternateLink") or target
            }
        except Exception as e:
            probe = self._drive_probe_variant(doc_id)
            if probe.get("title"):
                return {
                    "username": doc_id,
                    "type": "Doc GDrive",
                    "info": {
                        "Status": "Risorsa pubblica rilevata da pagina Google Drive",
                        "Nome file": probe.get("title", "N/D"),
                        "Fonte variante": probe.get("source", "N/D"),
                        "Metodo": "viewer fallback",
                        "URL rilevato": probe.get("url", target),
                        "HTTP Status": str(probe.get("status", "N/D"))
                    },
                    "main_img": drive_icon,
                    "status_code": 206,
                    "url": probe.get("url", target)
                }

            return {
                "username": doc_id or target or "Google Doc",
                "type": "Doc GDrive",
                "info": {
                    "Status": f"Errore analisi: {e}",
                    "Document ID": doc_id or "N/D"
                },
                "main_img": drive_icon,
                "status_code": 500,
                "url": target
            }
# --- ANALISI DOMINIO AVANZATA (NSLOOKUP STYLE + ENRICHMENT) ---
    def _safe_response_json(self, resp):
        if not resp:
            return None
        try:
            return resp.json()
        except Exception:
            return None

    def _domain_headers_and_tls(self, domain):
        out = {}
        homepage = f"https://{domain}"
        try:
            r = requests.get(homepage, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            out["HTTP Status"] = str(r.status_code)
            out["Final URL"] = r.url
            headers = r.headers or {}
            if headers:
                header_map = {
                    "server": "Server",
                    "x-powered-by": "X-Powered-By",
                    "x-frame-options": "X-Frame-Options",
                    "x-content-type-options": "X-Content-Type-Options",
                    "referrer-policy": "Referrer-Policy",
                    "strict-transport-security": "HSTS",
                    "content-security-policy": "CSP",
                    "permissions-policy": "Permissions-Policy",
                    "cross-origin-opener-policy": "COOP",
                    "cross-origin-resource-policy": "CORP",
                    "cross-origin-embedder-policy": "COEP"
                }
                present = []
                missing = []
                for k, label in header_map.items():
                    v = headers.get(k) or headers.get(k.title())
                    if v:
                        out[label] = str(v)
                        present.append(label)
                    else:
                        missing.append(label)
                out["Security Headers Presenti"] = ", ".join(present) if present else "Nessuno"
                out["Security Headers Mancanti"] = ", ".join(missing[:9]) if missing else "Completo"
        except Exception as e:
            out["HTTP Status"] = f"Err: {e}"
            return out, ""

        return out, r.text

    def _domain_rdap_lookup(self, domain):
        out = {"RDAP": "N/D"}
        if not domain:
            return out
        rdap_endpoints = [
            "https://rdap.org/domain/",
            "https://rdap.nic.fr/rdap/domain/",
            "https://rdap.arin.net/registry/domain/",
            "https://rdap.radb.net/registry/domain/"
        ]
        for base in rdap_endpoints:
            try:
                r = requests.get(base + urllib.parse.quote(domain), timeout=8, headers={"Accept": "application/rdap+json", "User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    out["RDAP"] = f"HTTP {r.status_code} ({base})"
                    continue
                data = self._safe_response_json(r)
                if not isinstance(data, dict):
                    continue

                out["RDAP"] = "OK"
                if data.get("handle"):
                    out["RDAP Handle"] = str(data.get("handle"))
                if data.get("ldhName"):
                    out["RDAP LdhName"] = str(data.get("ldhName"))
                if data.get("unicodeName"):
                    out["RDAP Unicode"] = str(data.get("unicodeName"))
                if data.get("status"):
                    status = data.get("status")
                    if isinstance(status, list):
                        out["RDAP Status"] = ", ".join([str(s) for s in status])
                    else:
                        out["RDAP Status"] = str(status)
                if data.get("nameservers"):
                    ns = [str(n.get("ldhName") or n.get("unicodeName") or n.get("name", "")) for n in data.get("nameservers", []) if n]
                    ns = [x for x in ns if x]
                    if ns:
                        out["RDAP Nameservers"] = ", ".join(ns[:15])

                events = []
                for e in (data.get("events") or []):
                    if not isinstance(e, dict):
                        continue
                    action = e.get("eventAction") or e.get("action")
                    when = e.get("eventDate") or e.get("date")
                    if action and when:
                        events.append(f"{action}: {when}")
                if events:
                    out["RDAP Events"] = " | ".join(events[:12])

                entities = data.get("entities") or []
                role_map = []
                for ent in entities:
                    if not isinstance(ent, dict):
                        continue
                    role = ent.get("roles") or ent.get("role")
                    name = None
                    if ent.get("vcardArray"):
                        for item in ent.get("vcardArray", [])[1] if isinstance(ent.get("vcardArray"), list) and len(ent.get("vcardArray")) > 1 else []:
                            if isinstance(item, list) and len(item) >= 4 and item[0] in ("fn", "org"):
                                name = item[3]
                                break
                    if name is None:
                        name = ent.get("handle")
                    if role and name:
                        roles = role if isinstance(role, list) else [role]
                        role_map.append(f"{name} ({','.join(roles)})")
                if role_map:
                    out["RDAP Entities"] = ", ".join(role_map[:12])

                return out
            except Exception:
                continue
        return out

    def _scan_tls_chain(self, domain):
        out = {}
        if not domain:
            return out
        try:
            r = requests.get(
                f"https://api.ssllabs.com/api/v3/analyze?host={urllib.parse.quote(domain)}&fromCache=on&all=done",
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code != 200:
                out["TLS Chain"] = f"SSLLabs HTTP {r.status_code}"
                return out
            data = self._safe_response_json(r)
            if not isinstance(data, dict):
                out["TLS Chain"] = "Dati SSLLabs non validi"
                return out
            if data.get("status") and data.get("status") not in ("READY", "READY",):
                out["TLS Scan Stato"] = str(data.get("status"))
                return out
            endpoints = data.get("endpoints") or []
            if not endpoints:
                out["TLS Scan Stato"] = "Nessun endpoint disponibile"
                return out

            ep = endpoints[0]
            ep_url = ep.get("ipAddress") or ""
            if ep_url:
                out["TLS Scan Endpoint"] = str(ep_url)
            details = ep.get("details") or {}
            cert = details.get("cert") or {}
            if cert:
                if cert.get("subject"):
                    subj = ", ".join([f"{k[0]}={k[1]}" for k in cert.get("subject", [])]) if isinstance(cert.get("subject"), list) else str(cert.get("subject"))
                    out["TLS SSL Labs Subject"] = subj
                if cert.get("issuer"):
                    iss = ", ".join([f"{k[0]}={k[1]}" for k in cert.get("issuer", [])]) if isinstance(cert.get("issuer"), list) else str(cert.get("issuer"))
                    out["TLS SSL Labs Issuer"] = iss
                if cert.get("notAfter"):
                    out["TLS SSL Labs Valid To"] = str(cert.get("notAfter"))
                if cert.get("notBefore"):
                    out["TLS SSL Labs Valid From"] = str(cert.get("notBefore"))
                if cert.get("sha1Fingerprint"):
                    out["TLS SSL Labs SHA1"] = str(cert.get("sha1Fingerprint"))
                if cert.get("sha256Fingerprint"):
                    out["TLS SSL Labs SHA256"] = str(cert.get("sha256Fingerprint"))

            chain = details.get("chain") or []
            chain_items = []
            for idx, c in enumerate(chain[:8], start=1):
                if not isinstance(c, dict):
                    continue
                name = c.get("label") or f"Cert {idx}"
                issuer = c.get("issuer") or {}
                if isinstance(issuer, dict):
                    issuer_name = issuer.get("O") or issuer.get("CN") or ""
                else:
                    issuer_name = str(issuer)
                serial = c.get("serialNumber") or c.get("serial") or ""
                chain_items.append(f"{idx}:{name}" + (f"|{issuer_name}" if issuer_name else "") + (f"|{serial}" if serial else ""))
            if chain_items:
                out["TLS Cert Chain"] = " ; ".join(chain_items)
            return out
        except Exception as e:
            out["TLS Chain"] = f"Err: {e}"
            return out

    def _find_sitemap_and_robots(self, domain):
        out = {}
        robots_url = f"https://{domain}/robots.txt"
        try:
            r = requests.get(robots_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                out["robots.txt"] = "Trovato"
                txt = r.text
                sitemaps = []
                disallow = []
                for line in txt.splitlines():
                    line_low = line.strip().lower()
                    if line_low.startswith("sitemap:"):
                        sitemaps.append(line.split(":", 1)[1].strip())
                    if line_low.startswith("disallow:"):
                        value = line.split(":", 1)[1].strip()
                        if value:
                            disallow.append(value)
                if sitemaps:
                    out["Sitemap in robots.txt"] = " | ".join(sitemaps)
                if disallow:
                    out["robots Disallow (primi 15)"] = ", ".join(disallow[:15])
            else:
                out["robots.txt"] = f"HTTP {r.status_code}"
        except Exception as e:
            out["robots.txt"] = f"Err: {e}"

        for candidate in [f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml"]:
            try:
                r = requests.get(candidate, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200 and r.text:
                    out["Sitemap"] = candidate
                    out["Sitemap dimensione"] = f"{len(r.text)} caratteri"
                    break
            except Exception:
                continue
        if "Sitemap" not in out:
            out["Sitemap"] = "Non trovato"
        return out

    def _certificate_transparency(self, domain):
        out = {}
        if not domain:
            return out
        try:
            r = requests.get(f"https://crt.sh/?q={urllib.parse.quote(domain)}&output=json", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                out["CT"] = f"HTTP {r.status_code}"
                return out
            data = self._safe_response_json(r)
            if not isinstance(data, list) or not data:
                out["CT"] = "Nessun risultato"
                return out
            cert_count = len(data)
            entries = []
            issuers = set()
            names = set()
            timestamps = []
            for row in data[:200]:
                if not isinstance(row, dict):
                    continue
                if row.get("name_value"):
                    names.add(str(row.get("name_value")).strip())
                if row.get("issuer_name"):
                    issuers.add(str(row.get("issuer_name")).strip())
                if row.get("not_before"):
                    timestamps.append(str(row.get("not_before")).strip())
            if timestamps:
                out["CT certificati trovati"] = str(cert_count)
                out["CT primi emittenti"] = ", ".join(sorted(issuers)[:5]) if issuers else "N/D"
                out["CT SAN più frequenti (campione)"] = ", ".join(sorted(list(names))[:10]) if names else "N/D"
            else:
                out["CT certificati trovati"] = str(cert_count)
            return out
        except Exception as e:
            out["CT"] = f"Err: {e}"
            return out

    def _domain_dns_history(self, domain):
        key = (self.creds.get("dns_history_api_key") or "").strip()
        out = {}
        if not key:
            out["DNS History"] = "API key non configurata (dns_history_api_key)"
            return out
        try:
            url = f"https://api.securitytrails.com/v1/domain/{urllib.parse.quote(domain)}/dns/history"
            r = requests.get(
                url,
                headers={"Accept": "application/json", "APIKEY": key},
                timeout=10
            )
            if r.status_code != 200:
                out["DNS History"] = f"HTTP {r.status_code}"
                return out
            data = self._safe_response_json(r)
            if not isinstance(data, dict):
                out["DNS History"] = "Formato non valido"
                return out
            records = data.get("records") or []
            out["DNS History"] = f"{len(records)} snapshot disponibili"
            if records:
                for idx, rec in enumerate(records[:10], start=1):
                    at = rec.get("observed_at") or rec.get("updated")
                    ttl = rec.get("ttl")
                    val = rec.get("value")
                    if val:
                        out[f"DNS History #{idx}"] = f"{rec.get('type')} {val} (ttl={ttl}, t={at})"
            return out
        except Exception as e:
            out["DNS History"] = f"Err: {e}"
            return out

    def _domain_tech_fingerprint(self, html_text, headers):
        out = {}
        if not html_text:
            return out
        text = (html_text or "").lower()
        tech = set()
        markers = {
            "WordPress": ["wp-content", "wordpress"],
            "Drupal": ["drupal-settings-json", "drupal"],
            "Joomla": ["joomla"],
            "Next.js": ["__next", "next/static"],
            "React": ["react", "data-reactroot"],
            "Vue": ["vue.", "__vuerouter"],
            "Angular": ["ng-app", "angular"],
            "Django": ["csrfmiddlewaretoken", "csrf"],
            "Laravel": ["laravel", "csrf-token"],
            "Rails": ["_rails", "rails-ujs"],
            "Shopify": ["shopify"],
            "Cloudflare": ["cloudflare"],
            "Wix": ["wix.com", "static-parastorage.com"]
        }
        for name, checks in markers.items():
            if any(c in text for c in checks):
                tech.add(name)

        gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html_text, flags=re.IGNORECASE)
        if gen:
            tech.add(gen.group(1).strip())

        server_h = headers.get("server") if isinstance(headers, dict) else None
        if server_h:
            out["Server header"] = str(server_h)
        if "x-powered-by" in {k.lower() for k in (headers.keys() if isinstance(headers, dict) else {})}:
            out["X-Powered-By"] = headers.get("x-powered-by") or headers.get("X-Powered-By")

        if tech:
            out["Tech Stack stimato"] = ", ".join(sorted(tech))
        else:
            out["Tech Stack stimato"] = "Non identificato"
        return out

    def _wayback_summary(self, domain):
        out = {}
        try:
            url = f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(domain)}/*&output=json&fl=timestamp,statuscode,original&filter=statuscode:200&limit=20"
            r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                out["Wayback"] = f"HTTP {r.status_code}"
                return out
            data = self._safe_response_json(r)
            if not data or len(data) <= 1:
                out["Wayback"] = "Nessuna istantanea pubblica trovata"
                return out
            rows = data[1:]
            first = rows[-1][0] if rows else ""
            last = rows[0][0] if rows else ""
            out["Wayback snapshot"] = f"Totale: {len(rows)}"
            out["Wayback prima"] = str(first)
            out["Wayback ultima"] = str(last)
            return out
        except Exception as e:
            out["Wayback"] = f"Err: {e}"
            return out

    def analyze_domain_advanced(self, target):
        domain = target.replace("https://", "").replace("http://", "").split('/')[0].strip()
        info = {"00. Dominio": domain, "Status": " Analisi Domain Intelligence"}

        dns_tasks = {
            'A': '01. Indirizzi IPv4 (A)',
            'AAAA': '02. Indirizzi IPv6 (AAAA)',
            'MX': '03. Server di Posta (MX)',
            'NS': '04. Name Servers (NS)',
            'TXT': '05. Record TXT (SPF/Verify)',
            'CAA': '06. Cert Authority (CAA)'
        }

        for record, label in dns_tasks.items():
            try:
                answers = dns.resolver.resolve(domain, record)
                if record == 'MX':
                    info[label] = ", ".join([f"{r.exchange} (prio:{r.preference})" for r in answers])
                else:
                    info[label] = ", ".join([str(r) for r in answers])
            except Exception:
                info[label] = "Record non trovato"

        try:
            w = whois.whois(domain)
            if w.registrar:
                info["07. Registrar"] = str(w.registrar)
            if w.name_servers:
                info["08. Nameserver WHOIS"] = str(w.name_servers)
            if w.creation_date:
                c_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                info["09. Registrato il"] = str(c_date)[:10]
            if w.expiration_date:
                e_date = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                info["10. Scadenza"] = str(e_date)[:10]
            if w.updated_date:
                u_date = w.updated_date[0] if isinstance(w.updated_date, list) else w.updated_date
                info["11. Aggiornato"] = str(u_date)[:10]
            if w.country:
                info["12. Country"] = str(w.country)
        except Exception:
            pass

        headers_info, html = self._domain_headers_and_tls(domain)
        rdap_info = self._domain_rdap_lookup(domain)
        info.update(headers_info)
        info.update(rdap_info)
        if headers_info.get("HTTP Status", "").startswith("Err"):
            return info

        info.update(self._find_sitemap_and_robots(domain))
        info.update(self._domain_tech_fingerprint(html, headers_info))
        info.update(self._wayback_summary(domain))

        try:
            ssl_out = self._scan_tls_cert(domain)
            info.update(ssl_out)
        except Exception:
            pass
        try:
            info.update(self._scan_tls_chain(domain))
        except Exception:
            pass

        if self.creds.get("ct_api_enabled", True):
            info.update(self._certificate_transparency(domain))

        dns_hist = self._domain_dns_history(domain)
        info.update(dns_hist)

        return info

    def _scan_tls_cert(self, domain):
        out = {}
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((domain, 443), timeout=6) as raw_sock:
                ssock = ctx.wrap_socket(raw_sock, server_hostname=domain)
                with ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        out["TLS"] = "Certificato non disponibile"
                        return out
                    out["TLS"] = "Certificato ottenuto"
                    out["TLS Issuer"] = ", ".join([f"{k}={v}" for k, v in cert.get("issuer", [])]) if cert.get("issuer") else "N/D"
                    out["TLS Soggetto"] = ", ".join([f"{k}={v}" for k, v in cert.get("subject", [])]) if cert.get("subject") else "N/D"
                    if cert.get("notBefore"):
                        out["TLS valid from"] = str(cert.get("notBefore"))
                    if cert.get("notAfter"):
                        out["TLS valid to"] = str(cert.get("notAfter"))
                    alt = cert.get("subjectAltName") or []
                    if alt:
                        out["TLS SAN"] = ", ".join([v[1] for v in alt if len(v) > 1][:25])
                    if cert.get("version"):
                        out["TLS Version"] = str(cert.get("version"))
                    if cert.get("serialNumber"):
                        out["TLS Serial"] = str(cert.get("serialNumber"))
                    return out
        except Exception as e:
            out["TLS"] = f"Err: {e}"
            return out

        

    def scan_ip_services(self, ip):
        ip = ip.strip()
        services = []
        common_ports = {
            80: "HTTP",
            443: "HTTPS",
            22: "SSH",
            25: "SMTP",
            110: "POP3",
            143: "IMAP",
            3306: "MySQL",
            5432: "PostgreSQL",
            8080: "HTTP-Alt"
        }
        for port, name in common_ports.items():
            try:
                family = socket.AF_INET6 if ":" in ip else socket.AF_INET
                s = socket.socket(family, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex((ip, port))
                s.close()
                if result == 0:
                    services.append({"port": port, "service": name})
            except:
                continue
        try:
            hostnames = []
            try:
                rev = socket.gethostbyaddr(ip)
                hostnames = list({rev[0], *rev[1]})
            except:
                hostnames = []
            return services, hostnames
        except:
            return services, []

    def _domain_only(self, target):
        return target.replace("https://", "").replace("http://", "").split('/')[0].strip()

    def ip_rdap_lookup(self, ip):
        ip = ip.strip()
        rdap_servers = [
            "https://rdap.arin.net/registry/ip/",
            "https://rdap.ripe.net/ip/",
            "https://rdap.apnic.net/ip/",
            "https://rdap.lacnic.net/rdap/ip/",
            "https://rdap.afrinic.net/rdap/ip/",
        ]
        headers = {"Accept": "application/rdap+json"}
        for base in rdap_servers:
            try:
                r = requests.get(base + ip, headers=headers, timeout=6)
                if r.status_code == 200:
                    j = r.json()
                    out = {"Status": " RDAP OK"}
                    if j.get("handle"): out["Handle"] = str(j.get("handle"))
                    if j.get("name"): out["Name"] = str(j.get("name"))
                    if j.get("type"): out["Type"] = str(j.get("type"))
                    if j.get("startAddress"): out["Start"] = str(j.get("startAddress"))
                    if j.get("endAddress"): out["End"] = str(j.get("endAddress"))
                    if j.get("country"): out["Country"] = str(j.get("country"))
                    if j.get("parentHandle"): out["Parent"] = str(j.get("parentHandle"))
                    if j.get("events"):
                        evs = []
                        for ev in j.get("events", []):
                            try:
                                evs.append(f"{ev.get('eventAction','')}: {ev.get('eventDate','')}")
                            except:
                                continue
                        if evs: out["Events"] = " | ".join(evs[:6])
                    return out
            except:
                continue
        return {"Status": " RDAP non disponibile"}

    def shodan_host(self, ip):
        key = (self.creds.get("shodan_key") or "").strip()
        if not key:
            return None
        ip = (ip or "").strip()
        if not ip:
            return None
        try:
            url = f"https://api.shodan.io/shodan/host/{urllib.parse.quote(ip, safe='')}"
            r = requests.get(url, params={"key": key}, timeout=10)
            if r.status_code != 200:
                return {"Status": f" Shodan {r.status_code}"}
            j = r.json()
            out = {"Status": " Shodan OK"}
            if j.get("org"): out["Org"] = str(j.get("org"))
            if j.get("isp"): out["ISP"] = str(j.get("isp"))
            if j.get("asn"): out["ASN"] = str(j.get("asn"))
            if j.get("os"): out["OS"] = str(j.get("os"))
            if j.get("ports"): out["Ports"] = ", ".join([str(p) for p in j.get("ports", [])][:50])
            if j.get("hostnames"): out["Hostnames"] = ", ".join(j.get("hostnames", [])[:20])
            if j.get("domains"): out["Domains"] = ", ".join(j.get("domains", [])[:20])
            if j.get("tags"): out["Tags"] = ", ".join(j.get("tags", [])[:20])
            if j.get("vulns"):
                vul = j.get("vulns")
                if isinstance(vul, dict):
                    out["Vulns"] = ", ".join(list(vul.keys())[:20])
                elif isinstance(vul, list):
                    out["Vulns"] = ", ".join([str(x) for x in vul][:20])
            if j.get("last_update"): out["Last Update"] = str(j.get("last_update"))
            if j.get("country_name") or j.get("city"):
                out["Geo"] = ", ".join([x for x in [j.get("city"), j.get("country_name")] if x])
            return out
        except Exception as e:
            return {"Status": f" Shodan error: {e}"}

    def build_ip_graph(self, domain):
        domain = self._domain_only(domain)
        info = self.analyze_domain_advanced(domain)
        ips = []
        ips_v4 = info.get(" Indirizzi IPv4 (A)", "")
        ips_v6 = info.get(" Indirizzi IPv6 (AAAA)", "")
        if ips_v4 and ips_v4 != "Record non trovato":
            ips += [x.strip() for x in str(ips_v4).split(",") if x.strip()]
        if ips_v6 and ips_v6 != "Record non trovato":
            ips += [x.strip() for x in str(ips_v6).split(",") if x.strip()]
        ips = list(dict.fromkeys(ips))  # unique preserve order

        nodes_dict = {}
        edges = []
        dom_id = f"dom:{domain}"
        nodes_dict[dom_id] = {"id": dom_id, "label": domain, "shape": "box", "color": {"background": "#0d1326", "border": "#00e5ff"}, "font": {"color": "#ffffff"}}

        for ip in ips[:30]:
            ip_id = f"ip:{ip}"
            nodes_dict[ip_id] = {"id": ip_id, "label": ip, "shape": "dot", "size": 18, "color": {"background": "#3b82f6", "border": "#00e5ff"}, "font": {"color": "#ffffff"}}
            edges.append({"from": dom_id, "to": ip_id, "color": {"color": "#00e676"}, "arrows": "to"})

            services, _ = self.scan_ip_services(ip)
            for s in services[:20]:
                svc_id = f"svc:{ip}:{s['port']}"
                nodes_dict[svc_id] = {"id": svc_id, "label": f"{s['service']}:{s['port']}", "shape": "ellipse", "color": {"background": "#070a13", "border": "#1e293b"}, "font": {"color": "#94a3b8", "size": 10}}
                edges.append({"from": ip_id, "to": svc_id, "color": {"color": "#3b82f6"}, "arrows": "to"})

        return {"domain": domain, "ips": ips, "nodes": list(nodes_dict.values()), "edges": edges}

    def holehe_scan(self, email):
        email = (email or "").strip()
        if not email or "@" not in email:
            return [{"username": email, "type": "Holehe", "info": {"Status": " Email non valida"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 400, "url": ""}]

        try:
            import trio
            import httpx
            import pkgutil
            import importlib
            import inspect
            import holehe.modules
        except Exception as e:
            return [{"username": email, "type": "Holehe", "info": {"Status": f" Holehe non disponibile: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 500, "url": ""}]

        results = []

        async def _run():
            out = []
            async with httpx.AsyncClient(timeout=10) as client:
                for m in pkgutil.walk_packages(holehe.modules.__path__, holehe.modules.__name__ + "."):
                    modname = m.name
                    basename = modname.split(".")[-1]
                    try:
                        mod = importlib.import_module(modname)
                    except Exception:
                        continue

                    fn = getattr(mod, basename, None)
                    if fn and inspect.iscoroutinefunction(fn):
                        try:
                            with trio.move_on_after(8):
                                await fn(email, client, out)
                        except Exception:
                            continue
            return out

        try:
            raw = trio.run(_run)
        except Exception as e:
            return [{"username": email, "type": "Holehe", "info": {"Status": f" Errore esecuzione: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 500, "url": ""}]

        # Mostra solo risultati positivi o rate-limited (per non spam)
        for r in (raw or []):
            try:
                name = r.get("name") or "unknown"
                exists = bool(r.get("exists"))
                rate = bool(r.get("rateLimit"))
                if not (exists or rate):
                    continue

                info = {"Status": " Account trovato" if exists else " Rate limit"}
                if rate:
                    info["RateLimit"] = "Sì"
                if r.get("emailrecovery"):
                    info["Recovery Email"] = str(r.get("emailrecovery"))
                if r.get("phoneNumber"):
                    info["Recovery Phone"] = str(r.get("phoneNumber"))
                if r.get("others") is not None:
                    info["Others"] = str(r.get("others"))[:200]

                results.append({
                    "username": email,
                    "type": f"Holehe: {name}",
                    "info": info,
                    "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png",
                    "status_code": 200 if exists else 206,
                    "url": ""
                })
            except Exception:
                continue

        if not results:
            results = [{
                "username": email,
                "type": "Holehe",
                "info": {"Status": " Nessuna corrispondenza (o moduli falliti)"},
                "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png",
                "status_code": 404,
                "url": ""
            }]

        return results

    def ignorant_scan(self, phone_input):
        phone_input = (phone_input or "").strip()
        if not phone_input:
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": " Numero mancante"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 400, "url": ""}]

        try:
            import trio
            import httpx
            import pkgutil
            import importlib
            import inspect
            import ignorant.modules
        except Exception as e:
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": f" Ignorant non disponibile: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 500, "url": ""}]

        # Parse numero per ottenere country_code e national number
        cc = None
        national = None
        try:
            p = phonenumbers.parse(phone_input, None)
            if phonenumbers.is_possible_number(p):
                cc = str(p.country_code)
                national = str(p.national_number)
        except Exception:
            pass

        # Fallback: prova a togliere '+' e separare
        if not cc or not national:
            digits = re.sub(r"\D+", "", phone_input)
            if digits.startswith("00"):
                digits = digits[2:]
            # default IT se non specificato (fallback best effort)
            if phone_input.startswith("+") and len(digits) >= 4:
                # prova 1..3 cifre per country code
                for n in (1, 2, 3):
                    cc_try = digits[:n]
                    nat_try = digits[n:]
                    if nat_try and len(nat_try) >= 6:
                        cc = cc_try
                        national = nat_try
                        break
            if not cc or not national:
                cc = "39"
                national = digits

        results = []

        async def _run():
            out = []
            async with httpx.AsyncClient(timeout=10) as client:
                for m in pkgutil.walk_packages(ignorant.modules.__path__, ignorant.modules.__name__ + "."):
                    modname = m.name
                    basename = modname.split(".")[-1]
                    try:
                        mod = importlib.import_module(modname)
                    except Exception:
                        continue

                    fn = getattr(mod, basename, None)
                    if fn and inspect.iscoroutinefunction(fn):
                        try:
                            with trio.move_on_after(8):
                                await fn(national, cc, client, out)
                        except Exception:
                            continue
            return out

        try:
            raw = trio.run(_run)
        except Exception as e:
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": f" Errore esecuzione: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 500, "url": ""}]

        for r in (raw or []):
            try:
                name = r.get("name") or "unknown"
                exists = bool(r.get("exists"))
                rate = bool(r.get("rateLimit"))
                info = {"Status": " Presente" if exists else (" Rate limit" if rate else " Non presente")}
                if r.get("domain"):
                    info["Domain"] = str(r.get("domain"))
                if r.get("method"):
                    info["Method"] = str(r.get("method"))
                if rate:
                    info["RateLimit"] = "Sì"

                results.append({
                    "username": phone_input,
                    "type": f"Ignorant: {name}",
                    "info": info,
                    "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png",
                    "status_code": 206 if rate else (200 if exists else 404),
                    "url": ""
                })
            except Exception:
                continue

        if not results:
            results = [{
                "username": phone_input,
                "type": "Ignorant",
                "info": {"Status": " Nessuna corrispondenza (o moduli falliti)"},
                "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png",
                "status_code": 404,
                "url": ""
            }]

        return results

    def analyze_gmail(self, email):
        email = (email or "").strip()
        if not email.endswith('@gmail.com'):
            return None

        info = {"Status": "Analisi Gmail in corso..."}
        main_img = "https://cdn-icons-png.flaticon.com/512/281/281764.png" # Google icon
        status_code = 404

        try:
            # Undocumented endpoint, may break without notice.
            lookup_url = "https://accounts.google.com/_/lookup/accountlookup?hl=it"
            
            # This payload structure is based on observed requests from web clients.
            payload = f"[[null,null,null,null,[1,null,null,null,null,[null,\"{email}\"]]]]"

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Google-Accounts-XSRF': '1', # Required header
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
            }

            r = requests.post(lookup_url, headers=headers, data=payload, timeout=8)
            
            if r.status_code == 200:
                clean_response = r.text[5:] # Remove )]}' XSSI prefix
                data = json.loads(clean_response)
                
                # Navigate through the nested list structure to find user data.
                # This is highly dependent on the current API response format.
                user_data = data[0][2][1]
                
                gaia_id = user_data[8]
                name = user_data[3]
                pfp_url = user_data[2]

                info["Status"] = " Informazioni Trovate"
                status_code = 200
                if gaia_id: info[" Gaia ID"] = gaia_id
                if name: info[" Nome"] = name
                if pfp_url: main_img = pfp_url
                
            else:
                info["Status"] = f" Nessun risultato (Codice: {r.status_code})"

        except Exception as e:
            # This can happen if the endpoint changes, payload is wrong, or parsing fails.
            info["Status"] = " Errore durante l'analisi"
            info["Dettagli Errore"] = "L'endpoint di Google potrebbe essere cambiato."

        return {
            "username": email,
            "type": "Gmail Account",
            "info": info,
            "main_img": main_img,
            "status_code": status_code,
            "url": f"https://myaccount.google.com/?authuser={email}"
        }
    # --- TELEGRAM ---
    async def tg_send_code(self, api_id, api_hash, phone):
        global temp_tg_client, temp_phone_hash
        try:
            client = TelegramClient(StringSession(), int(api_id), api_hash, loop=telethon_loop)
            await client.connect()
            if not await client.is_user_authorized():
                temp_phone_hash = await client.send_code_request(phone); temp_tg_client = client; return "ok", "Inviato"
            else:
                self.creds['tg_session'] = client.session.save(); self.save_creds(self.creds); await client.disconnect(); return "authorized", "Gi Auth"
        except Exception as e: return "error", str(e)

    async def tg_verify_code(self, code, phone):
        global temp_tg_client, temp_phone_hash
        try:
            await temp_tg_client.sign_in(phone, code, phone_code_hash=temp_phone_hash.phone_code_hash)
            self.creds['tg_session'] = temp_tg_client.session.save(); self.save_creds(self.creds); await temp_tg_client.disconnect(); temp_tg_client = None; return "ok", "Successo"
        except Exception as e: return "error", str(e)

    # --- RICERCA TELEGRAM GLOBALE CON API ---
    async def _parse_tg_entity(self, client, entity, base_icon, query, exact=False):
        img_path = base_icon
        try:
            photo_bytes = await client.download_profile_photo(entity, file=bytes)
            if photo_bytes:
                img_path = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode()}"
        except: pass
        
        if hasattr(entity, 'first_name'): # Gestione Utenti/Bot
            info = {
                "Status": " Trovato (Match Esatto)" if exact else " Trovato (Ricerca API)",
                "ID Numerico": str(entity.id),
                "Tipologia": "Bot" if getattr(entity, 'bot', False) else "Utente",
            }
            if getattr(entity, 'first_name', None): info["Nome"] = entity.first_name
            if getattr(entity, 'last_name', None): info["Cognome"] = entity.last_name
            if getattr(entity, 'username', None): info["Username"] = f"@{entity.username}"
            if getattr(entity, 'phone', None): info["Telefono Visibile"] = f"+{entity.phone}"
            
            url = f"https://t.me/{entity.username}" if getattr(entity, 'username', None) else ""
            username_label = getattr(entity, 'username', None) or f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip()
            
        else: # Gestione Canali/Gruppi
            info = {
                "Status": " Trovato (Match Esatto)" if exact else " Trovato (Ricerca API)",
                "ID Numerico": str(entity.id),
                "Tipologia": "Canale/Gruppo",
                "Titolo": getattr(entity, 'title', 'Sconosciuto')
            }
            if getattr(entity, 'username', None): info["Username"] = f"@{entity.username}"
            if getattr(entity, 'participants_count', None): info["Partecipanti (Stima)"] = str(entity.participants_count)
            
            url = f"https://t.me/{entity.username}" if getattr(entity, 'username', None) else ""
            username_label = getattr(entity, 'title', 'Sconosciuto')
            
        return {
            "username": username_label,
            "type": "Telegram",
            "info": info,
            "main_img": img_path,
            "status_code": 200,
            "url": url
        }

    async def analyze_telegram(self, query):
        results = []
        seen_ids = set()
        base_icon = SOCIAL_MAP["Telegram"]["icon"]
        
        api_id = self.creds.get('tg_id')
        api_hash = self.creds.get('tg_hash')
        session_str = self.creds.get('tg_session')
        
        if not api_id or not api_hash or not session_str:
            info = {"Status": " Accesso Negato", "Note": "Inserisci API ID/HASH Telegram e fai Login per la ricerca profonda."}
            return [{"username": query, "type": "Telegram", "info": info, "main_img": base_icon, "status_code": 401, "url": ""}]
            
        try:
            client = TelegramClient(StringSession(session_str), int(api_id), api_hash, loop=telethon_loop)
            await client.connect()
            if not await client.is_user_authorized():
                raise Exception("Sessione scaduta")
                
            # 1. Tentiamo prima il Match Esatto (Molto pi preciso per trovare profili specifici)
            try:
                entity = await client.get_entity(query)
                res = await self._parse_tg_entity(client, entity, base_icon, query, exact=True)
                if res:
                    results.append(res)
                    seen_ids.add(entity.id)
            except Exception:
                pass 
                
            # 2. Procediamo con la Ricerca Globale allargata
            search_results = await client(functions.contacts.SearchRequest(q=query, limit=15))
            
            for user in search_results.users:
                if user.id not in seen_ids:
                    res = await self._parse_tg_entity(client, user, base_icon, query, exact=False)
                    if res: results.append(res)
                    seen_ids.add(user.id)
                    
            for chat in search_results.chats:
                if chat.id not in seen_ids:
                    res = await self._parse_tg_entity(client, chat, base_icon, query, exact=False)
                    if res: results.append(res)
                    seen_ids.add(chat.id)
                
            await client.disconnect()
            
            if not results:
                info = {"Status": " Nessun Risultato", "Note": "La ricerca API non ha prodotto risultati."}
                return [{"username": query, "type": "Telegram", "info": info, "main_img": base_icon, "status_code": 404, "url": ""}]
                
            return results

        except Exception as e:
            print(f"[*] Errore API Telegram: {e}")
            info = {"Status": " Errore API", "Note": str(e)}
            return [{"username": query, "type": "Telegram", "info": info, "main_img": base_icon, "status_code": 500, "url": ""}]

    async def get_tg_participants_csv(self, entity_id):
        api_id = self.creds.get('tg_id')
        api_hash = self.creds.get('tg_hash')
        session_str = self.creds.get('tg_session')
        
        if not api_id or not api_hash or not session_str:
            return "Errore: Autenticazione Telegram mancante."
            
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Username", "Nome", "Cognome", "Bot", "Premium"])
        
        try:
            client = TelegramClient(StringSession(session_str), int(api_id), api_hash, loop=telethon_loop)
            await client.connect()
            
            participants = await client.get_participants(int(entity_id))
            for p in participants:
                writer.writerow([
                    p.id,
                    p.username if p.username else "",
                    p.first_name if p.first_name else "",
                    p.last_name if p.last_name else "",
                    "Sì" if p.bot else "No",
                    "Sì" if getattr(p, 'premium', False) else "No"
                ])
                
            await client.disconnect()
            return output.getvalue()
        except Exception as e:
            return f"Errore durante l'estrazione: {str(e)}\n\nNota: Alcuni gruppi nascondono i membri o richiedono di essere iscritti."

    # --- PHONE FULL PARSING ---
    def _phone_portability_hint(self, country_code, national_number):
        key = (self.creds.get("numverify_key") or "").strip()
        if not key:
            return {"NumVerify": "Non configurato"}
        try:
            r = requests.get(
                "http://apilayer.net/api/validate",
                params={
                    "access_key": key,
                    "country_code": country_code,
                    "number": f"{country_code}{national_number}"
                },
                timeout=8
            )
            if r.status_code != 200:
                return {"NumVerify": f"HTTP {r.status_code}"}
            data = self._safe_response_json(r) or {}
            if not isinstance(data, dict):
                return {"NumVerify": "Formato risposta non valido"}
            if not data.get("valid"):
                return {"NumVerify": "Numero non valido"}
            out = {
                "NumVerify": "Numero validato",
                "Portabilità/Carrier": str(data.get("ported", "N/D")),
                "Carrier verificato": str(data.get("carrier") or "N/D"),
                "Tipo linea": str(data.get("line_type") or "N/D"),
                "Paese API": str(data.get("country_name") or "N/D"),
                "Prefisso internazionale API": str(data.get("country_code") or "N/D")
            }
            if data.get("location"):
                out["Località API"] = str(data.get("location"))
            if data.get("local_format"):
                out["Formato locale API"] = str(data.get("local_format"))
            return out
        except Exception as e:
            return {"NumVerify": f"Err: {e}"}

    def _phone_country_name(self, country_code):
        try:
            return str(pycountry.countries.get(numeric=str(country_code).zfill(3)).name)
        except Exception:
            try:
                return str(pycountry.countries.get(alpha_2=country_code).name)
            except Exception:
                return "N/D"

    def _normalize_carrier_name(self, carrier_name):
        carrier_name = (carrier_name or "").strip()
        if not carrier_name:
            return "N/D"
        txt = carrier_name.lower()
        replacements = {
            "ltd": " Ltd",
            "plc": " PLC",
            "srl": " s.r.l.",
            "inc": " Inc.",
            "sp zoo": " S.p.A.",
            "telefonica deutschland gmbh & co. ohg": "Telefonica",
            "vodafone italie": "Vodafone",
            "wind tre s.p.a.": "WindTre",
            "elysium": "Elysis",
        }
        for src, dst in replacements.items():
            if src in txt:
                if dst.strip() not in txt:
                    return f"{dst.strip()} (normalizzato)"
                break
        return carrier_name

    def _phone_score(self, info):
        score = 0
        if info.get("Validation") == "Possibile":
            score += 30
        if info.get("Validità") == "Valido":
            score += 35
        if info.get("09. Paese"):
            score += 5
        if info.get("Carrier"):
            score += 10
        if info.get("Timezone"):
            score += 10
        if info.get("02. Input Normalizzato") and info.get("03. Formato E164 (solo cifre)"):
            score += 10
        if info.get("NumVerify") == "Numero validato":
            score += 15
        if info.get("15. Coerenza formato") == "OK" or info.get("Coerenza formato") == "OK":
            score += 5
        if info.get("Portabilità/Carrier") and "Sì" in str(info.get("Portabilità/Carrier")):
            score += 10
        if info.get("Tipo numero") and "mobile" in str(info.get("Tipo numero")).lower():
            score += 5
        return min(100, score)

    async def analyze_phone(self, target):
        info = {"00. Input": target}
        clean_target = re.sub(r"[^0-9+]", "", target or "")
        wa_link, tg_link = f"https://wa.me/{clean_target.lstrip('+')}", f"https://t.me/{clean_target.lstrip('+')}"
        main_img = "https://cdn-icons-png.flaticon.com/512/159/159832.png"

        try:
            pn = phonenumbers.parse(target)
            tz_list = phone_timezone.time_zones_for_number(pn) or []
            carrier_name = (carrier.name_for_number(pn, "en") or "").strip()
            country_code = region_code_for_country_code(pn.country_code)
            geo_desc = geocoder.description_for_number(pn, "en") or ""

            info["01. Formato Input"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            info["02. Input Normalizzato"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)
            info["03. Formato E164 (solo cifre)"] = info["02. Input Normalizzato"].replace("+", "")
            info["04. Formato Nazionale"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.NATIONAL)
            info["05. Validation"] = "Possibile" if phonenumbers.is_possible_number(pn) else "Possibile ma insolito"
            if phonenumbers.is_valid_number(pn):
                info["05. Validità"] = "Valido"
            else:
                info["05. Validità"] = "Non valido"
            info["06. Prefisso internazionale"] = f"+{pn.country_code}"
            info["07. ISO Paese"] = country_code or "N/D"
            info["08. Paese"] = geo_desc or self._phone_country_name(country_code)
            info["09. Paese ISO nome"] = self._phone_country_name(country_code) if country_code else "N/D"
            if geo_desc and "," in geo_desc:
                parts = [x.strip() for x in geo_desc.split(",") if x.strip()]
                if len(parts) > 1:
                    info["16. Regione stimata"] = parts[-1]
                    info["17. Città stimata"] = parts[0]
                else:
                    info["16. Regione stimata"] = geo_desc
            info["10. Timezone"] = ", ".join(sorted(set(tz_list))) if tz_list else "N/D"
            info["Timezone"] = info["10. Timezone"]
            info["11. Carrier"] = carrier_name or "N/D"
            info["Carrier"] = info["11. Carrier"]
            info["12. Operatore normalizzato"] = self._normalize_carrier_name(carrier_name) if carrier_name else "N/D"
            info["Carrier normalizzato"] = info["12. Operatore normalizzato"]
            info["13. Numero Type"] = str(phonenumbers.number_type(pn))
            ntype = str(phonenumbers.number_type(pn)).lower()
            info["14. Tipo Linea"] = "Mobile" if "mobile" in ntype else "Voce/Fisso"
            info["Tipo numero"] = info["14. Tipo Linea"]

            normalized = re.sub(r"\D", "", info["02. Input Normalizzato"])
            original_digits = re.sub(r"\D", "", target or "")
            info["15. Coerenza formato"] = "OK" if normalized == original_digits else "Corretto con normalizzazione"

            if phonenumbers.is_valid_number(pn):
                ext = self._phone_portability_hint(str(pn.country_code), str(pn.national_number))
                if isinstance(ext, dict):
                    info.update(ext)
        except Exception as e:
            info["Parsing"] = f"Errore: {e}"

        score = self._phone_score(info)
        info["16. Affidabilità contatto"] = f"{score}/100"

        info["20. WhatsApp"] = f"Vedi link: {wa_link}"
        info["21. Telegram"] = "Checking..."

        if self.creds.get('tg_session'):
            try:
                client = TelegramClient(StringSession(self.creds['tg_session']), int(self.creds['tg_id']), self.creds['tg_hash'], loop=telethon_loop)
                await client.connect()
                try:
                    entity = await client.get_entity(target)
                    info["TG Name"] = f"{entity.first_name} {entity.last_name or ''}".strip()
                    info["TG ID"] = str(entity.id)
                    info["21. Telegram"] = " ATTIVO"
                    if entity.username: 
                        info["TG User"] = f"@{entity.username}"
                        tg_link = f"https://t.me/{entity.username}"
                    try: 
                        p = await client.download_profile_photo(entity, file=bytes)
                        if p:
                            main_img = f"data:image/jpg;base64,{base64.b64encode(p).decode()}"
                    except:
                        pass
                except:
                    info["21. Telegram"] = " Non Trovato/Privacy"

                try:
                    bot = "TrueCalleRobot"
                    await client.send_message(bot, clean_target)
                    await asyncio.sleep(3)
                    msgs = await client.get_messages(bot, limit=1)
                    if msgs:
                        txt = msgs[0].message
                        if "Name" in txt or "Nome" in txt:
                            info["TrueCaller"] = " FOUND"
                            lines = txt.split('\n')
                            for line in lines:
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    clean_k = k.strip().replace("*", "")
                                    clean_v = v.strip().replace("`", "")
                                    if len(clean_v) > 1 and "Limit" not in clean_k:
                                        info[f"TC_{clean_k}"] = clean_v
                except:
                    pass
                await client.disconnect()
            except:
                info["TG Error"] = "Auth Fallita"
        return main_img, info, tg_link, wa_link

    def check_revolut(self, target):
        try:
            r = requests.get(f"https://revolut.me/api/web-profile/{target}", headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
            if r.status_code == 200:
                d = r.json()
                return {"Name": f"{d.get('firstName')} {d.get('lastName')}", "Tag": f"@{d.get('revtag')}", "Country": d.get('country')}, 200
            return {}, 404
        except: return {}, 404

    def check_paypal(self, target):
        try:
            target_clean = urllib.parse.quote(target.strip())
            r = session.get(f"https://www.paypal.com/paypalme/{target_clean}", timeout=5)
            if r.status_code == 200 and target_clean.lower() in r.text.lower():
                return " Attivo", f"https://www.paypal.com/paypalme/{target_clean}", 200
            return " No", "", 404
        except Exception as e:
            print(f"[*] Errore PayPal: {e}")
            return " Err", "", 404

    def _safe_social_json(self, html_text):
        if not html_text:
            return None
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", html_text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        m = re.search(r"window\.__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*(\{.*?\});", html_text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        return None

    def _social_playwright_probe(self, platform, username, url, base_icon=None):
        base_icon = base_icon or ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--log-level=3", "--disable-blink-features=AutomationControlled"])
                page = browser.new_page()
                page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
                response = page.goto(url, wait_until="domcontentloaded", timeout=18000)
                status_code = response.status if response else 500
                html = page.content() if response else ""
                final_url = response.url if response else url
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            if not soup:
                return None

            info = {"Profile": final_url}
            title = ""
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = str(og_title.get("content", "")).strip()
            if not title:
                twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
                if twitter_title and twitter_title.get("content"):
                    title = str(twitter_title.get("content", "")).strip()
            if not title and soup.title and soup.title.text:
                title = str(soup.title.text).strip()

            if title:
                info["Nome"] = title

            desc = ""
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = str(og_desc.get("content", "")).strip()
            if not desc:
                twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
                if twitter_desc and twitter_desc.get("content"):
                    desc = str(twitter_desc.get("content", "")).strip()
            if desc:
                info["Bio"] = desc[:260]

            profile_img = ""
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                profile_img = str(og_img.get("content", "")).strip()

            found = bool(info.get("Nome") or info.get("Bio") or profile_img)
            if status_code == 404:
                info["Status"] = f"Non Trovato (Playwright HTTP {status_code})"
                found = False
            elif status_code in (401, 403, 429):
                info["Status"] = f"Accesso limitato (Playwright HTTP {status_code})"
                found = False
            elif status_code >= 500:
                info["Status"] = f"Errore accesso (Playwright HTTP {status_code})"
                found = False
            elif found:
                info["Status"] = f"Online (Playwright/OG) - {platform}"
            else:
                info["Status"] = f"Profilo non verificabile (Playwright HTTP {status_code})"

            if not found and status_code >= 400:
                return self._social_result(platform, username, info, profile_img or base_icon, status_code, final_url, False)
            return self._social_result(platform, username, info, profile_img or base_icon, status_code, final_url, found)
        except Exception:
            return None

    def _social_result(self, platform, username, info, image, status_code, url, found=True):
        if info is None:
            info = {}
        if isinstance(info, dict):
            info = dict(info)
            info["__found"] = bool(found)
        else:
            info = {"Status": str(info), "__found": bool(found)}
        return {
            "username": username,
            "type": platform,
            "info": info,
            "main_img": image,
            "status_code": status_code,
            "url": url
        }

    def analyze_social_github(self, username, base):
        url = f"https://github.com/{urllib.parse.quote(username)}"
        img = base["icon"]
        info = {"Status": " Richiesta API", "Profile": url}
        try:
            r = requests.get(f"https://api.github.com/users/{urllib.parse.quote(username)}", timeout=10)
            if r.status_code == 404:
                return [self._social_result("GitHub", username, {"Status": " Non Trovato"}, img, 404, url, False)]
            if r.status_code != 200:
                return None
            d = r.json()
            info["Status"] = " Online (API GitHub)"
            if d.get("name"): info["Nome"] = d.get("name")
            if d.get("bio"): info["Bio"] = str(d.get("bio")).replace('\n', ' ')
            if d.get("location"): info["Location"] = d.get("location")
            if d.get("company"): info["Azienda"] = d.get("company")
            if d.get("blog"): info["Website"] = d.get("blog")
            if d.get("twitter_username"): info["X"] = d.get("twitter_username")
            info["Followers"] = str(d.get("followers", 0))
            info["Following"] = str(d.get("following", 0))
            info["Repo Pubbliche"] = str(d.get("public_repos", 0))
            if d.get("created_at"): info["Iscritto il"] = d.get("created_at")[:10]
            if d.get("updated_at"): info["Aggiornato il"] = d.get("updated_at")[:10]
            if d.get("id"): info["ID Utente"] = str(d.get("id"))
            return [self._social_result("GitHub", username, info, d.get("avatar_url", img), 200, d.get("html_url", url), True)]
        except Exception:
            return None

    def analyze_social_reddit(self, username, base):
        api_url = f"https://www.reddit.com/user/{urllib.parse.quote(username)}/about.json"
        url = f"https://www.reddit.com/user/{urllib.parse.quote(username)}"
        info = {"Profile": url, "Status": " Analisi Reddit"}
        try:
            r = requests.get(api_url, headers={"User-Agent":"Mozilla/5.0", "Accept":"application/json"}, timeout=10)
            if r.status_code == 404:
                info["Status"] = " Non Trovato"
                return [self._social_result("Reddit", username, info, base["icon"], 404, url, False)]
            if r.status_code in (403, 429):
                return [self._social_result("Reddit", username, {"Status": "Blocco temporaneo (Reddit)", "Profile": url, "Nota": f"HTTP {r.status_code}"}, base["icon"], 200, url, False)]
            if r.status_code != 200:
                return None
            j = self._safe_response_json(r)
            d = (j or {}).get("data", {})
            if not d:
                info["Status"] = " Non Trovato"
                return [self._social_result("Reddit", username, info, base["icon"], 404, url, False)]

            info["Status"] = " Online (Reddit API)"
            info["Nome"] = d.get("name") or username
            info["Karma Totale"] = str(d.get("total_karma", 0))
            info["Post Karma"] = str(d.get("link_karma", 0))
            info["Comment Karma"] = str(d.get("comment_karma", 0))
            info["ID Reddit"] = str(d.get("id") or "N/D")
            info["Is Gold"] = "Sì" if d.get("is_gold") else "No"
            info["Gold Expire"] = str(d.get("gold_expiration") or "N/D")
            info["Account Creato"] = self._crypto_ts_to_utc(d.get("created_utc")) if d.get("created_utc") else "N/D"
            if d.get("icon_img"): info["Avatar"] = d.get("icon_img")
            return [self._social_result("Reddit", username, info, d.get("icon_img") or base["icon"], 200, url, True)]
        except Exception:
            return None

    def analyze_social_tiktok(self, username, base):
        clean = urllib.parse.quote((username or "").lstrip("@"))
        url = f"https://www.tiktok.com/@{clean}"
        info = {"Status": " Analisi TikTok", "Profile": url}
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"en-US,en;q=0.9"})
            if r.status_code == 403:
                return [self._social_result("TikTok", username, {"Status": "Possibile protezione anti-bot", "Profile": url}, base["icon"], 200, url, False)]
                return None
            if r.status_code != 200:
                return [self._social_result("TikTok", username, {"Status": " Non Trovato", "Nota": f"HTTP {r.status_code}", "Profile": url}, base["icon"], r.status_code, url, False)]
            html = r.text
            js = self._safe_social_json(html) or {}
            if isinstance(js, dict):
                user_info = js.get("__DEFAULT_SCOPE__", {})
                if isinstance(user_info, dict):
                    u = user_info.get("userInfo") or user_info.get("webapp.user-detail")
                    if isinstance(u, dict):
                        user = u.get("user")
                        if isinstance(user, dict):
                            info["Status"] = " Online (JSON/TikTok)"
                            if user.get("nickname"): info["Nome"] = user.get("nickname")
                            if user.get("id"): info["ID Numerico"] = str(user.get("id"))
                            if user.get("uniqueId"): info["Handle"] = f"@{user.get('uniqueId')}"
                            if user.get("signature"): info["Bio"] = str(user.get("signature")).replace('\n', ' | ')
                            if user.get("followers"): info["Followers"] = str(user.get("followers"))
                            if user.get("following"): info["Seguiti"] = str(user.get("following"))
                            if user.get("heart"): info["Likes"] = str(user.get("heart"))
                            if user.get("video"): info["Video"] = str(user.get("video"))
                        return [self._social_result("TikTok", username, info, base["icon"], 200, url, True)]
            soup = BeautifulSoup(html, 'html.parser')
            t_title = soup.find("title")
            if t_title: info["Nome"] = t_title.text.split("(")[0].strip()
            og_desc = soup.find("meta", property="og:description")
            if og_desc: info["Bio"] = str(og_desc.get("content", "")).replace('\n', ' | ')
            return [self._social_result("TikTok", username, info, base["icon"], 200, url, bool(info.get("Nome") or info.get("Bio")))]
        except Exception:
            return None

    def analyze_social_youtube(self, username, base):
        uname = urllib.parse.quote((username or "").lstrip("@"))
        url = f"https://www.youtube.com/@{uname}"
        info = {"Profile": url, "Status": " Analisi YouTube"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"en-US,en;q=0.9"})
            if r.status_code == 404:
                return [self._social_result("YouTube", username, {"Status": " Non Trovato", "Profile": url}, base["icon"], 404, url, False)]
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            og_title = soup.find("meta", property="og:title")
            if og_title:
                info["Canale"] = og_title.get("content", "").replace(" - YouTube", "").strip()
            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                info["Descrizione"] = str(og_desc.get("content", "")).replace('\n', ' | ')[:240]
            meta = re.search(r'"subscriberCountText":\\{"simpleText":"([^"]+)"', r.text)
            if meta:
                info["Iscritti"] = meta.group(1)
            channel_id = re.search(r'"channelId":"(UC[0-9A-Za-z_-]{22})"', r.text)
            if channel_id: info["Channel ID"] = channel_id.group(1)
            info["Status"] = " Online (Via pagina YouTube)"
            return [self._social_result("YouTube", username, info, base["icon"], 200, url, True)]
        except Exception:
            return None

    def analyze_social_linkedin(self, username, base):
        clean = urllib.parse.quote((username or "").lstrip("@").strip("/"))
        url = f"https://www.linkedin.com/in/{clean}/"
        info = {"Profile": url, "Status": " Analisi LinkedIn"}
        try:
            r = requests.get(f"https://r.jina.ai/http://www.linkedin.com/in/{clean}/", timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200 or "not found" in r.text.lower():
                return [self._social_result("LinkedIn", username, {"Status": " Profilo non indicizzato da cache", "Profile": url}, base["icon"], 404, url, False)]
            text = r.text
            title = re.search(r"# (.+) - LinkedIn", text)
            if title:
                info["Nome/Azienda"] = title.group(1).strip()
            snippet = text.split("\n", 1)[1][:220] if "\n" in text else ""
            if snippet:
                info["Snippet"] = snippet
            info["Status"] = " Online (via Jina AI cache)"
            return [self._social_result("LinkedIn", username, info, base["icon"], 200, url, True)]
        except Exception:
            return None

    def analyze_social_pinterest(self, username, base):
        url = f"https://www.pinterest.com/{urllib.parse.quote(username)}/"
        info = {"Profile": url, "Status": " Analisi Pinterest"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"en-US,en;q=0.9"})
            if r.status_code != 200:
                if r.status_code == 403:
                    return [self._social_result("Pinterest", username, {"Status": "Pagina bloccata (anti-bot)", "Profile": url}, base["icon"], 200, url, False)]
                return [self._social_result("Pinterest", username, {"Status": " Non Trovato", "Nota": f"HTTP {r.status_code}", "Profile": url}, base["icon"], r.status_code, url, False)]
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.find("title")
            if title and title.text:
                info["Nome"] = title.text.split(" | ")[0].strip()
            raw = r.text
            fl = re.search(r'"follower_count":(\d+)', raw)
            if fl: info["Followers"] = fl.group(1)
            following = re.search(r'"following_count":(\d+)', raw)
            if following: info["Seguiti"] = following.group(1)
            info["Status"] = " Online (via pagina Pinterest)"
            return [self._social_result("Pinterest", username, info, base["icon"], 200, url, bool(info.get("Nome") or info.get("Followers") or info.get("Seguiti")))]
        except Exception:
            return None

    def analyze_social_discord(self, username, base):
        clean = (username or "").strip()
        if not clean:
            return None
        info = {"Status": " Analisi Discord"}
        if re.fullmatch(r"\d{17,20}", clean):
            url = f"https://discord.com/api/v10/users/{clean}"
            info["Profile"] = f"https://discord.com/users/{clean}"
            try:
                r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
                if r.status_code == 200:
                    js = self._safe_response_json(r) or {}
                    if isinstance(js, dict):
                        if js.get("id"):
                            info["ID Utente"] = js.get("id")
                        if js.get("username"): info["Nome"] = js.get("username")
                        if js.get("global_name"): info["Nome Pubblico"] = js.get("global_name")
                        if js.get("discriminator"): info["Tag"] = js.get("discriminator")
                    info["Status"] = " Utente disponibile tramite API"
                    return [self._social_result("Discord", clean, info, base["icon"], 200, f"https://discord.com/users/{clean}", True)]
                if r.status_code == 404:
                    return [self._social_result("Discord", clean, {"Status": " Profilo non trovato", "Profile": f"https://discord.com/users/{clean}"}, base["icon"], 404, f"https://discord.com/users/{clean}", False)]
                if r.status_code in (403, 429):
                    return [self._social_result("Discord", clean, {"Status": "Discord API bloccata (antibot)", "Profile": f"https://discord.com/users/{clean}", "Nota": f"HTTP {r.status_code}"}, base["icon"], 200, url, False)]
            except Exception:
                pass
        url = f"https://discord.com/search?q={urllib.parse.quote(clean)}"
        return [self._social_result("Discord", clean, {"Status": " Analisi in modalità web", "Nota": "Discord richiede verifica anti-bot o login per dettagli di profilo.", "Profile": url}, base["icon"], 200, url, False)]

    def analyze_social_twitch(self, username, base):
        url = f"https://www.twitch.tv/{urllib.parse.quote(username)}"
        info = {"Profile": url, "Status": " Analisi Twitch"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200:
                if r.status_code == 404:
                    return [self._social_result("Twitch", username, {"Status": " Non Trovato", "Profile": url}, base["icon"], 404, url, False)]
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.find("meta", property="og:title")
            if title and title.get("content"): info["Nome"] = title.get("content").split("-")[0].strip()
            bio = soup.find("meta", property="og:description")
            if bio and bio.get("content"): info["Bio"] = bio.get("content")[:240]
            views = re.search(r'"viewCount":(\d+)', r.text)
            if views: info["Views"] = views.group(1)
            followers = re.search(r'"followers":(\d+)', r.text)
            if followers: info["Followers"] = followers.group(1)
            info["Status"] = " Online (pagina Twitch)"
            return [self._social_result("Twitch", username, info, base["icon"], 200, url, bool(info.get("Nome") or info.get("Followers")))]
        except Exception:
            return None

    def analyze_social_steam(self, username, base):
        clean = (username or "").strip()
        url = f"https://steamcommunity.com/id/{urllib.parse.quote(clean)}" if not re.fullmatch(r"\d{16,20}", clean) else f"https://steamcommunity.com/profiles/{clean}"
        info = {"Profile": url, "Status": " Analisi Steam"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200:
                if r.status_code == 404:
                    return [self._social_result("Steam", username, {"Status": " Non Trovato", "Profile": url}, base["icon"], 404, url, False)]
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            name = re.search(r'"profileData">\\{"name":"([^"]+)"', r.text)
            if name: info["Nome"] = name.group(1)
            if not name:
                title = soup.find("title")
                if title and title.text:
                    info["Nome"] = title.text.split(" - ")[0]
            if "SteamID" in r.text:
                sid = re.search(r'"steamid":"(7656\\d+)"', r.text)
                if sid: info["SteamID"] = sid.group(1)
            info["Status"] = " Online (Steam)"
            return [self._social_result("Steam", username, info, base["icon"], 200, url, bool(info.get("Nome") or info.get("SteamID")))]
        except Exception:
            return None

    def analyze_social_spotify(self, username, base):
        clean = urllib.parse.quote((username or "").strip())
        url = f"https://open.spotify.com/user/{clean}"
        info = {"Profile": url, "Status": " Analisi Spotify"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code == 404:
                return [self._social_result("Spotify", username, {"Status": " Non Trovato", "Profile": url}, base["icon"], 404, url, False)]
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.find("meta", property="og:title")
            if title and title.get("content"): info["Utente"] = title.get("content")
            desc = soup.find("meta", property="og:description")
            if desc and desc.get("content"): info["Descrizione"] = desc.get("content")[:260]
            info["Status"] = " Online (Spotify)"
            return [self._social_result("Spotify", username, info, base["icon"], 200, url, bool(info.get("Utente") or info.get("Descrizione")))]
        except Exception:
            return None

    def analyze_social_soundcloud(self, username, base):
        clean = urllib.parse.quote((username or "").strip())
        url = f"https://soundcloud.com/{clean}"
        info = {"Profile": url, "Status": " Analisi SoundCloud"}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"en-US,en;q=0.9"})
            if r.status_code != 200:
                if r.status_code == 404:
                    return [self._social_result("SoundCloud", username, {"Status": " Non Trovato", "Profile": url}, base["icon"], 404, url, False)]
                return None
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.find("meta", property="og:title")
            if title and title.get("content"): info["Nome"] = title.get("content")
            desc = soup.find("meta", property="og:description")
            if desc and desc.get("content"): info["Bio"] = desc.get("content")[:240]
            followers = re.search(r'"followersCount":(\d+)', r.text)
            if followers: info["Followers"] = followers.group(1)
            tracks = re.search(r'"track_count":(\d+)', r.text)
            if tracks: info["Tracks"] = tracks.group(1)
            info["Status"] = " Online (SoundCloud)"
            return [self._social_result("SoundCloud", username, info, base["icon"], 200, url, bool(info.get("Nome") or info.get("Followers") or info.get("Tracks")))]
        except Exception:
            return None

    def _crypto_ts_to_utc(self, value):
        try:
            return datetime.utcfromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return str(value)

    def _crypto_ts_window(self, timestamps):
        values = []
        for t in timestamps:
            try:
                iv = int(t)
            except Exception:
                continue
            if iv > 0:
                values.append(iv)
        if not values:
            return None, None, None
        first_ts = min(values)
        last_ts = max(values)
        try:
            first_utc = self._crypto_ts_to_utc(first_ts)
            last_utc = self._crypto_ts_to_utc(last_ts)
            age_days = (datetime.utcnow() - datetime.utcfromtimestamp(first_ts)).days
        except Exception:
            return first_ts, last_ts, None
        return first_utc, last_utc, age_days

    def _ripple_to_unix(self, ripple_ts):
        try:
            return int(ripple_ts) + 946684800
        except Exception:
            return None

    def _infer_crypto_risk(self, tx_count, timestamps, counterparties, ticker, balance=0):
        labels = []
        unique_parties = len(counterparties)
        total = int(tx_count or 0)
        timestamps = [t for t in timestamps if isinstance(t, (int, float))]
        if unique_parties == 0 and total == 0:
            return "Nessun contatto on-chain rilevato"

        if total > 3000:
            labels.append("Rischio medio: alto volume transazioni")
        if unique_parties > 180:
            labels.append("Profilo ad alta connettività (possibile Exchange)")
        if unique_parties <= 2 and total > 50:
            labels.append("Pattern service/bridge (pochi peer, molti movimenti)")
        if total > 0 and len(timestamps) >= 2:
            elapsed = max(timestamps) - min(timestamps)
            if elapsed and elapsed < 24 * 3600:
                labels.append("Attività concentrata in <24h")
        if unique_parties < 3 and total > 10:
            labels.append("Possibile account specializzato (service)")
        if ticker in ["XRP"] and total > 500:
            labels.append("Attività elevata su ledger bridge-focused")
        if ticker in ["XRP"] and any("amm" in str(p).lower() for p in counterparties):
            labels.append("Possibile interazione con bridge/AMM")
        concentration, _ = self._crypto_peer_stats(counterparties)
        if concentration and concentration > 0.80 and len(counterparties) > 0:
            labels.append("Concentratore: 1-2 controparti dominanti")
        if isinstance(balance, (int, float)) and balance < 0.00005:
            labels.append("Saldo on-chain molto basso")
        if total <= 3 and unique_parties <= 3:
            labels.append("Profilo con bassa attività")
        if not labels:
            return "Nessun alert"
        return " | ".join(labels)

    def _crypto_peer_stats(self, counterparties):
        if not counterparties:
            return None, 0
        sorted_peers = sorted(counterparties.items(), key=lambda x: x[1], reverse=True)
        top = sorted_peers[0][1] if sorted_peers else 0
        total = sum(counterparties.values()) or 0
        concentration = (top / total) if total else 0
        return concentration, len(sorted_peers)

    def _crypto_top_counterparties(self, peer_map, top_n=5):
        if not peer_map:
            return "N/A"
        return ", ".join([f"{k}:{v}" for k, v in sorted(peer_map.items(), key=lambda x: x[1], reverse=True)[:top_n]])

    def _evm_token_metadata(self, explorer_url, address):
        out = {"Token metadata": "N/A"}
        try:
            r = requests.get(
                f"https://{explorer_url}/api?module=account&action=tokentx&address={address}&page=1&offset=60&sort=desc",
                timeout=8
            )
            if r.status_code != 200:
                return out
            data = self._safe_response_json(r)
            if not isinstance(data, dict) or data.get("status") != "1":
                return out
            tokens = {}
            for item in data.get("result", []):
                sym = item.get("tokenSymbol") or item.get("tokenName") or "Unknown"
                name = item.get("tokenName") or ""
                dec = item.get("tokenDecimal") or ""
                tokens[sym] = {"name": name, "dec": dec}
            if tokens:
                out["Token metadata"] = ", ".join([f"{k} ({v['name']})" for k, v in list(tokens.items())[:15]])
        except Exception:
            pass
        return out

    def get_crypto_data(self, address, name, ticker):
        """
        Recupera info base + metadati avanzati (timestamp, controparti top, metrica rischio).
        """
        info = {
            "Status": " Trovato",
            "Indirizzo": address,
            "Rete": name
        }
        graph_data = []

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            peer_counter = {}
            tx_count = None
            timestamps = []
            balance = 0

            def _commit_tx_window():
                first_utc, last_utc, age_days = self._crypto_ts_window(timestamps)
                if first_utc:
                    info["Prima transazione UTC"] = first_utc
                    info["Ultima transazione UTC"] = last_utc
                    if age_days is not None:
                        info["Età prima tx (giorni)"] = str(age_days)

            # --- BITCOIN ---
            if ticker == "BTC":
                r = requests.get(f"https://mempool.space/api/address/{address}", headers=headers, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    stats = data.get("chain_stats", {})
                    funded = stats.get("funded_txo_sum", 0) / 100_000_000
                    spent = stats.get("spent_txo_sum", 0) / 100_000_000
                    tx_count = stats.get("tx_count", 0)
                    balance = funded - spent
                    info[f"Bilancio Attuale ({ticker})"] = f"{balance:.8f}"
                    info[f"Totale Ricevuto ({ticker})"] = f"{funded:.8f}"
                    info["Transazioni Totali"] = str(tx_count)
                    if data.get("mempool_stats") and isinstance(data["mempool_stats"], dict):
                        info["Mempool tx"] = str(data["mempool_stats"].get("count", "N/D"))

                r_txs = requests.get(f"https://mempool.space/api/address/{address}/txs/chain", headers=headers, timeout=10)
                txs = r_txs.json() if r_txs.status_code == 200 else []
                if isinstance(txs, list):
                    for tx in txs[:80]:
                        ts = tx.get("status", {}).get("block_time")
                        if ts:
                            timestamps.append(int(ts))
                        for vin in tx.get("vin", []) or []:
                            p = (vin.get("prevout") or {}).get("scriptpubkey_address")
                            if p and p != address:
                                peer_counter[p] = peer_counter.get(p, 0) + 1
                        for vout in tx.get("vout", []) or []:
                            p = vout.get("scriptpubkey_address")
                            if p and p != address:
                                peer_counter[p] = peer_counter.get(p, 0) + 1

            # --- RETI EVM (ETH, BSC, POLYGON, AVAX) ---
            elif ticker in ["ETH", "BSC", "POLYGON", "AVAX"]:
                domain_map = {
                    "ETH": "api.etherscan.io",
                    "BSC": "api.bscscan.com",
                    "POLYGON": "api.polygonscan.com",
                    "AVAX": "api.snowtrace.io"
                }
                explorer = domain_map[ticker]
                url_balance = f"https://{explorer}/api?module=account&action=balance&address={address}&tag=latest"
                r_bal = requests.get(url_balance, headers=headers, timeout=8)
                if r_bal.status_code == 200:
                    bal_data = r_bal.json()
                    if bal_data.get("status") == "1" or "result" in bal_data:
                        wei_balance = int(bal_data.get("result", 0))
                        balance = wei_balance / 10**18
                        info[f"Bilancio Attuale ({ticker})"] = f"{balance:.8f}"
                        if wei_balance:
                            graph_data.append({"t": "Balance", "y": wei_balance / 10**18})

                url_tx = f"https://{explorer}/api?module=account&action=txlist&address={address}&page=1&offset=100&sort=desc"
                r_tx = requests.get(url_tx, headers=headers, timeout=10)
                if r_tx.status_code == 200:
                    tx_data = r_tx.json()
                    if tx_data.get("status") == "1":
                        tx_list = tx_data.get("result", [])
                        tx_count = len(tx_list)
                        info["Transazioni Totali"] = str(tx_count)
                        for tx in tx_list:
                            ts = tx.get("timeStamp")
                            if ts:
                                timestamps.append(int(ts))
                            frm = (tx.get("from") or "").lower()
                            to = (tx.get("to") or "").lower()
                            if frm and frm != address.lower():
                                peer_counter[frm] = peer_counter.get(frm, 0) + 1
                            if to and to != address.lower():
                                peer_counter[to] = peer_counter.get(to, 0) + 1
                token_meta = self._evm_token_metadata(explorer, address)
                info.update(token_meta)
            
            # --- LITECOIN, DOGECOIN, DASH ---
            elif ticker in ["LTC", "DOGE", "DASH"]:
                r = requests.get(f"https://api.blockcypher.com/v1/{ticker.lower()}/main/addrs/{address}/full?limit=25", headers=headers, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    txs = data.get("txs") or []
                    tx_count = data.get("n_tx") if isinstance(data.get("n_tx"), int) else len(txs)
                    balance = (data.get("balance", 0) / 100_000_000) if data.get("balance") is not None else 0
                    total_recv = (data.get("total_received", 0) / 100_000_000) if data.get("total_received") is not None else 0
                    info[f"Bilancio Attuale ({ticker})"] = f"{balance:.8f}"
                    info[f"Totale Ricevuto ({ticker})"] = f"{total_recv:.8f}"
                    info["Transazioni Totali"] = str(tx_count or 0)
                    for tx in txs:
                        ts = tx.get("received")
                        if ts:
                            try:
                                ts_u = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                                timestamps.append(int(ts_u))
                            except Exception:
                                pass
                        for inp in tx.get("inputs", []) or []:
                            for p in (inp.get("addresses") or []):
                                if p and p != address:
                                    peer_counter[p] = peer_counter.get(p, 0) + 1
                        for out in tx.get("outputs", []) or []:
                            for p in (out.get("addresses") or []):
                                if p and p != address:
                                    peer_counter[p] = peer_counter.get(p, 0) + 1

            # --- TRON ---
            elif ticker == "TRX":
                r = requests.get(f"https://apilist.tronscanapi.com/api/accountv2?address={address}", headers=headers, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("balance") is not None:
                        balance = data.get("balance", 0) / 1_000_000
                        info[f"Bilancio Attuale ({ticker})"] = f"{balance:.6f}"
                    tx_count = data.get("transactions") if isinstance(data.get("transactions"), int) else data.get("totalTransactionCount")
                    if tx_count is not None:
                        info["Transazioni Totali"] = str(tx_count)
                    if data.get("date_created"):
                        info["Account creato"] = data.get("date_created")

            # --- SOLANA ---
            elif ticker == "SOL":
                rpc = "https://api.mainnet-beta.solana.com"
                r = requests.post(rpc, json={"jsonrpc":"2.0", "id":1, "method":"getBalance", "params":[address]}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if "result" in data and data["result"]:
                        balance = data["result"]["value"] / 1_000_000_000
                        info[f"Bilancio Attuale ({ticker})"] = f"{balance:.6f}"
                sig_payload = {"jsonrpc":"2.0", "id":2, "method":"getSignaturesForAddress", "params":[address, {"limit":80}]}
                r_sigs = requests.post(rpc, json=sig_payload, timeout=10)
                if r_sigs.status_code == 200:
                    sig_data = r_sigs.json()
                    txs = sig_data.get("result") or []
                    tx_count = len(txs) if isinstance(txs, list) else 0
                    info["Transazioni Totali"] = str(tx_count)
                    for tx in (txs or []):
                        bt = tx.get("blockTime")
                        if bt:
                            timestamps.append(int(bt))

            # --- XRP ---
            elif ticker == "XRP":
                rpc = "https://xrplcluster.com/"
                payload = {
                    "method": "account_info",
                    "params": [{"account": address, "ledger_index": "current", "strict": True}]
                }
                r_info = requests.post(rpc, json={"method":"account_info","params":[{"account": address, "ledger_index":"current", "strict":True}], "id": 1}, timeout=10)
                if r_info.status_code == 200:
                    ri = self._safe_response_json(r_info) or {}
                    ai = ri.get("result", {}).get("account_data", {})
                    if ai.get("Balance") is not None:
                        balance = int(ai.get("Balance", 0)) / 1_000_000
                        info[f"Bilancio Attuale ({ticker})"] = f"{balance:.6f}"
                tx_payload = {
                    "id": 2,
                    "jsonrpc": "2.0",
                    "method": "account_tx",
                    "params": [{
                        "account": address,
                        "binary": False,
                        "forward": False,
                        "limit": 80
                    }]
                }
                r_txs = requests.post(rpc, json=tx_payload, timeout=10)
                if r_txs.status_code == 200:
                    rt = self._safe_response_json(r_txs) or {}
                    tx_result = (rt.get("result") or {})
                    tx_count = tx_result.get("count")
                    tx_list = tx_result.get("transactions") or []
                    if tx_count is not None:
                        info["Transazioni Totali"] = str(tx_count)
                    for txrow in tx_list:
                        tx = txrow.get("tx", {}) or {}
                        ts = tx.get("date")
                        if ts is not None:
                            ux = self._ripple_to_unix(ts)
                            if ux:
                                timestamps.append(ux)
                        for field in ("Account", "Destination"):
                            peer = tx.get(field)
                            if peer and peer != address:
                                peer_counter[peer] = peer_counter.get(peer, 0) + 1
                        # Token/IOU activity fallback
                        amt = tx.get("Amount")
                        if isinstance(amt, dict):
                            ccy = amt.get("currency") or ""
                            if ccy and ccy not in peer_counter:
                                peer_counter[ccy] = peer_counter.get(ccy, 0) + 1

            _commit_tx_window()

            # --- Metadati aggregati di rete ---
            if peer_counter:
                info["Top Controparti"] = self._crypto_top_counterparties(peer_counter)
                info["Numero Controparti"] = str(len(peer_counter))
            if tx_count is not None:
                info["Rischio stimato"] = self._infer_crypto_risk(
                    int(tx_count),
                    [int(x) for x in timestamps if isinstance(x, (int, float))],
                    peer_counter,
                    ticker,
                    float(balance or 0)
                )
            if tx_count is not None:
                info["Transazioni Totali"] = str(tx_count)

        except Exception as e:
            # Se c' un errore di connessione, lo segnaliamo ma non facciamo crashare l'app
            info["Avviso"] = f"Impossibile leggere i dettagli avanzati: {str(e)}"

        return info, graph_data

    def get_crypto_graph(self, address):
        icon = CRYPTO_MAP["BTC"]["icon"]
        ticker = "BTC"
        
        for s, cm in CRYPTO_MAP.items():
            if re.match(cm['regex'], address):
                icon = cm['icon']
                ticker = s
                break
                
        short_address = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        nodes_dict = {address: {"id": address, "label": short_address, "image": icon, "size": 35}}
        edges = []
        in_nodes = set()
        out_nodes = set()
        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            
            # --- GRAFICO PER BITCOIN ---
            if ticker == "BTC":
                r = requests.get(f"https://mempool.space/api/address/{address}/txs", headers=headers, timeout=10)
                if r.status_code == 200:
                    for tx in r.json()[:15]: 
                        senders = [vin.get('prevout', {}).get('scriptpubkey_address') for vin in tx.get('vin', []) if vin.get('prevout')]
                        receivers = [vout.get('scriptpubkey_address') for vout in tx.get('vout', [])]

                        if address in senders: # USCITA
                            for peer in receivers:
                                if peer and peer != address:
                                    if peer not in nodes_dict: nodes_dict[peer] = {"id": peer, "label": f"{peer[:6]}...{peer[-4:]}", "image": icon, "size": 25}
                                    if peer not in out_nodes:
                                        edges.append({"from": address, "to": peer, "color": {"color": "#f43f5e"}, "arrows": "to"})
                                        out_nodes.add(peer)
                        else: # INGRESSO
                            for peer in senders:
                                if peer and peer != address:
                                    if peer not in nodes_dict: nodes_dict[peer] = {"id": peer, "label": f"{peer[:6]}...{peer[-4:]}", "image": icon, "size": 25}
                                    if peer not in in_nodes:
                                        edges.append({"from": peer, "to": address, "color": {"color": "#00e676"}, "arrows": "to"})
                                        in_nodes.add(peer)

            # --- GRAFICO PER RETI EVM (ETH, BSC, POLYGON, AVAX) ---
            elif ticker in ["ETH", "BSC", "POLYGON", "AVAX"]:
                domain_map = {"ETH": "api.etherscan.io", "BSC": "api.bscscan.com", "POLYGON": "api.polygonscan.com", "AVAX": "api.snowtrace.io"}
                url = f"https://{domain_map[ticker]}/api?module=account&action=txlist&address={address}&page=1&offset=15&sort=desc"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and r.json().get("status") == "1":
                    for tx in r.json().get("result", []):
                        frm = tx.get("from", "").lower()
                        to = tx.get("to", "").lower()
                        if not frm or not to: continue
                        
                        if frm == address.lower(): # USCITA
                            if to != address.lower():
                                if to not in nodes_dict: nodes_dict[to] = {"id": to, "label": f"{to[:6]}...{to[-4:]}", "image": icon, "size": 25}
                                if to not in out_nodes:
                                    edges.append({"from": address, "to": to, "color": {"color": "#f43f5e"}, "arrows": "to"})
                                    out_nodes.add(to)
                        else: # INGRESSO
                            if frm != address.lower():
                                if frm not in nodes_dict: nodes_dict[frm] = {"id": frm, "label": f"{frm[:6]}...{frm[-4:]}", "image": icon, "size": 25}
                                if frm not in in_nodes:
                                    edges.append({"from": frm, "to": address, "color": {"color": "#00e676"}, "arrows": "to"})
                                    in_nodes.add(frm)

            # --- GRAFICO PER LTC, DOGE, DASH ---
            elif ticker in ["LTC", "DOGE", "DASH"]:
                url = f"https://api.blockcypher.com/v1/{ticker.lower()}/main/addrs/{address}/full?limit=10"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    for tx in r.json().get("txs", []):
                        senders = [inp.get("addresses", [""])[0] for inp in tx.get("inputs", []) if inp.get("addresses")]
                        receivers = [out.get("addresses", [""])[0] for out in tx.get("outputs", []) if out.get("addresses")]
                        
                        if address in senders: # USCITA
                            for peer in receivers:
                                if peer and peer != address:
                                    if peer not in nodes_dict: nodes_dict[peer] = {"id": peer, "label": f"{peer[:6]}...{peer[-4:]}", "image": icon, "size": 25}
                                    if peer not in out_nodes:
                                        edges.append({"from": address, "to": peer, "color": {"color": "#f43f5e"}, "arrows": "to"})
                                        out_nodes.add(peer)
                        else: # INGRESSO
                            for peer in senders:
                                if peer and peer != address:
                                    if peer not in nodes_dict: nodes_dict[peer] = {"id": peer, "label": f"{peer[:6]}...{peer[-4:]}", "image": icon, "size": 25}
                                    if peer not in in_nodes:
                                        edges.append({"from": peer, "to": address, "color": {"color": "#00e676"}, "arrows": "to"})
                                        in_nodes.add(peer)

        except Exception as e: 
            print(f"[*] Errore durante la creazione del grafo: {e}")
            
        return {
            "nodes": list(nodes_dict.values())[:50], 
            "edges": edges[:100],
            "in_nodes": list(in_nodes),
            "out_nodes": list(out_nodes)
        }

    def _wmn_get_social_sites(self):
        if getattr(self, "_wmn_social_sites", None) is not None:
            return self._wmn_social_sites
        self._wmn_social_sites = []
        try:
            r = requests.get(WMN_DATA_URL, timeout=45)
            r.raise_for_status()
            data = r.json()
            self._wmn_social_sites = [
                s for s in data.get("sites", [])
                if s.get("cat") == "social" and s.get("uri_check") and s.get("e_string")
            ]
        except Exception as e:
            print(f"[*] WhatsMyName load error: {e}")
            self._wmn_social_sites = []
        return self._wmn_social_sites

    def _wmn_prepare_account(self, site, raw):
        acc = (raw or "").strip()
        if not acc:
            return ""
        strip = site.get("strip_bad_char")
        if strip:
            for c in strip:
                acc = acc.replace(c, "")
        return acc.strip()

    def _wmn_favicon_from_url(self, url):
        try:
            dom = urllib.parse.urlparse(url).netloc
            if not dom:
                return ""
            if dom.startswith("www."):
                dom = dom[4:]
            return f"https://www.google.com/s2/favicons?domain={dom}&sz=128"
        except Exception:
            return ""

    def _wmn_perform_request(self, site, account):
        acc = self._wmn_prepare_account(site, account)
        if not acc:
            return None
        check_url = site["uri_check"].replace("{account}", acc)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if site.get("headers"):
            headers.update(site["headers"])
        try:
            if site.get("post_body"):
                body = site["post_body"].replace("{account}", acc)
                ct = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
                if "application/json" in ct:
                    body_obj = json.loads(body)
                    return requests.post(check_url, json=body_obj, headers=headers, timeout=8, allow_redirects=True)
                return requests.post(check_url, data=body, headers=headers, timeout=8, allow_redirects=True)
            return requests.get(check_url, headers=headers, timeout=8, allow_redirects=True)
        except Exception:
            return None

    def _wmn_match_result(self, resp, site):
        if not resp:
            return None
        text = resp.text
        code = resp.status_code
        if code == site["e_code"] and site["e_string"] in text:
            return True
        mc = site.get("m_code")
        ms = site.get("m_string") or ""
        if mc is not None and code == mc:
            if not ms or ms in text:
                return False
        return None

    def _wmn_pretty_url(self, site, account):
        acc = self._wmn_prepare_account(site, account)
        if site.get("uri_pretty"):
            return site["uri_pretty"].replace("{account}", acc)
        return site["uri_check"].replace("{account}", acc)

    def whatsmyname_social_scan(self, account):
        wmn_fallback = SOCIAL_MAP.get("WhatsMyName (Social)", {}).get("icon", "")
        sites = self._wmn_get_social_sites()
        if not sites:
            return [{
                "username": account,
                "type": "WhatsMyName (Social)",
                "info": {
                    "Status": " Dataset non disponibile",
                    "Nota": "Impossibile scaricare wmn-data.json. Controlla la rete.",
                },
                "main_img": wmn_fallback,
                "status_code": 500,
                "url": WMN_DATA_URL,
            }]

        results = []

        def worker(site):
            r = self._wmn_perform_request(site, account)
            if self._wmn_match_result(r, site) is not True:
                return None
            pretty = self._wmn_pretty_url(site, account)
            src = site.get("uri_pretty") or site.get("uri_check")
            icon = self._wmn_favicon_from_url(src) or wmn_fallback
            name = site.get("name") or "Unknown"
            return {
                "username": account,
                "type": name,
                "info": {
                    "Status": " Profilo trovato (WhatsMyName)",
                    "Fonte": "WhatsMyName  social",
                    "HTTP": str(r.status_code) if r else "",
                },
                "main_img": icon,
                "status_code": 200,
                "url": pretty,
            }

        max_workers = min(32, max(4, len(sites) // 4 or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(worker, s) for s in sites]
            for fut in as_completed(futures):
                try:
                    row = fut.result()
                    if row:
                        results.append(row)
                except Exception:
                    pass

        results.sort(key=lambda x: (x.get("type") or "").lower())

        if not results:
            return [{
                "username": account,
                "type": "WhatsMyName (Social)",
                "info": {
                    "Status": "Nessun riscontro extra",
                    "Nota": f"Dataset WMN social: {len(sites)} siti testati, nessuna corrispondenza.",
                },
                "main_img": wmn_fallback,
                "status_code": 404,
                "url": "https://github.com/WebBreacher/WhatsMyName",
            }]
        return results

    def analyze_instagram(self, username):
        sid_raw = self.creds.get('sid', '')
        sid = str(sid_raw).encode('ascii', 'ignore').decode('ascii').strip()
        
        base_icon = SOCIAL_MAP["Instagram"]["icon"]
        url = f"https://instagram.com/{username}"
        
        info = {}
        img = base_icon
        uid = None
        
        def safe_str(val):
            if not val: return ""
            return str(val).replace('\n', ' | ').strip()

        api_success = False
        if sid:
            headers = {"User-Agent": "iphone_ua", "x-ig-app-id": "936619743392459"}
            cookies = {'sessionid': sid}
            try:
                res1 = requests.get(f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}', headers=headers, cookies=cookies, timeout=10)
                
                if res1.status_code == 404:
                    return [self._social_result("Instagram", username, {"Status": " Utente non trovato", "Profile": url}, base_icon, 404, url, False)]
                    
                if res1.status_code == 200:
                    try:
                        res1_data = res1.json()
                        user_data = res1_data.get("data", {}).get("user", {})
                        uid = user_data.get("id")
                        
                        if uid:
                            info["Status"] = " Online (API Instagram)"
                            info[" ID Numerico"] = str(uid)
                            if user_data.get("full_name"): info[" Nome"] = safe_str(user_data.get("full_name"))
                            if user_data.get("biography"): info[" Bio"] = safe_str(user_data.get("biography"))
                            if user_data.get("external_url"): info["Link in Bio"] = safe_str(user_data.get("external_url"))
                            info[" Followers"] = str(user_data.get("edge_followed_by", {}).get("count", 0))
                            info[" Following"] = str(user_data.get("edge_follow", {}).get("count", 0))
                            info[" Post"] = str(user_data.get("edge_owner_to_timeline_media", {}).get("count", 0))
                            if user_data.get("is_verified"): info["Verificato"] = "Sì"
                            if user_data.get("is_private"): info["Privato"] = "Sì"
                            if user_data.get("is_business_account"): info["Business"] = "Sì"
                            img = user_data.get("profile_pic_url_hd") or base_icon
                            
                            try:
                                res2 = requests.get(f'https://i.instagram.com/api/v1/users/{uid}/info/', headers={'User-Agent': 'Instagram 64.0.0.14.96'}, cookies=cookies, timeout=10)
                                if res2.status_code == 200:
                                    u_info = res2.json().get("user", {})
                                    if u_info.get("public_email"): info["Email Pubblica"] = safe_str(u_info.get("public_email"))
                                    if u_info.get("public_phone_number"): info["Tel Pubblico"] = f"+{u_info.get('public_phone_country_code','')} {u_info.get('public_phone_number')}"
                            except: pass
                            
                            api_success = True
                    except ValueError:
                        print("[*] IG API: Ricevuto HTML anzich JSON per i dati pubblici.")
            except Exception as e:
                print(f"[*] API Pubblica Fallita: {e}")

        if not api_success:
            info["Status"] = " Online (Via Playwright)"
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, args=["--log-level=3"])
                    page = browser.new_page()
                    page.set_extra_http_headers({"Accept-Language": "it-IT,it;q=0.9"})
                    response = page.goto(url, wait_until="domcontentloaded", timeout=15000)

                    if not response or not response.ok:
                        status_code = response.status if response else 500
                        info["Status"] = " Non Trovato"
                        info["Note"] = f"La pagina ha restituito un errore {status_code}."
                        return [self._social_result("Instagram", username, info, base_icon, status_code, url, False)]

                    html = page.content()
                    browser.close()

                soup = BeautifulSoup(html, 'html.parser')
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"): img = og_img['content']
                
                og_title = soup.find("meta", property="og:title")
                raw_title = og_title['content'] if og_title else ""
                clean_name = raw_title.split('(')[0].split('|')[0].strip() if raw_title else username
                
                info[" Nome"] = clean_name
                
                og_desc = soup.find("meta", property="og:description")
                raw_desc = og_desc['content'] if og_desc else ""
                
                stats = re.search(r'([\d,.]+[kmKM]?)\s*(?:Followers?|follower).*?([\d,.]+[kmKM]?)\s*(?:Following|seguiti).*?([\d,.]+[kmKM]?)\s*(?:Posts?|post)', raw_desc, re.IGNORECASE)
                
                if stats:
                    info[" Followers"] = stats.group(1)
                    info[" Seguiti"] = stats.group(2)
                    info[" Post"] = stats.group(3)
                
                clean_bio = re.split(r'-\s*Vedi le foto|-\s*See Instagram', raw_desc, flags=re.IGNORECASE)[0]
                if clean_bio and not stats:
                    info[" Bio"] = safe_str(clean_bio[:150]) + "..."
                elif clean_bio and stats and clean_bio != raw_desc:
                    info[" Bio"] = "N/A (Accedi per leggere)"
                
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        ig_data = json.loads(json_ld.string)
                        if isinstance(ig_data, list) and len(ig_data) > 0: 
                            ig_data = ig_data[0]
                        
                        ig_user = ig_data.get("mainEntityofPage", ig_data.get("author", ig_data))
                        
                        if ig_user.get("identifier"): 
                            uid = str(ig_user["identifier"])
                            info[" ID Numerico"] = uid
                        if ig_user.get("description"): 
                            info[" Bio"] = str(ig_user["description"]).replace('\n', ' | ')[:150]
                    except: 
                        pass
                
                if " ID Numerico" not in info:
                    m = re.search(r'profilePage_(\d+)', html) or re.search(r'"profile_id":"(\d+)"', html) or re.search(r'"user_id":"(\d+)"', html)
                    if m: 
                        uid = m.group(1)
                        info[" ID Numerico"] = uid
            except Exception as e:
                info["Status"] = " Richiede Login / Errore Render"

        if sid:
            try:
                guid = str(uuid.uuid4())
                device_id = f"android-{uuid.uuid4().hex[:16]}"
                payload = {"q": username, "device_id": device_id, "guid": guid, "_csrftoken": "missing"}
                json_p = json.dumps(payload, separators=(',', ':'))
                
                IG_KEY = "52491a62d7c0fb70bc1b9dbf8b030e4bbf6316fa7b12ec709dbca9c47e8bbec4"
                APP_ID_LOOKUP = "124024574287414"
                signed = hmac.new(IG_KEY.encode('utf-8'), json_p.encode('utf-8'), hashlib.sha256).hexdigest() + "." + json_p
                
                headers_post = {
                    "X-IG-App-ID": APP_ID_LOOKUP, 
                    "User-Agent": "Instagram 292.0.0.17.111 Android", 
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                res3 = requests.post(
                    'https://i.instagram.com/api/v1/users/lookup/', 
                    headers=headers_post, 
                    cookies={'sessionid': sid}, 
                    data={"signed_body": signed, "ig_sig_key_version": "4"}, 
                    timeout=10, 
                    allow_redirects=False
                )
                
                if res3.status_code == 200:
                    try:
                        res_json = res3.json()
                        lookup_data = res_json.get("user", {})
                        if not lookup_data and "obfuscated_email" in res_json:
                            lookup_data = res_json
                            
                        if lookup_data.get("obfuscated_email"): info["Email (Offuscata)"] = safe_str(lookup_data.get("obfuscated_email"))
                        if lookup_data.get("obfuscated_phone"): info["Tel (Offuscato)"] = safe_str(lookup_data.get("obfuscated_phone"))
                    except ValueError:
                        pass
            except Exception as e:
                print(f"[*] Dati Offuscati ignorati: {e}")

        return [self._social_result("Instagram", username, info, img, 200, url, info.get("Status") != " Non Trovato")]

    def enhanced_scraper(self, target, platform):
        target_clean = target.strip()
        target_norm = target_clean.strip()

        def _norm_for_lookup(s):
            # case-insensitive matching without losing original
            return (s or "").strip().lower()

        def _is_probable_handle_x(h):
            # X usernames are typically [A-Za-z0-9_], but we allow extra chars for "best effort"
            return bool(re.fullmatch(r"[A-Za-z0-9_]{1,32}", h or ""))
        
        def safe_str(val):
            if not val: return ""
            return str(val).replace('\n', ' | ').strip()
        
        if "t.me/" in target_clean or "telegram.me/" in target_clean:
            target_clean = target_clean.split('/')[-1].split('?')[0]
            platform = "Telegram"
        elif target_clean.startswith('@') or (target_clean.isdigit() and len(target_clean) > 5 and platform == "Telegram"):
            if target_clean.startswith('@'): target_clean = target_clean[1:]
            platform = "Telegram"
            
        if platform == "Telegram":
            return run_async(self.analyze_telegram(target_clean))

        if platform == "WhatsMyName (Social)":
            if "@" in target_clean or " " in target_clean:
                fb = SOCIAL_MAP.get("WhatsMyName (Social)", {}).get("icon", "")
                return [{
                    "username": target_clean,
                    "type": platform,
                    "info": {
                        "Status": " Input non valido",
                        "Nota": "WhatsMyName accetta un solo username (senza email o spazi).",
                    },
                    "main_img": fb,
                    "status_code": 400,
                    "url": "https://github.com/WebBreacher/WhatsMyName/blob/main/wmn-data.json",
                }]
            return self.whatsmyname_social_scan(target_clean)

        base = SOCIAL_MAP.get(platform, {"icon": "", "base": ""})
        encoded_path = urllib.parse.quote(target_clean, safe="@._-~")
        url = f"https://{base['base']}{encoded_path}"

        dedicated_social = {
            "GitHub": self.analyze_social_github,
            "Reddit": self.analyze_social_reddit,
            "YouTube": self.analyze_social_youtube,
            "LinkedIn": self.analyze_social_linkedin,
            "TikTok": self.analyze_social_tiktok,
            "Pinterest": self.analyze_social_pinterest,
            "Discord": self.analyze_social_discord,
            "Twitch": self.analyze_social_twitch,
            "Steam": self.analyze_social_steam,
            "Spotify": self.analyze_social_spotify,
            "SoundCloud": self.analyze_social_soundcloud
        }
        if platform in dedicated_social:
            dedicated_result = dedicated_social[platform](target_clean, base)
            if dedicated_result:
                return dedicated_result
            probe = self._social_playwright_probe(platform, target_clean, url, base.get("icon", ""))
            if probe:
                return probe
        
        if " " in target_clean:
            query = urllib.parse.quote_plus(target_clean)
            domain = base['base'].split('/')[0]
            
            results = []
            
            if platform == "GitHub":
                try:
                    search_api = f"https://api.github.com/search/users?q={query}&per_page=5"
                    r_api = requests.get(search_api, timeout=8)
                    if r_api.status_code == 200:
                        items = r_api.json().get('items', [])
                        for user in items:
                            results.append({
                                "username": user.get("login"),
                                "type": platform,
                                "info": {"Status": " Trovato (Ricerca Multipla)", "ID Numerico": str(user.get("id"))},
                                "main_img": user.get("avatar_url", base['icon']),
                                "status_code": 200,
                                "url": user.get("html_url")
                            })
                        if results: return results
                except Exception as e:
                    pass

            if platform == "Facebook":
                search_url = f"https://www.facebook.com/search/people/?q={query}"
            elif platform == "Twitter/X":
                search_url = f"https://x.com/search?q={query}&f=user"
            elif platform == "LinkedIn":
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={query}"
            elif platform == "TikTok":
                search_url = f"https://www.tiktok.com/search/user?q={query}"
            elif platform == "YouTube":
                search_url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAg%253D%253D"
            else:
                search_url = f"https://www.google.com/search?q=site:{domain}+%22{query}%22"
                
            info = {
                "Status": " Muro Anti-Bot (Ricerca Multipla)",
                "Nota": "Le piattaforme bloccano le ricerche massive. Usa 'APRI LINK' per vedere i risultati."
            }
            return [{"username": f"Ricerca: {target_clean}", "type": platform, "info": info, "main_img": base['icon'], "status_code": 200, "url": search_url}]

        info = {"Status": "Scansione in corso...", "Profile": url}
        img = base['icon']
        status_code = 200
        
        if platform == "Instagram":
            ig_api_result = self.analyze_instagram(target_clean)
            if ig_api_result:
                return ig_api_result

        # --- TWITTER/X: arricchimento via twiteridfinder.com ---
        if platform == "Twitter/X":
            try:
                # Il sito lavora su username (senza '@')
                tw_user = target_clean.lstrip('@')
                # se non sembra un handle valido, meglio usare la search di X
                if not _is_probable_handle_x(tw_user):
                    info["Nota"] = " Username con caratteri non standard: uso ricerca X (non profilo diretto)."
                    url = f"https://x.com/search?q={urllib.parse.quote_plus(target_clean)}&f=user"
                    info["Profile"] = url
                helper_url = f"https://twiteridfinder.com/?username={urllib.parse.quote(tw_user)}"
                r_tw = requests.get(helper_url, timeout=10)
                if r_tw.status_code == 200:
                    # parsing robusto: estraiamo testo "piatto" e facciamo regex
                    from bs4 import BeautifulSoup as _BS_TW
                    s2 = _BS_TW(r_tw.text, 'html.parser')
                    flat = s2.get_text("\n", strip=True)

                    def _pick(label, pat):
                        m = re.search(pat, flat, re.IGNORECASE | re.MULTILINE)
                        if m:
                            v = (m.group(1) or "").strip()
                            return v if v and v != "-" else ""
                        return ""

                    tw_info = {}
                    tw_info["STATUS"] = _pick("STATUS", r"STATUS\s*\n+(.+)")
                    tw_info["TWITTER ID"] = _pick("TWITTER ID", r"TWITTER ID\s*\n+([0-9]{3,})")
                    tw_info["TWITTER USERNAME"] = _pick("TWITTER USERNAME", r"TWITTER USERNAME\s*\n+@?([A-Za-z0-9_]{1,32})")
                    if tw_info.get("TWITTER USERNAME"):
                        tw_info["TWITTER USERNAME"] = f"@{tw_info['TWITTER USERNAME'].lstrip('@')}"
                    tw_info["TWITTER DESCRIPTION"] = _pick("TWITTER DESCRIPTION", r"TWITTER DESCRIPTION\s*\n+(.+)")
                    tw_info["TWITTER EMAIL"] = _pick("TWITTER EMAIL", r"TWITTER EMAIL\s*\n+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
                    tw_info["FOLLOWER COUNT"] = _pick("FOLLOWER COUNT", r"FOLLOWER COUNT\s*\n+(.+)")
                    tw_info["DATE CREATE"] = _pick("DATE CREATE", r"DATE CREATE\s*\n+(.+)")

                    # rimuovi vuoti
                    tw_info = {k: v for k, v in tw_info.items() if v}

                    if tw_info:
                        if tw_info.get("STATUS") and "live" in str(tw_info["STATUS"]).lower():
                            info["Status"] = " Account Live (Twitter ID Finder)"
                        info.update(tw_info)
            except Exception as e:
                info["TwitterIDFinder"] = f"Errore: {e}"
                
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--log-level=3", "--disable-blink-features=AutomationControlled"])
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                if platform == 'TikTok':
                    tiktok_sid = self.creds.get('tiktok_sid')
                    if tiktok_sid:
                        context.add_cookies([{"name": "sessionid", "value": tiktok_sid, "domain": ".tiktok.com", "path": "/"}])

                page = context.new_page()
                page.set_extra_http_headers({"Accept-Language": "it-IT,it;q=0.9"})
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # TikTok often returns 403 or captcha. We can tolerate some errors or wait slightly for TikTok.
                if platform == 'TikTok':
                    page.wait_for_timeout(3000)
                
                # Check for response.ok except for TikTok where 403 might just be a captcha but the title is still readable sometimes
                if not response or (not response.ok and platform != 'TikTok'):
                    status_code = response.status if response else 500
                    info["Status"] = " Non Trovato"
                    info["Note"] = f"La pagina ha restituito un errore {status_code}."
                    return [{"username": target_clean, "type": platform, "info": info, "main_img": img, "status_code": status_code, "url": url}]

                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            
            if ("Accedi a Facebook" in title_tag_text(soup) or "login" in page.url.lower()) and platform != "TikTok":
                info["Status"] = " Richiede Login (Protetto)"
                info["Note"] = "Il social nasconde il profilo. Usa 'APRI LINK'."
            else:
                info["Status"] = " Online (Via Playwright)"
                
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    img = og_img['content']
                    
            import re
            
            # Estrazione Dati Comuni (Meta Tags)
            og_title = soup.find("meta", property="og:title")
            raw_title = og_title['content'] if og_title else ""
            
            og_desc = soup.find("meta", property="og:description")
            raw_desc = og_desc['content'] if og_desc else ""
            
            # 1. FACEBOOK
            if platform == "Facebook":
                # Estrazione Nome (pulito dal suffisso di Facebook)
                clean_name = raw_title.split('|')[0].strip() if raw_title else target_clean
                if clean_name: info[" Nome"] = safe_str(clean_name)
                
                # Tenta di pescare "123 amici" dal blocco HTML
                amici_match = re.search(r'(\d+[\d,.]*)\s+amici', html, re.IGNORECASE)
                if amici_match: info[" Amici"] = safe_str(amici_match.group(1))

                # Tenta di pescare Lavoro / Istruzione
                lavoro_match = re.search(r'"work":\[{"employer":{"name":"([^"]+)"', html)
                if lavoro_match: info[" Lavoro"] = safe_str(lavoro_match.group(1))
                
                edu_match = re.search(r'"education":\[{"school":{"name":"([^"]+)"', html)
                if edu_match: info[" Istruzione"] = safe_str(edu_match.group(1))
                
                # Regex per l'ID Numerico (il Santo Graal di FB)
                m = re.search(r'fb://profile/(\d+)', html) or re.search(r'"(?:userID|entity_id|actorID)"\s*:\s*"(\d+)"', html) or re.search(r'"user":\{"id":"(\d+)"', html)
                if m: info[" ID Numerico"] = m.group(1)
                    
            # 2. TWITTER / X
            elif platform == "Twitter/X":
                clean_name = raw_title.split('(')[0].split('/')[0].strip() if raw_title else target_clean
                if clean_name: info[" Nome"] = safe_str(clean_name)
                
                user_match = re.search(r'\((@[A-Za-z0-9_\.]+)\)', raw_title)
                if user_match: info[" Username"] = safe_str(user_match.group(1))

                if raw_desc: info[" Bio"] = safe_str(raw_desc[:150]) + ("..." if len(raw_desc) > 150 else "")
                # estrazione email e URL pubblici dalla bio/descrizione
                combined_desc = " ".join([raw_desc or "", str(info.get("TWITTER DESCRIPTION",""))])
                email_matches = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', combined_desc)
                url_matches = re.findall(r'https?://[^\s)]+', combined_desc)
                if email_matches:
                    info[" Email (dal profilo)"] = ", ".join(sorted(set(email_matches)))
                if url_matches:
                    info[" Link (dal profilo)"] = " | ".join(sorted(set(url_matches))[:5])
                
                # Estrazione dati robusta dai JSON nascosti nella pagina di X
                loc_match = re.search(r'"location"\s*:\s*"([^"]+)"', html)
                if loc_match and loc_match.group(1): info[" Luogo"] = safe_str(loc_match.group(1))

                verified_match = re.search(r'"verified"\s*:\s*(true|false)', html)
                if verified_match: info[" Verificato"] = "Sì" if verified_match.group(1) == "true" else "No"

                bio_full_match = re.search(r'"description"\s*:\s*"([^"]+)"', html)
                if bio_full_match and bio_full_match.group(1):
                    bio_full = safe_str(bytes(bio_full_match.group(1), "utf-8").decode("unicode_escape"))
                    if bio_full and len(bio_full) > 0:
                        info[" Bio (full)"] = bio_full[:300] + ("..." if len(bio_full) > 300 else "")

                url_entity = re.search(r'"expanded_url"\s*:\s*"([^"]+)"', html)
                if url_entity and url_entity.group(1):
                    try:
                        expanded = safe_str(bytes(url_entity.group(1), "utf-8").decode("unicode_escape"))
                        if expanded:
                            info[" Sito/URL"] = expanded
                    except Exception:
                        pass
                
                created_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', html)
                if created_match: 
                    info[" Iscrizione"] = safe_str(created_match.group(1))
                    
                # 'friends_count' in Twitter corrisponde ai 'Following'
                following_match = re.search(r'"friends_count"\s*:\s*(\d+)', html)
                if following_match: info[" Following"] = following_match.group(1)
                
                followers_match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
                if followers_match: info[" Followers"] = followers_match.group(1)

                m = re.search(r'"identifier"\s*:\s*"(\d+)"', html) or re.search(r'"rest_id"\s*:\s*"(\d+)"', html)
                if m: info[" ID Numerico"] = m.group(1)

            # 3. THREADS
            elif platform == "Threads":
                clean_name = raw_title.split('(')[0].split('|')[0].strip() if raw_title else target_clean
                info[" Nome"] = safe_str(clean_name)
                
                stats = re.search(r'Followers?:\s*([\d,.]+[kmKM]?)\s*[\|\u00b7\-\u2013:\\s]*\s*Threads?:\s*([\d,.]+[kmKM]?)', raw_desc, re.IGNORECASE)
                if stats:
                    info[" Followers"] = stats.group(1)
                    info[" Threads"] = stats.group(2)
                else:
                    clean_bio = re.split(r'\.\s*Vedi le conversazioni|\.\s*See recent', raw_desc, flags=re.IGNORECASE)[0]
                    info[" Info"] = safe_str(clean_bio)

            # 4. TIKTOK
            elif platform == "TikTok":
                clean_name = raw_title.split('|')[0].strip() if raw_title else target_clean
                info[" Nome"] = safe_str(clean_name)
                
                stats = re.search(r'([\d,.]+[kmKM]?)\s*Followers?,\s*([\d,.]+[kmKM]?)\s*Following?,\s*([\d,.]+[kmKM]?)\s*Likes?', raw_desc, re.IGNORECASE)
                if stats:
                    info[" Followers"] = stats.group(1)
                    info[" Seguiti"] = stats.group(2)
                    info[" Likes"] = stats.group(3)
                else:
                    clean_bio = re.split(r'-\s*Watch', raw_desc, flags=re.IGNORECASE)[0]
                    info[" Bio"] = safe_str(clean_bio[:150]) + "..."
                    
                m = re.search(r'"user":\{"id":"(\d+)"', html) or re.search(r'"authorId":"(\d+)"', html)
                if m: info[" ID Numerico"] = m.group(1)

            # 5. YOUTUBE
            elif platform == "YouTube":
                clean_name = raw_title.split('-')[0].strip() if raw_title else target_clean
                if clean_name: info[" Canale"] = safe_str(clean_name)
                if raw_desc: info[" Descrizione"] = safe_str(raw_desc[:150]) + "..."
                sub_match = re.search(r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"', html)
                if sub_match: info[" Iscritti"] = safe_str(sub_match.group(1))

            # 6. LINKEDIN
            elif platform == "LinkedIn":
                clean_name = raw_title.split('|')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info[" Nome/Azienda"] = safe_str(clean_name)
                if raw_desc: info[" Sommario"] = safe_str(raw_desc[:150]) + "..."

            # 7. PINTEREST
            elif platform == "Pinterest":
                clean_name = raw_title.split('(')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info[" Nome"] = safe_str(clean_name)
                stats = re.search(r'-\s*([\d,.]+[kmKM]?)\s*followers?,\s*([\d,.]+[kmKM]?)\s*following', raw_desc, re.IGNORECASE)
                if stats:
                    info[" Followers"] = stats.group(1)
                    info[" Seguiti"] = stats.group(2)
                elif raw_desc:
                    info[" Info"] = safe_str(raw_desc[:150]) + "..."

            # 8. REDDIT
            elif platform == "Reddit":
                clean_name = raw_title.split('(')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info[" Utente"] = safe_str(clean_name)
                if raw_desc: info[" Bio"] = safe_str(raw_desc[:150]) + "..."
                karma_match = re.search(r'"totalKarma":(\d+)', html)
                if karma_match: info["Karma Totale"] = karma_match.group(1)

            # 9. FALLBACK GENERico per tutti gli altri (Twitch, PornHub, OnlyFans, Discord, ecc.)
            else:
                clean_name = raw_title.split('|')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info[" Nome Profilo"] = safe_str(clean_name)
                if raw_desc: info[" Info"] = safe_str(raw_desc[:150]) + "..."

        except Exception as e:
            info["Status"] = " Timeout/Errore"
            info["Note"] = "Il rendering della pagina ha fallito."
            
        return [{"username": target_clean, "type": platform, "info": info, "main_img": img, "status_code": status_code, "url": url}]

def title_tag_text(soup):
    title = soup.find('title')
    return title.text if title else ""

class ReportGenerator:
    def generate(self, data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "CSCORZA REPORT", ln=True, align="C")
        for d in data:
            pdf.ln(5)
            pdf.set_fill_color(240, 240, 240)
            
            sanitized_type = str(d.get('type', '')).encode('latin-1', 'ignore').decode('latin-1')
            sanitized_username = str(d.get('username', '')).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(0, 10, f"{sanitized_type}: {sanitized_username}", ln=True, fill=True)

            if d.get('info'):
                for k,v in d['info'].items():
                    sanitized_key = str(k).encode('latin-1', 'ignore').decode('latin-1')
                    sanitized_value = str(v).encode('latin-1', 'ignore').decode('latin-1')
                    pdf.cell(0, 8, f"- {sanitized_key}: {sanitized_value}", ln=True)
        return pdf.output()

core = OSINTCore()

@app.route('/')
def home(): return render_template_string(HTML_UI, creds=core.creds, social_map=SOCIAL_MAP, crypto_map=CRYPTO_MAP, logo_url=LOGO_URL, author_info=AUTHOR_INFO, donations=DONATIONS)

@app.route('/api/save_creds', methods=['POST'])
def api_save(): core.save_creds(request.json); return jsonify({"status":"ok"})

@app.route('/api/tg/send_code', methods=['POST'])
def tg_send(): d = request.json; s, m = run_async(core.tg_send_code(d['tg_id'], d['tg_hash'], d['phone'])); return jsonify({"status": s, "error": m})

@app.route('/api/tg/verify', methods=['POST'])
def tg_verify(): d = request.json; s, m = run_async(core.tg_verify_code(d['code'], core.creds.get('my_phone'))); return jsonify({"status": s, "error": m})

@app.route('/api/web_dork', methods=['POST'])
def api_web_dork():
    from bs4 import BeautifulSoup
    from playwright.sync_api import sync_playwright
    import urllib.parse
    
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({"results": []})
        
    results = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            
            # Iniezione cookie per bypassare il pop-up di consenso europeo di Google
            context.add_cookies([{"name": "CONSENT", "value": "YES+cb.20230501-14-p0.it+FX+874", "domain": ".google.com", "path": "/"}])
            page = context.new_page()
            
            # --- GOOGLE CSE ---
            try:
                page.goto(f"https://cse.google.com/cse?cx=d28c23ec014bd4cca&q={urllib.parse.quote(query)}", wait_until="domcontentloaded", timeout=15000)
                
                for _ in range(3):
                    try: page.wait_for_selector('.gsc-webResult', timeout=8000)
                    except: pass
                    
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    for res in soup.find_all('div', class_='gsc-webResult'):
                        a = res.find('a', class_='gs-title')
                        if a and a.get('href'):
                            title = a.text.strip()
                            url_node = a.get('data-ctorig') or a.get('href')
                            if url_node and url_node.startswith('http'):
                                snippet_div = res.find('div', class_='gs-snippet')
                                snippet = snippet_div.text.strip() if snippet_div else ""
                                if title:
                                    results.append({
                                        "engine": "Google",
                                        "title": title,
                                        "snippet": snippet,
                                        "url": url_node
                                    })
                    try:
                        has_next = page.evaluate('''() => {
                            let curr = document.querySelector('.gsc-cursor-current-page');
                            if(curr && curr.nextSibling) {
                                curr.nextSibling.click();
                                return true;
                            }
                            return false;
                        }''')
                        if has_next:
                            page.wait_for_timeout(2000)
                        else:
                            break
                    except:
                        break
            except Exception as e:
                print(f"Google CSE error: {e}")

            # --- YANDEX ---
            for p_num in range(3):
                try:
                    page.goto(f"https://yandex.com/search/?text={urllib.parse.quote(query)}&lang=en&p={p_num}", wait_until="domcontentloaded", timeout=15000)
                    try:
                        page.locator('button:has-text("Accept"), button:has-text("Accetta")').first.click(timeout=2000)
                    except: pass
                    
                    try: page.wait_for_selector('li.serp-item', timeout=3000)
                    except: pass
                    
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    added_any = False
                    for li in soup.find_all('li', class_='serp-item'):
                        a = li.find('a', class_=lambda c: c and 'Link' in c)
                        if a and a.get('href') and a.get('href').startswith('http'):
                            title = a.find('h2')
                            title_text = title.text.strip() if title else a.text.strip()
                            snippet_div = li.find('div', class_=lambda c: c and 'TextContainer' in c)
                            results.append({
                                "engine": "Yandex",
                                "title": title_text,
                                "snippet": snippet_div.text.strip() if snippet_div else "",
                                "url": a.get('href')
                            })
                            added_any = True
                    if not added_any:
                        break
                except Exception as e:
                    print(f"Yandex pw error on page {p_num}: {e}")
                    break

            browser.close()
    except Exception as e:
        print(f"Playwright error in web_dork: {e}")
                
    # Filter duplicates by URL
    seen_urls = set()
    unique_results = []
    for r in results:
        if r['url'] not in seen_urls:
            unique_results.append(r)
            seen_urls.add(r['url'])
            
    import random
    random.shuffle(unique_results)
    
    # Sort priority
    engine_priority = {'Google': 0, 'Yandex': 1}
    unique_results.sort(key=lambda x: engine_priority.get(x['engine'], 99))

    return jsonify({"results": unique_results})

@app.route('/api/search', methods=['POST'])
def search():
    d = request.json
    t = d.get('target', '').strip()
    p = d.get('platform')
    
    if p == 'holehe':
        return jsonify(core.holehe_scan(t))

    if p == 'messaging':
        img, info, tg_l, wa_l = run_async(core.analyze_phone(t))
        info['__tg_link'] = tg_l; info['__wa_link'] = wa_l
        base = {"username": t, "type": "Messaging", "info": info, "main_img": img, "status_code": 200, "url": ""}
        extra = []
        try:
            extra = core.ignorant_scan(t)
        except Exception:
            extra = []
        return jsonify([base] + (extra if isinstance(extra, list) else [extra]))
    elif p == 'gdrive':
        return jsonify([core.analyze_gdrive_doc(t)])
    elif p == 'finance':
        res = []
        try:
            for s, cm in CRYPTO_MAP.items():
                if re.match(cm['regex'], t):
                    c_info, c_graph = core.get_crypto_data(t, cm['name'], s)
                    res.append({"username": t, "type": cm['name'], "info": c_info, "main_img": cm['icon'], "status_code": 200, "url": cm['explorer']+t, "graph_data": c_graph})
            rev_i, rev_s = core.check_revolut(t)
            if rev_s == 200: res.append({"username": t, "type": "Revolut", "info": rev_i, "main_img": REV_ICON, "status_code": rev_s, "url": f"https://revolut.me/{t}"})
            pp_i, pp_u, pp_s = core.check_paypal(t)
            if pp_s == 200: res.append({"username": t, "type": "PayPal", "info": {"Status": pp_i}, "main_img": "https://cdn-icons-png.flaticon.com/512/174/174861.png", "status_code": pp_s, "url": pp_u})
        except Exception as e:
            print(f"[*] Errore Finance: {e}")
        return jsonify(res)
    elif p == 'domain':
        try:
            domain = core._domain_only(t)

            # 1) RISULTATO "CLASSICO" (come prima): WHOIS semplice
            w = whois.whois(domain)
            if hasattr(w, "items"):
                w_items = list(w.items())
            else:
                w_items = list(getattr(w, "__dict__", {}).items())
            whois_info = {str(k).capitalize(): str(v)[:200] for k, v in w_items if v}
            classic = {
                "username": domain,
                "type": "WHOIS",
                "info": whois_info,
                "main_img": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png",
                "status_code": 200,
                "url": ""
            }

            # 2) RISULTATO "IP MAP": DNS + servizi per IP + pulsante grafico nodi
            info = core.analyze_domain_advanced(domain)
            graph_data = []
            ips = []
            raw_v4 = info.get(" Indirizzi IPv4 (A)", "")
            raw_v6 = info.get(" Indirizzi IPv6 (AAAA)", "")
            if raw_v4 and raw_v4 != "Record non trovato":
                ips += [x.strip() for x in str(raw_v4).split(",") if x.strip()]
            if raw_v6 and raw_v6 != "Record non trovato":
                ips += [x.strip() for x in str(raw_v6).split(",") if x.strip()]
            ips = list(dict.fromkeys(ips))

            if ips:
                for ip in ips:
                    services, hostnames = core.scan_ip_services(ip)
                    if services:
                        info[f" Servizi su {ip}"] = ", ".join([f"{s['service']} ({s['port']})" for s in services])
                    else:
                        info[f" Servizi su {ip}"] = "Nessun servizio comune aperto"
                    if hostnames:
                        info[f" Reverse DNS {ip}"] = ", ".join(hostnames)
                    sh = core.shodan_host(ip)
                    if sh:
                        for k, v in sh.items():
                            info[f" Shodan {ip}  {k}"] = v
                    graph_data.append({"t": ip, "y": len(services)})

            ip_map = {
                "username": domain,
                "type": "DNS Analysis / IP Map",
                "info": info,
                "main_img": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png",
                "status_code": 200,
                "url": f"https://www.virustotal.com/gui/domain/{domain}",
                "graph_data": graph_data,
                "ip_graph_target": domain
            }

            return jsonify([classic, ip_map])
        except:
            return jsonify([{"status_code": 404}])
        
    results = core.enhanced_scraper(t, p)
    
    if not isinstance(results, list):
        results = [results]
        
    return jsonify(results)

@app.route('/api/crypto_graph', methods=['POST'])
def crypto_graph(): return jsonify(core.get_crypto_graph(request.json.get('address')))

@app.route('/api/ip_graph', methods=['POST'])
def ip_graph():
    d = request.json or {}
    domain = d.get('domain', '')
    return jsonify(core.build_ip_graph(domain))

@app.route('/api/ip_whois', methods=['POST'])
def ip_whois():
    d = request.json or {}
    ip = (d.get('ip') or "").strip()
    services, hostnames = core.scan_ip_services(ip) if ip else ([], [])
    rdap = core.ip_rdap_lookup(ip) if ip else {"Status": " IP mancante"}
    out = {"ip": ip, "rdap": rdap, "reverse_dns": hostnames, "services": services}
    return jsonify(out)

@app.route('/api/tg/export_participants', methods=['GET'])
def tg_export_csv():
    entity_id = request.args.get('entity')
    if not entity_id: return "Errore: ID mancante.", 400
    
    csv_data = run_async(core.get_tg_participants_csv(entity_id))
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=Telegram_Export_{entity_id}.csv"}
    )

@app.route('/api/export', methods=['POST'])
def export():
    pdf_bytes = ReportGenerator().generate(request.json.get('data', []))
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name="Report_CSCORZA.pdf")

if __name__ == '__main__':
    threading.Thread(target=lambda: (time.sleep(2), webbrowser.open(f"http://127.0.0.1:{PORT_NUMBER}/"))).start()
    app.run(port=PORT_NUMBER)


