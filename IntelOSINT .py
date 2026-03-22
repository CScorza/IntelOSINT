#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSCORZA IntelOSINT V.1
"""

import os, sys, subprocess, threading, webbrowser, time, base64, json, re, asyncio, io, random, socket, urllib.parse, csv, uuid, hmac, hashlib
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

# --- CONFIG ---
CREDS_FILE = "credenziali_api.json"
PORT_NUMBER = 5055
LOGO_URL = "https://github.com/CScorza.png"
REV_ICON = "https://static.vecteezy.com/system/resources/previews/067/065/684/non_2x/revolut-logo-rounded-icon-transparent-background-free-png.png"
DEFAULT_CREDS = {"sid": "", "tg_id": "", "tg_hash": "", "tg_session": "", "my_phone": "", "shodan_key": ""}

AUTHOR_INFO = [
    {"label": "Telegram", "val": "@CScorzaTg", "url": "https://t.me/CScorzaTg", "icon": "https://cdn-icons-png.flaticon.com/512/2111/2111646.png", "bg": "#229ED9"},
    {"label": "Website", "val": "cscorza.github.io", "url": "https://cscorza.github.io/CScorza", "icon": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png", "bg": "#3b82f6"},
    {"label": "X (Twitter)", "val": "@CScorzaOSINT", "url": "https://x.com/CScorzaOSINT", "icon": "https://cdn-icons-png.flaticon.com/512/5968/5968830.png", "bg": "#000000"},
    {"label": "GitHub", "val": "github.com/CScorza", "url": "https://github.com/CScorza", "icon": "https://cdn-icons-png.flaticon.com/512/25/25231.png", "bg": "#333333"},
    {"label": "Email", "val": "cscorzaosint@protonmail.com", "url": "mailto:cscorzaosint@protonmail.com", "icon": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "bg": "#8B5CF6", "copy": True}
]

DONATIONS = [{"curr": "BTC", "addr": "bc1qfn9kynt7k26eaxk4tc67q2hjuzhfcmutzq2q6a"}, {"curr": "TON", "addr": "UQBtLB6m-7q8j9Y81FeccBEjccvl34Ag5tWaUD"}]

SOCIAL_MAP = {
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
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
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
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        ::-webkit-scrollbar { width: 8px; } ::-webkit-scrollbar-track { background: #070a13; } ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        
        #login-view { position: fixed; inset: 0; z-index: 2000; display: flex; justify-content: center; align-items: center; }
        #globe-canvas { position: fixed; top: 0; right: 0; width: 50%; height: 100%; z-index: -1; filter: drop-shadow(-12px 0 40px rgba(0, 229, 255, 0.12)); }
        
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
        .auth-icon { width: 28px; height: 28px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5)); }
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
        
        #dashboard { display: none; width: 100%; height: 100%; }
        #sidebar { width: 300px; background: var(--panel); border-right: 1px solid #1e293b; display: flex; flex-direction: column; padding: 20px; }
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
        #main-area { flex: 1; display: flex; flex-direction: column; background: var(--bg); position: relative; overflow: hidden; }
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

        .top-nav { background: var(--panel); padding: 0 20px; height: 70px; display: flex; align-items: center; border-bottom: 1px solid #1e293b; }
        .header-logo-area { display: flex; align-items: center; gap: 15px; width: 250px; }
        .header-logo { width: 40px; border-radius: 50%; border: 2px solid var(--accent); }
        .header-title { font-weight: 800; font-size: 16px; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase; }
        .header-title span { color: white; }
        
        .nav-center { flex: 1; display: flex; justify-content: center; height: 100%; gap: 5px; }
        .nav-btn { background: transparent; border: none; color: #94a3b8; padding: 0 25px; height: 100%; cursor: pointer; font-weight: 700; font-size: 13px; border-bottom: 3px solid transparent; transition: 0.3s; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
        .nav-btn:hover { color: white; background: rgba(255,255,255,0.02); }
        .nav-btn.active { color: var(--accent); border-bottom-color: var(--accent); background: linear-gradient(180deg, rgba(0, 229, 255, 0.0) 0%, rgba(0, 229, 255, 0.1) 100%); }
        
        .tab-panel { display: none; padding: 25px; height: 100%; overflow-y: auto; transition: all 0.5s ease; }
        .tab-panel.active { display: flex; flex-direction: column; animation: slideIn 0.3s; }
        
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; background: var(--panel); padding: 15px 64px 15px 15px; border-radius: 12px; border: 1px solid #1e293b; position: relative; transition: all 0.5s ease; width: 100%; box-sizing: border-box; }
        .search-box.center-search { margin-top: 30vh; max-width: 600px; margin-left: auto; margin-right: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.6); transform: scale(1.1); }
        
        .main-input { flex: 1; background: var(--bg); border: 1px solid #1e293b; color: white; padding: 12px; border-radius: 8px; outline: none; font-size: 14px; }
        .loader-wrap { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); width: 52px; height: 52px; display: none; align-items: center; justify-content: center; pointer-events: none; }
        .loader-wrap svg { display: block; width: 48px; height: 48px; }
        .loader-ring-track { stroke: #1e293b; }
        .loader-ring-progress { stroke: var(--accent); transition: stroke-dashoffset 0.25s ease; filter: drop-shadow(0 0 4px rgba(0, 229, 255, 0.45)); }
        .loader-pct { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; color: var(--accent); letter-spacing: -0.5px; }
        
        .res-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 15px; padding-bottom: 40px; align-items: start; width: 100%; opacity: 0; transition: opacity 0.5s ease; }
        .res-grid.show { opacity: 1; }
        .res-grid.wide { max-width: 1200px; margin: 0 auto; grid-template-columns: minmax(720px, 1fr); }

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
    </style>
</head>
<body>
    <div id="overlay" onclick="closeAllCards()"></div>
    
    <img id="hover-zoom-img" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); max-width:85vw; max-height:85vh; z-index:9999; border-radius:15px; box-shadow: 0 0 0 100vmax rgba(0,0,0,0.85), 0 0 50px rgba(0,229,255,0.4); pointer-events:none; object-fit:contain;">
    
    <div id="graph-overlay">
        <div class="graph-nav">
            <div style="display: flex; flex-direction: column;">
                <div style="font-weight:bold; color:var(--accent);">🕸️ ANALISI VISUALE NETWORK</div>
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
                <div style="font-weight:bold; color:var(--accent);">🌐 IP NETWORK (DOMINIO → IP → SERVIZI)</div>
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
        <canvas id="globe-canvas"></canvas>
        <div class="login-card">
            <div class="login-form">
                <div class="section-title">🔑 Instagram Session</div>
                <input type="password" id="sid" class="login-input" value="{{creds.sid}}" placeholder="SessionID Cookie...">
                <div class="section-title" style="margin-top:20px; color:var(--secondary)">📱 Telegram Live</div>
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
                <div class="section-title" style="margin-top:20px; color:var(--success)">🔎 Shodan API</div>
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
                        <img src="{{c.icon}}" class="auth-icon">
                        <div class="auth-text">
                            <h4>{{c.label}}</h4>
                            <span style="color:white">{{c.val}}</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="donation-section">
                    <div class="donation-title">☕ Supporta il Progetto</div>
                    {% for d in donations %}
                    <div class="donation-card" onclick="copyText('{{d.addr}}')" title="Clicca per copiare l'indirizzo">
                        <div class="donation-info">
                            <span class="donation-curr">Donazione in {{d.curr}}</span>
                            <span class="donation-addr">{{d.addr}}</span>
                        </div>
                        <div class="donation-icon">📋</div>
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
            <button class="action-btn" onclick="location.reload()" style="background:#1e293b; color:white; width:100%; margin-bottom:10px;">🏠 HOME / LOGOUT</button>
            <button onclick="exportReport()" class="action-btn" style="width:100%; background:var(--success); color:#000;">📄 GENERA REPORT PDF</button>
        </div>
        <div id="main-area">
            <div class="top-nav">
                <div class="header-logo-area"><img src="{{logo_url}}" class="header-logo"><div class="header-title">CScorza <span style="color:var(--accent)">IntelOSINT</span></div></div>
                <div class="nav-center">
                    <button class="nav-btn active" onclick="setTab('social')">🌐 Social</button>
                    <button class="nav-btn" onclick="setTab('messaging')">📱 Phone</button>
                    <button class="nav-btn" onclick="setTab('finance')">💰 Financial</button>
                    <button class="nav-btn" onclick="setTab('domain')">🌍 Domain</button>
                </div>
                <div style="width:250px;"></div> 
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

        function setTab(name) {
            document.querySelectorAll('.tab-panel').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
            document.getElementById('tab-'+name).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        async function doLogin() {
            await fetch('/api/save_creds', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
                sid: document.getElementById('sid').value, tg_id: document.getElementById('tg_id').value,
                tg_hash: document.getElementById('tg_hash').value, my_phone: document.getElementById('phone').value,
                shodan_key: document.getElementById('shodan_key').value
            })});
            document.getElementById('login-view').style.display='none';
            document.getElementById('dashboard').style.display='flex';
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
                return { svc, state, meta: metaParts.join(' • ') };
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
            
            if (d.status_code !== 200 || (d.info && d.info.Status && d.info.Status.includes("❌"))) {
                dotColor = 's-red';
            } else {
                let hasId = d.info && (d.info["🆔 ID Numerico"] || d.info["ID Numerico"]);
                let hasName = d.info && (d.info["👤 Nome"] || d.info["👤 Nome Profilo"] || d.info["👤 Utente"] || d.info["👤 Canale"] || d.info["👤 Nome/Azienda"] || d.info["Nome"]);
                let isDefaultIcon = (socialIcons[d.type] && d.main_img === socialIcons[d.type].icon) || (d.main_img && d.main_img.includes('flaticon.com'));
                
                if (hasId || hasName || !isDefaultIcon) {
                    dotColor = 's-green';
                    highlightClass = 'highlight';
                }
                if (d.info && d.info.Status && d.info.Status.includes("⚠️")) dotColor = 's-yellow';
            }
            
            const inactiveClass = dotColor === 's-red' ? 'inactive' : '';
            const div = document.createElement('div'); div.className = `card ${inactiveClass} ${highlightClass}`;
            
            let rows = ''; for(let k in d.info) { if(!k.startsWith('__')) rows += `<div class="data-row"><label>${k}</label><span>${d.info[k]}</span></div>`; }
            
            let extra = '';
            if (d.graph_data && d.graph_data.length > 0) extra += `<canvas id="${uniqueId}"></canvas>`;
            
            let displayTitle = d.username;
            if (cryptoIconsMap[d.type] || d.type === 'Bitcoin' || d.type === 'Ethereum' || d.type === 'Binance SC' || d.type === 'Polygon' || d.type === 'Avalanche' || d.type === 'Litecoin' || d.type === 'Dogecoin' || d.type === 'Dash' || d.type === 'Tron' || d.type === 'Solana' || d.type === 'Ripple') {
                extra += `<button class="btn-link" onclick="openGraph('${d.username}')" style="background:var(--secondary); color:white;">ANALISI NETWORK 🕸️</button>`;
                if (displayTitle.length > 15) {
                    displayTitle = displayTitle.substring(0, 6) + "..." + displayTitle.substring(displayTitle.length - 4);
                }
            } else {
                displayTitle = displayTitle.substring(0,25);
            }
            
            if (d.type === 'Telegram' && d.info.Tipologia === 'Canale/Gruppo') extra += `<button class="btn-link" onclick="downloadCSV('${d.info['ID Numerico']}')" style="background:var(--accent); color:#000;">📥 SCARICA PARTECIPANTI (CSV)</button>`;
            if (d.ip_graph_target) extra += `<button class="btn-link" onclick="openIpGraph('${d.ip_graph_target}')" style="background:var(--secondary); color:white;">🌐 IP NETWORK</button>`;
            if (d.url) extra += `<a href="${d.url}" target="_blank" class="btn-link">APRI LINK ↗</a>`;
            extra += `<button type="button" class="btn-add-report">➕ REPORT</button>`;

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
                            <br><button class="tx-btn copy" style="margin-top:8px; width:100%; padding:8px;" onclick="copyText('${ip}')">📋 COPIA IP</button>
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
                html += `<div class="tx-list"><h4 style="color:var(--success);">🔌 SERVIZI (porte comuni)</h4>`;
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
            document.getElementById('graph-address-path').innerHTML += `<br>↳ Salto ${currentJumps}: <span style="color:var(--success)">${peerAddress}</span>`;
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
                                <br><button class="tx-btn copy" style="margin-top:8px; width:100%; padding:8px;" onclick="copyText('${address}')">📋 COPIA INDIRIZZO INTERO</button>
                            </div>`;
                            
                for(let k in d.info) { if(!k.startsWith('__')) html += `<div class="node-info-row"><label>${k}</label><span>${d.info[k]}</span></div>`; }

                if(graphData.in_nodes && graphData.in_nodes.length > 0) {
                    html += `<div class="tx-list"><h4 style="color:var(--success);">⬇️ TRANSAZIONI IN INGRESSO</h4>`;
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
                    html += `<div class="tx-list"><h4 style="color:var(--danger);">⬆️ TRANSAZIONI IN USCITA</h4>`;
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

function escapeAttr(s) {
            return escapeHtml(s).replace(/'/g, '&#39;');
        }

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
                list.innerHTML = '<div class="hist-empty">Nessun target nel report.<br>Usa <strong>➕ REPORT</strong> sulle card.</div>';
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
                const typeName = escapeHtml(String(entry.type || '—'));
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
                    '<button type="button" class="hist-remove" title="Rimuovi" aria-label="Rimuovi">×</button></div>';
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
        
        // --- GLOBE (nucleo + doppio wireframe, luci, stelle, rotazione veloce con delta-time) ---
        const globeCanvas = document.getElementById('globe-canvas');
        if (globeCanvas && typeof THREE !== 'undefined') {
            const scene = new THREE.Scene();
            const aspect = (window.innerWidth / 2) / window.innerHeight;
            const camera = new THREE.PerspectiveCamera(58, aspect, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({
                canvas: globeCanvas,
                alpha: true,
                antialias: true,
                powerPreference: 'high-performance'
            });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            renderer.setSize(window.innerWidth / 2, window.innerHeight);
            renderer.setClearColor(0x000000, 0);

            scene.add(new THREE.AmbientLight(0x4a5a78, 0.45));
            const keyLight = new THREE.PointLight(0x00e5ff, 1.6, 28);
            keyLight.position.set(5, 2, 6);
            scene.add(keyLight);
            const rim = new THREE.DirectionalLight(0x3b82f6, 0.5);
            rim.position.set(-5, 4, 3);
            scene.add(rim);

            const globe = new THREE.Group();
            const radius = 2.5;
            const segs = 56;
            const geo = new THREE.SphereGeometry(radius, segs, segs);

            const innerMat = new THREE.MeshPhongMaterial({
                color: 0x040810,
                emissive: 0x001520,
                emissiveIntensity: 0.55,
                shininess: 18,
                specular: 0x5599bb
            });
            globe.add(new THREE.Mesh(geo, innerMat));

            const wireMat = new THREE.MeshBasicMaterial({
                color: 0x00e5ff,
                wireframe: true,
                transparent: true,
                opacity: 0.88
            });
            globe.add(new THREE.Mesh(geo.clone(), wireMat));

            const wireOuter = new THREE.Mesh(
                new THREE.SphereGeometry(radius * 1.018, 28, 28),
                new THREE.MeshBasicMaterial({
                    color: 0x3b82f6,
                    wireframe: true,
                    transparent: true,
                    opacity: 0.22
                })
            );
            globe.add(wireOuter);

            scene.add(globe);

            const starN = 720;
            const starPos = new Float32Array(starN * 3);
            for (let i = 0; i < starN; i++) {
                const rad = 7 + Math.random() * 14;
                const u = Math.random();
                const v = Math.random();
                const th = u * Math.PI * 2;
                const ph = Math.acos(2 * v - 1);
                starPos[i * 3] = rad * Math.sin(ph) * Math.cos(th);
                starPos[i * 3 + 1] = rad * Math.sin(ph) * Math.sin(th);
                starPos[i * 3 + 2] = rad * Math.cos(ph);
            }
            const starGeo = new THREE.BufferGeometry();
            starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
            const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
                color: 0xaabbdd,
                size: 0.045,
                transparent: true,
                opacity: 0.55,
                sizeAttenuation: true,
                depthWrite: false
            }));
            scene.add(stars);

            camera.position.set(0, 0.15, 5.35);

            const clock = new THREE.Clock();
            const rotGlobeRadPerSec = 1.15;
            const rotStarsRadPerSec = 0.04;

            function animate() {
                requestAnimationFrame(animate);
                const dt = Math.min(clock.getDelta(), 0.05);
                globe.rotation.y += rotGlobeRadPerSec * dt;
                stars.rotation.y += rotStarsRadPerSec * dt;
                renderer.render(scene, camera);
            }

            animate();

            window.addEventListener('resize', () => {
                const w = window.innerWidth / 2;
                const h = window.innerHeight;
                renderer.setSize(w, h);
                camera.aspect = w / h;
                camera.updateProjectionMatrix();
            });
        }
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
# --- ANALISI DOMINIO AVANZATA (NSLOOKUP STYLE) ---
    def analyze_domain_advanced(self, target):
        domain = target.replace("https://", "").replace("http://", "").split('/')[0].strip()
        info = {"00. Dominio": domain, "Status": "✅ Analisi DNS Completa"}
        
        dns_tasks = {
            'A': '🌐 Indirizzi IPv4 (A)',
            'AAAA': '🌐 Indirizzi IPv6 (AAAA)',
            'MX': '📧 Server di Posta (MX)',
            'NS': '📛 Name Servers (NS)',
            'TXT': '📄 Record TXT (SPF/Verify)'
        }

        for record, label in dns_tasks.items():
            try:
                answers = dns.resolver.resolve(domain, record)
                if record == 'MX':
                    info[label] = ", ".join([f"{r.exchange} (prio:{r.preference})" for r in answers])
                else:
                    info[label] = ", ".join([str(r) for r in answers])
            except:
                info[label] = "Record non trovato"

        try:
            w = whois.whois(domain)
            if w.registrar: info["🏢 Registrar"] = str(w.registrar)
            if w.creation_date:
                c_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                info["📅 Registrato il"] = str(c_date)[:10]
        except:
            pass
        return info

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
                    out = {"Status": "✅ RDAP OK"}
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
        return {"Status": "⚠️ RDAP non disponibile"}

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
                return {"Status": f"⚠️ Shodan {r.status_code}"}
            j = r.json()
            out = {"Status": "✅ Shodan OK"}
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
            return {"Status": f"⚠️ Shodan error: {e}"}

    def build_ip_graph(self, domain):
        domain = self._domain_only(domain)
        info = self.analyze_domain_advanced(domain)
        ips = []
        ips_v4 = info.get("🌐 Indirizzi IPv4 (A)", "")
        ips_v6 = info.get("🌐 Indirizzi IPv6 (AAAA)", "")
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
            return [{"username": email, "type": "Holehe", "info": {"Status": "❌ Email non valida"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 400, "url": ""}]

        try:
            import trio
            import httpx
            import pkgutil
            import importlib
            import inspect
            import holehe.modules
        except Exception as e:
            return [{"username": email, "type": "Holehe", "info": {"Status": f"❌ Holehe non disponibile: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 500, "url": ""}]

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
            return [{"username": email, "type": "Holehe", "info": {"Status": f"❌ Errore esecuzione: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png", "status_code": 500, "url": ""}]

        # Mostra solo risultati positivi o rate-limited (per non spam)
        for r in (raw or []):
            try:
                name = r.get("name") or "unknown"
                exists = bool(r.get("exists"))
                rate = bool(r.get("rateLimit"))
                if not (exists or rate):
                    continue

                info = {"Status": "✅ Account trovato" if exists else "⚠️ Rate limit"}
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
                "info": {"Status": "❌ Nessuna corrispondenza (o moduli falliti)"},
                "main_img": "https://cdn-icons-png.flaticon.com/512/732/732200.png",
                "status_code": 404,
                "url": ""
            }]

        return results

    def ignorant_scan(self, phone_input):
        phone_input = (phone_input or "").strip()
        if not phone_input:
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": "❌ Numero mancante"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 400, "url": ""}]

        try:
            import trio
            import httpx
            import pkgutil
            import importlib
            import inspect
            import ignorant.modules
        except Exception as e:
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": f"❌ Ignorant non disponibile: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 500, "url": ""}]

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
            # default IT se non specificato (fallback “best effort”)
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
            return [{"username": phone_input, "type": "Ignorant", "info": {"Status": f"❌ Errore esecuzione: {e}"}, "main_img": "https://cdn-icons-png.flaticon.com/512/733/733585.png", "status_code": 500, "url": ""}]

        for r in (raw or []):
            try:
                name = r.get("name") or "unknown"
                exists = bool(r.get("exists"))
                rate = bool(r.get("rateLimit"))
                info = {"Status": "✅ Presente" if exists else ("⚠️ Rate limit" if rate else "❌ Non presente")}
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
                "info": {"Status": "❌ Nessuna corrispondenza (o moduli falliti)"},
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

                info["Status"] = "✅ Informazioni Trovate"
                status_code = 200
                if gaia_id: info["🆔 Gaia ID"] = gaia_id
                if name: info["👤 Nome"] = name
                if pfp_url: main_img = pfp_url
                
            else:
                info["Status"] = f"❌ Nessun risultato (Codice: {r.status_code})"

        except Exception as e:
            # This can happen if the endpoint changes, payload is wrong, or parsing fails.
            info["Status"] = "❌ Errore durante l'analisi"
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
                self.creds['tg_session'] = client.session.save(); self.save_creds(self.creds); await client.disconnect(); return "authorized", "Già Auth"
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
                "Status": "✅ Trovato (Match Esatto)" if exact else "✅ Trovato (Ricerca API)",
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
                "Status": "✅ Trovato (Match Esatto)" if exact else "✅ Trovato (Ricerca API)",
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
            info = {"Status": "⚠️ Accesso Negato", "Note": "Inserisci API ID/HASH Telegram e fai Login per la ricerca profonda."}
            return [{"username": query, "type": "Telegram", "info": info, "main_img": base_icon, "status_code": 401, "url": ""}]
            
        try:
            client = TelegramClient(StringSession(session_str), int(api_id), api_hash, loop=telethon_loop)
            await client.connect()
            if not await client.is_user_authorized():
                raise Exception("Sessione scaduta")
                
            # 1. Tentiamo prima il Match Esatto (Molto più preciso per trovare profili specifici)
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
                info = {"Status": "❌ Nessun Risultato", "Note": "La ricerca API non ha prodotto risultati."}
                return [{"username": query, "type": "Telegram", "info": info, "main_img": base_icon, "status_code": 404, "url": ""}]
                
            return results

        except Exception as e:
            print(f"[*] Errore API Telegram: {e}")
            info = {"Status": "❌ Errore API", "Note": str(e)}
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
    async def analyze_phone(self, target):
        info = {"00. Input": target}
        wa_link, tg_link = f"https://wa.me/{target.replace('+','')}", f"https://t.me/{target.replace('+','')}"
        main_img = "https://cdn-icons-png.flaticon.com/512/159/159832.png"
        try:
            pn = phonenumbers.parse(target)
            if phonenumbers.is_valid_number(pn):
                info["01. Region"] = geocoder.description_for_number(pn, "it")
                info["02. Carrier"] = carrier.name_for_number(pn, "it")
                info["03. Format"] = phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            else: info["Status"] = "Invalido"
        except: info["Error"] = "Parsing"
        
        info["04. WhatsApp"] = "Vedi Link"
        info["05. Telegram"] = "Checking..."

        if self.creds.get('tg_session'):
            try:
                client = TelegramClient(StringSession(self.creds['tg_session']), int(self.creds['tg_id']), self.creds['tg_hash'], loop=telethon_loop)
                await client.connect()
                try:
                    entity = await client.get_entity(target)
                    info["TG Name"] = f"{entity.first_name} {entity.last_name or ''}"
                    info["TG ID"] = str(entity.id)
                    info["05. Telegram"] = "✅ ATTIVO"
                    if entity.username: 
                        info["TG User"] = f"@{entity.username}"
                        tg_link = f"https://t.me/{entity.username}"
                    try: 
                        p = await client.download_profile_photo(entity, file=bytes)
                        if p: main_img = f"data:image/jpg;base64,{base64.b64encode(p).decode()}"
                    except: pass
                except: info["05. Telegram"] = "❌ Non Trovato/Privacy"
                
                try:
                    bot = "TrueCalleRobot"
                    await client.send_message(bot, target)
                    await asyncio.sleep(3)
                    msgs = await client.get_messages(bot, limit=1)
                    if msgs:
                        txt = msgs[0].message
                        if "Name" in txt or "Nome" in txt:
                            info["TrueCaller"] = "✅ FOUND"
                            lines = txt.split('\n')
                            for line in lines:
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    clean_k = k.strip().replace("*", "")
                                    clean_v = v.strip().replace("`", "")
                                    if len(clean_v) > 1 and "Limit" not in clean_k:
                                        info[f"TC_{clean_k}"] = clean_v
                except: pass
                await client.disconnect()
            except: info["TG Error"] = "Auth Fallita"
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
                return "✅ Attivo", f"https://www.paypal.com/paypalme/{target_clean}", 200
            return "❌ No", "", 404
        except Exception as e:
            print(f"[*] Errore PayPal: {e}")
            return "⚠️ Err", "", 404

    def get_crypto_data(self, address, name, ticker):
        """
        Recupera le informazioni di base (bilancio, transazioni) di un wallet crypto.
        """
        info = {
            "Status": "✅ Trovato",
            "Indirizzo": address,
            "Rete": name
        }
        graph_data = [] # Qui potremmo inserire lo storico del bilancio se supportato dall'API

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            # --- BITCOIN ---
            if ticker == "BTC":
                r = requests.get(f"https://mempool.space/api/address/{address}", headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    stats = data.get("chain_stats", {})
                    funded = stats.get("funded_txo_sum", 0) / 100_000_000
                    spent = stats.get("spent_txo_sum", 0) / 100_000_000
                    info[f"Bilancio Attuale ({ticker})"] = f"{funded - spent:.8f}"
                    info[f"Totale Ricevuto ({ticker})"] = f"{funded:.8f}"
                    info["Transazioni Totali"] = str(stats.get("tx_count", 0))
            
            # --- RETI EVM (ETH, BSC, POLYGON, AVAX) ---
            elif ticker in ["ETH", "BSC", "POLYGON", "AVAX"]:
                domain_map = {"ETH": "api.etherscan.io", "BSC": "api.bscscan.com", "POLYGON": "api.polygonscan.com", "AVAX": "api.snowtrace.io"}
                
                # Ottieni bilancio tramite API gratuita (senza key)
                url_balance = f"https://{domain_map[ticker]}/api?module=account&action=balance&address={address}&tag=latest"
                r_bal = requests.get(url_balance, headers=headers, timeout=5)
                if r_bal.status_code == 200:
                    bal_data = r_bal.json()
                    if bal_data.get("status") == "1" or "result" in bal_data:
                        wei_balance = int(bal_data.get("result", 0))
                        info[f"Bilancio Attuale ({ticker})"] = f"{wei_balance / 10**18:.8f}"
                
                # Ottieni numero transazioni
                url_tx = f"https://{domain_map[ticker]}/api?module=proxy&action=eth_getTransactionCount&address={address}&tag=latest"
                r_tx = requests.get(url_tx, headers=headers, timeout=5)
                if r_tx.status_code == 200:
                    tx_data = r_tx.json()
                    if tx_data.get("result"):
                        info["Transazioni Totali"] = str(int(tx_data["result"], 16))
            
            # --- LITECOIN, DOGECOIN, DASH ---
            elif ticker in ["LTC", "DOGE", "DASH"]:
                r = requests.get(f"https://api.blockcypher.com/v1/{ticker.lower()}/main/addrs/{address}/balance", headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    balance = data.get("balance", 0) / 100_000_000
                    total_recv = data.get("total_received", 0) / 100_000_000
                    info[f"Bilancio Attuale ({ticker})"] = f"{balance:.8f}"
                    info[f"Totale Ricevuto ({ticker})"] = f"{total_recv:.8f}"
                    info["Transazioni Totali"] = str(data.get("n_tx", 0))
            
            # --- TRON ---
            elif ticker == "TRX":
                r = requests.get(f"https://apilist.tronscanapi.com/api/accountv2?address={address}", headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    balance = data.get("balance", 0) / 1_000_000
                    info[f"Bilancio Attuale ({ticker})"] = f"{balance:.6f}"
                    info["Transazioni Totali"] = str(data.get("totalTransactionCount", 0))
                    
            # --- SOLANA ---
            elif ticker == "SOL":
                payload = {"jsonrpc":"2.0", "id":1, "method":"getBalance", "params":[address]}
                r = requests.post("https://api.mainnet-beta.solana.com", json=payload, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if "result" in data:
                        balance = data["result"]["value"] / 1_000_000_000
                        info[f"Bilancio Attuale ({ticker})"] = f"{balance:.6f}"

        except Exception as e:
            # Se c'è un errore di connessione, lo segnaliamo ma non facciamo crashare l'app
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
                    "Status": "❌ Dataset non disponibile",
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
                    "Status": "✅ Profilo trovato (WhatsMyName)",
                    "Fonte": "WhatsMyName · social",
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
                    "Status": "ℹ️ Nessun riscontro extra",
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
                    return [{"username": username, "type": "Instagram", "info": {"Status": "❌ Utente non trovato"}, "main_img": base_icon, "status_code": 404, "url": url}]
                    
                if res1.status_code == 200:
                    try:
                        res1_data = res1.json()
                        user_data = res1_data.get("data", {}).get("user", {})
                        uid = user_data.get("id")
                        
                        if uid:
                            info["Status"] = "✅ Online (API Instagram)"
                            info["🆔 ID Numerico"] = str(uid)
                            if user_data.get("full_name"): info["👤 Nome"] = safe_str(user_data.get("full_name"))
                            if user_data.get("biography"): info["📝 Bio"] = safe_str(user_data.get("biography"))
                            if user_data.get("external_url"): info["Link in Bio"] = safe_str(user_data.get("external_url"))
                            info["👥 Followers"] = str(user_data.get("edge_followed_by", {}).get("count", 0))
                            info["👣 Following"] = str(user_data.get("edge_follow", {}).get("count", 0))
                            info["📸 Post"] = str(user_data.get("edge_owner_to_timeline_media", {}).get("count", 0))
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
                        print("[*] IG API: Ricevuto HTML anziché JSON per i dati pubblici.")
            except Exception as e:
                print(f"[*] API Pubblica Fallita: {e}")

        if not api_success:
            info["Status"] = "✅ Online (Via Playwright)"
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_extra_http_headers({"Accept-Language": "it-IT,it;q=0.9"})
                    response = page.goto(url, wait_until="domcontentloaded", timeout=15000)

                    if not response or not response.ok:
                        status_code = response.status if response else 500
                        info["Status"] = "❌ Non Trovato"
                        info["Note"] = f"La pagina ha restituito un errore {status_code}."
                        return [{"username": username, "type": "Instagram", "info": info, "main_img": base_icon, "status_code": status_code, "url": url}]

                    html = page.content()
                    browser.close()

                soup = BeautifulSoup(html, 'html.parser')
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"): img = og_img['content']
                
                og_title = soup.find("meta", property="og:title")
                raw_title = og_title['content'] if og_title else ""
                clean_name = raw_title.split('(')[0].split('•')[0].strip() if raw_title else username
                
                info["👤 Nome"] = clean_name
                
                og_desc = soup.find("meta", property="og:description")
                raw_desc = og_desc['content'] if og_desc else ""
                
                stats = re.search(r'([\d,.]+[kmKM]?)\s*(?:Followers?|follower).*?([\d,.]+[kmKM]?)\s*(?:Following|seguiti).*?([\d,.]+[kmKM]?)\s*(?:Posts?|post)', raw_desc, re.IGNORECASE)
                
                if stats:
                    info["👥 Followers"] = stats.group(1)
                    info["👣 Seguiti"] = stats.group(2)
                    info["📸 Post"] = stats.group(3)
                
                clean_bio = re.split(r'-\s*Vedi le foto|-\s*See Instagram', raw_desc, flags=re.IGNORECASE)[0]
                if clean_bio and not stats:
                    info["📝 Bio"] = safe_str(clean_bio[:150]) + "..."
                elif clean_bio and stats and clean_bio != raw_desc:
                    info["📝 Bio"] = "N/A (Accedi per leggere)"
                
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        ig_data = json.loads(json_ld.string)
                        if isinstance(ig_data, list) and len(ig_data) > 0: 
                            ig_data = ig_data[0]
                        
                        ig_user = ig_data.get("mainEntityofPage", ig_data.get("author", ig_data))
                        
                        if ig_user.get("identifier"): 
                            uid = str(ig_user["identifier"])
                            info["🆔 ID Numerico"] = uid
                        if ig_user.get("description"): 
                            info["📝 Bio"] = str(ig_user["description"]).replace('\n', ' | ')[:150]
                    except: 
                        pass
                
                if "🆔 ID Numerico" not in info:
                    m = re.search(r'profilePage_(\d+)', html) or re.search(r'"profile_id":"(\d+)"', html) or re.search(r'"user_id":"(\d+)"', html)
                    if m: 
                        uid = m.group(1)
                        info["🆔 ID Numerico"] = uid
            except Exception as e:
                info["Status"] = "⚠️ Richiede Login / Errore Render"

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

        return [{"username": username, "type": "Instagram", "info": info, "main_img": img, "status_code": 200, "url": url}]

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
                        "Status": "⚠️ Input non valido",
                        "Nota": "WhatsMyName accetta un solo username (senza email o spazi).",
                    },
                    "main_img": fb,
                    "status_code": 400,
                    "url": "https://github.com/WebBreacher/WhatsMyName/blob/main/wmn-data.json",
                }]
            return self.whatsmyname_social_scan(target_clean)

        base = SOCIAL_MAP.get(platform, {"icon": "", "base": ""})
        
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
                                "info": {"Status": "✅ Trovato (Ricerca Multipla)", "ID Numerico": str(user.get("id"))},
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
                "Status": "⚠️ Muro Anti-Bot (Ricerca Multipla)",
                "Nota": "Le piattaforme bloccano le ricerche massive. Usa 'APRI LINK' per vedere i risultati."
            }
            return [{"username": f"Ricerca: {target_clean}", "type": platform, "info": info, "main_img": base['icon'], "status_code": 200, "url": search_url}]

        # For profile URLs, encode path safely (handles special chars)
        encoded_path = urllib.parse.quote(target_clean, safe="@._-~")
        url = f"https://{base['base']}{encoded_path}"
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
                    info["Nota"] = "⚠️ Username con caratteri non standard: uso ricerca X (non profilo diretto)."
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
                            info["Status"] = "✅ Account Live (Twitter ID Finder)"
                        info.update(tw_info)
            except Exception as e:
                info["TwitterIDFinder"] = f"Errore: {e}"
                
        if platform == "GitHub":
            try:
                api_url = f"https://api.github.com/users/{target_clean}"
                r_api = requests.get(api_url, timeout=8)
                if r_api.status_code == 200:
                    d = r_api.json()
                    img = d.get("avatar_url", base['icon'])
                    info["Status"] = "✅ Online (API GitHub)"
                    
                    if d.get("name"): info["Nome"] = d.get("name")
                    if d.get("bio"): info["Bio"] = str(d.get("bio")).replace('\n', ' ')
                    if d.get("location"): info["Location"] = d.get("location")
                    if d.get("company"): info["Company"] = d.get("company")
                    
                    info["Followers"] = str(d.get("followers", 0))
                    info["Following"] = str(d.get("following", 0))
                    info["Repo Pubbliche"] = str(d.get("public_repos", 0))
                    
                    if d.get("twitter_username"): info["X (Twitter)"] = d.get("twitter_username")
                    if d.get("created_at"): info["Iscritto il"] = d.get("created_at")[:10]
                    
                    return [{"username": target_clean, "type": platform, "info": info, "main_img": img, "status_code": 200, "url": url}]
                elif r_api.status_code == 404:
                    info["Status"] = "❌ Non Trovato"
                    return [{"username": target_clean, "type": platform, "info": info, "main_img": img, "status_code": 404, "url": url}]
            except Exception as e:
                pass
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"Accept-Language": "it-IT,it;q=0.9"})
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)

                if not response or not response.ok:
                    status_code = response.status if response else 500
                    info["Status"] = "❌ Non Trovato"
                    info["Note"] = f"La pagina ha restituito un errore {status_code}."
                    return [{"username": target_clean, "type": platform, "info": info, "main_img": img, "status_code": status_code, "url": url}]

                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            
            if "Accedi a Facebook" in title_tag_text(soup) or "login" in page.url.lower():
                info["Status"] = "⚠️ Richiede Login (Protetto)"
                info["Note"] = "Il social nasconde il profilo. Usa 'APRI LINK'."
            else:
                info["Status"] = "✅ Online (Via Playwright)"
                
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
                if clean_name: info["👤 Nome"] = safe_str(clean_name)
                
                # Tenta di pescare "123 amici" dal blocco HTML
                amici_match = re.search(r'(\d+[\d,.]*)\s+amici', html, re.IGNORECASE)
                if amici_match: info["👥 Amici"] = safe_str(amici_match.group(1))

                # Tenta di pescare Lavoro / Istruzione
                lavoro_match = re.search(r'"work":\[{"employer":{"name":"([^"]+)"', html)
                if lavoro_match: info["💼 Lavoro"] = safe_str(lavoro_match.group(1))
                
                edu_match = re.search(r'"education":\[{"school":{"name":"([^"]+)"', html)
                if edu_match: info["🎓 Istruzione"] = safe_str(edu_match.group(1))
                
                # Regex per l'ID Numerico (il Santo Graal di FB)
                m = re.search(r'fb://profile/(\d+)', html) or re.search(r'"(?:userID|entity_id|actorID)"\s*:\s*"(\d+)"', html) or re.search(r'"user":\{"id":"(\d+)"', html)
                if m: info["🆔 ID Numerico"] = m.group(1)
                    
            # 2. TWITTER / X
            elif platform == "Twitter/X":
                clean_name = raw_title.split('(')[0].split('/')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Nome"] = safe_str(clean_name)
                
                user_match = re.search(r'\((@[A-Za-z0-9_\.]+)\)', raw_title)
                if user_match: info["🔗 Username"] = safe_str(user_match.group(1))

                if raw_desc: info["📝 Bio"] = safe_str(raw_desc[:150]) + ("..." if len(raw_desc) > 150 else "")
                # estrazione email e URL pubblici dalla bio/descrizione
                combined_desc = " ".join([raw_desc or "", str(info.get("TWITTER DESCRIPTION",""))])
                email_matches = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', combined_desc)
                url_matches = re.findall(r'https?://[^\s)]+', combined_desc)
                if email_matches:
                    info["📧 Email (dal profilo)"] = ", ".join(sorted(set(email_matches)))
                if url_matches:
                    info["🔗 Link (dal profilo)"] = " | ".join(sorted(set(url_matches))[:5])
                
                # Estrazione dati robusta dai JSON nascosti nella pagina di X
                loc_match = re.search(r'"location"\s*:\s*"([^"]+)"', html)
                if loc_match and loc_match.group(1): info["📍 Luogo"] = safe_str(loc_match.group(1))

                verified_match = re.search(r'"verified"\s*:\s*(true|false)', html)
                if verified_match: info["✅ Verificato"] = "Sì" if verified_match.group(1) == "true" else "No"

                bio_full_match = re.search(r'"description"\s*:\s*"([^"]+)"', html)
                if bio_full_match and bio_full_match.group(1):
                    bio_full = safe_str(bytes(bio_full_match.group(1), "utf-8").decode("unicode_escape"))
                    if bio_full and len(bio_full) > 0:
                        info["📝 Bio (full)"] = bio_full[:300] + ("..." if len(bio_full) > 300 else "")

                url_entity = re.search(r'"expanded_url"\s*:\s*"([^"]+)"', html)
                if url_entity and url_entity.group(1):
                    try:
                        expanded = safe_str(bytes(url_entity.group(1), "utf-8").decode("unicode_escape"))
                        if expanded:
                            info["🌐 Sito/URL"] = expanded
                    except Exception:
                        pass
                
                created_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', html)
                if created_match: 
                    info["📅 Iscrizione"] = safe_str(created_match.group(1))
                    
                # 'friends_count' in Twitter corrisponde ai 'Following'
                following_match = re.search(r'"friends_count"\s*:\s*(\d+)', html)
                if following_match: info["👣 Following"] = following_match.group(1)
                
                followers_match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
                if followers_match: info["👥 Followers"] = followers_match.group(1)

                m = re.search(r'"identifier"\s*:\s*"(\d+)"', html) or re.search(r'"rest_id"\s*:\s*"(\d+)"', html)
                if m: info["🆔 ID Numerico"] = m.group(1)

            # 3. THREADS
            elif platform == "Threads":
                clean_name = raw_title.split('(')[0].split('•')[0].strip() if raw_title else target_clean
                info["👤 Nome"] = safe_str(clean_name)
                
                stats = re.search(r'Followers?:\s*([\d,.]+[kmKM]?)\s*•\s*Threads?:\s*([\d,.]+[kmKM]?)', raw_desc, re.IGNORECASE)
                if stats:
                    info["👥 Followers"] = stats.group(1)
                    info["🧵 Threads"] = stats.group(2)
                else:
                    clean_bio = re.split(r'\.\s*Vedi le conversazioni|\.\s*See recent', raw_desc, flags=re.IGNORECASE)[0]
                    info["📝 Info"] = safe_str(clean_bio)

            # 4. TIKTOK
            elif platform == "TikTok":
                clean_name = raw_title.split('|')[0].strip() if raw_title else target_clean
                info["👤 Nome"] = safe_str(clean_name)
                
                stats = re.search(r'([\d,.]+[kmKM]?)\s*Followers?,\s*([\d,.]+[kmKM]?)\s*Following?,\s*([\d,.]+[kmKM]?)\s*Likes?', raw_desc, re.IGNORECASE)
                if stats:
                    info["👥 Followers"] = stats.group(1)
                    info["👣 Seguiti"] = stats.group(2)
                    info["❤️ Likes"] = stats.group(3)
                else:
                    clean_bio = re.split(r'-\s*Watch', raw_desc, flags=re.IGNORECASE)[0]
                    info["📝 Bio"] = safe_str(clean_bio[:150]) + "..."
                    
                m = re.search(r'"user":\{"id":"(\d+)"', html) or re.search(r'"authorId":"(\d+)"', html)
                if m: info["🆔 ID Numerico"] = m.group(1)

            # 5. YOUTUBE
            elif platform == "YouTube":
                clean_name = raw_title.split('-')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Canale"] = safe_str(clean_name)
                if raw_desc: info["📝 Descrizione"] = safe_str(raw_desc[:150]) + "..."
                sub_match = re.search(r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"', html)
                if sub_match: info["👥 Iscritti"] = safe_str(sub_match.group(1))

            # 6. LINKEDIN
            elif platform == "LinkedIn":
                clean_name = raw_title.split('|')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Nome/Azienda"] = safe_str(clean_name)
                if raw_desc: info["💼 Sommario"] = safe_str(raw_desc[:150]) + "..."

            # 7. PINTEREST
            elif platform == "Pinterest":
                clean_name = raw_title.split('(')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Nome"] = safe_str(clean_name)
                stats = re.search(r'-\s*([\d,.]+[kmKM]?)\s*followers?,\s*([\d,.]+[kmKM]?)\s*following', raw_desc, re.IGNORECASE)
                if stats:
                    info["👥 Followers"] = stats.group(1)
                    info["👣 Seguiti"] = stats.group(2)
                elif raw_desc:
                    info["📝 Info"] = safe_str(raw_desc[:150]) + "..."

            # 8. REDDIT
            elif platform == "Reddit":
                clean_name = raw_title.split('(')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Utente"] = safe_str(clean_name)
                if raw_desc: info["📝 Bio"] = safe_str(raw_desc[:150]) + "..."
                karma_match = re.search(r'"totalKarma":(\d+)', html)
                if karma_match: info["⭐ Karma Totale"] = karma_match.group(1)

            # 9. FALLBACK GENERico per tutti gli altri (Twitch, PornHub, OnlyFans, Discord, ecc.)
            else:
                clean_name = raw_title.split('|')[0].split('-')[0].strip() if raw_title else target_clean
                if clean_name: info["👤 Nome Profilo"] = safe_str(clean_name)
                if raw_desc: info["📝 Info"] = safe_str(raw_desc[:150]) + "..."

        except Exception as e:
            info["Status"] = "❌ Timeout/Errore"
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
            raw_v4 = info.get("🌐 Indirizzi IPv4 (A)", "")
            raw_v6 = info.get("🌐 Indirizzi IPv6 (AAAA)", "")
            if raw_v4 and raw_v4 != "Record non trovato":
                ips += [x.strip() for x in str(raw_v4).split(",") if x.strip()]
            if raw_v6 and raw_v6 != "Record non trovato":
                ips += [x.strip() for x in str(raw_v6).split(",") if x.strip()]
            ips = list(dict.fromkeys(ips))

            if ips:
                for ip in ips:
                    services, hostnames = core.scan_ip_services(ip)
                    if services:
                        info[f"🔌 Servizi su {ip}"] = ", ".join([f"{s['service']} ({s['port']})" for s in services])
                    else:
                        info[f"🔌 Servizi su {ip}"] = "Nessun servizio comune aperto"
                    if hostnames:
                        info[f"🔁 Reverse DNS {ip}"] = ", ".join(hostnames)
                    sh = core.shodan_host(ip)
                    if sh:
                        for k, v in sh.items():
                            info[f"🛰️ Shodan {ip} · {k}"] = v
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
    rdap = core.ip_rdap_lookup(ip) if ip else {"Status": "❌ IP mancante"}
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
