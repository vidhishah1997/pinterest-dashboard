"""
Pinterest Analytics Tool - Backend Server
==========================================
Run this file on your computer. It creates a local server at http://localhost:5000
that acts as a bridge between your browser and the Pinterest API.

HOW TO RUN:
  1. Open your terminal / command prompt
  2. cd into this folder
  3. Run: python server.py
  4. Open your browser and go to: http://localhost:5000
  5. Enter your Pinterest Access Token and start fetching data

INSTALL REQUIREMENTS FIRST (run once):
  pip install flask requests
"""

import json
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
import requests as req
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__, static_folder=".")

PINTEREST_BASE = "https://api.pinterest.com/v5"

# =========================================================
# OPTIMIZED SESSION (FASTER REQUESTS)
# =========================================================
session = req.Session()

retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(
    pool_connections=50,
    pool_maxsize=50,
    max_retries=retries
)

session.mount("https://", adapter)

# =========================================================
# HELPER: Pinterest API Call
# =========================================================
def pinterest_get(endpoint, token, params=None):
    url = PINTEREST_BASE + endpoint

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    r = session.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    data = r.json()

    if r.status_code == 401:
        raise Exception(
            "Invalid token or token expired."
        )

    if r.status_code == 403:
        raise Exception(
            "Access forbidden. Check Pinterest scopes."
        )

    if r.status_code == 429:
        raise Exception(
            "Pinterest rate limit hit."
        )

    if not r.ok:
        msg = data.get("message", r.text[:200])
        raise Exception(
            f"Pinterest API error {r.status_code}: {msg}"
        )

    return data

# =========================================================
# SERVE FRONTEND
# =========================================================
@app.route("/")
def index():
    return send_from_directory(".", "dashboard.html")

# =========================================================
# TEST TOKEN
# =========================================================
@app.route("/api/test-token", methods=["POST"])
def test_token():
    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        if not token:
            return jsonify({
                "ok": False,
                "error": "No token provided"
            })

        user = pinterest_get("/user_account", token)

        return jsonify({
            "ok": True,
            "username": user.get("username", ""),
            "account_type": user.get("account_type", ""),
            "profile_image": user.get("profile_image", "")
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        })

# =========================================================
# FETCH ALL BOARDS
# =========================================================
@app.route("/api/boards", methods=["POST"])
def get_boards():
    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        all_boards = []

        bookmark = None

        while True:

            params = {
                "page_size": 100
            }

            if bookmark:
                params["bookmark"] = bookmark

            res = pinterest_get(
                "/boards",
                token,
                params
            )

            all_boards.extend(
                res.get("items", [])
            )

            bookmark = res.get("bookmark")

            if not bookmark:
                break

        return jsonify({
            "ok": True,
            "boards": all_boards
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        })

# =========================================================
# FETCH BOARD PINS
# =========================================================
@app.route("/api/board-pins", methods=["POST"])
def get_board_pins():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()
        board_id = body.get("board_id", "")

        all_pins = []

        bookmark = None

        while True:

            params = {
                "page_size": 100
            }

            if bookmark:
                params["bookmark"] = bookmark

            res = pinterest_get(
                f"/boards/{board_id}/pins",
                token,
                params
            )

            all_pins.extend(
                res.get("items", [])
            )

            bookmark = res.get("bookmark")

            if not bookmark:
                break

        return jsonify({
            "ok": True,
            "pins": all_pins
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        })

# =========================================================
# FAST ANALYTICS HELPER
# =========================================================
def fetch_board_analytics(board_id, token, start_date, end_date):

    try:

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "metric_types": "IMPRESSION,SAVE,OUTBOUND_CLICK,PIN_CLICK"
        }

        res = pinterest_get(
            f"/boards/{board_id}/analytics",
            token,
            params
        )

        totals = {
            "IMPRESSION": 0,
            "SAVE": 0,
            "OUTBOUND_CLICK": 0,
            "PIN_CLICK": 0
        }

        daily = res.get("all", {}).get("daily_metrics", [])

        for day in daily:

            metrics = day.get("metrics", {})

            for k in totals:
                totals[k] += metrics.get(k, 0)

        return {
            "board_id": board_id,
            "analytics": totals
        }

    except Exception:

        return {
            "board_id": board_id,
            "analytics": {
                "IMPRESSION": 0,
                "SAVE": 0,
                "OUTBOUND_CLICK": 0,
                "PIN_CLICK": 0
            }
        }

# =========================================================
# PARALLEL BOARD ANALYTICS
# =========================================================
@app.route("/api/multi-board-analytics", methods=["POST"])
def multi_board_analytics():

    try:

        body = request.get_json()

        token = body.get("token", "").strip()

        board_ids = body.get("board_ids", [])

        start_date = body.get("start_date", "")
        end_date = body.get("end_date", "")

        results = []

        # SAFE THREAD COUNT
        max_workers = 8

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            futures = [
                executor.submit(
                    fetch_board_analytics,
                    board_id,
                    token,
                    start_date,
                    end_date
                )
                for board_id in board_ids
            ]

            for future in as_completed(futures):
                results.append(
                    future.result()
                )

        return jsonify({
            "ok": True,
            "results": results
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        })

# =========================================================
# ACCOUNT ANALYTICS
# =========================================================
@app.route("/api/account-analytics", methods=["POST"])
def get_account_analytics():

    try:

        body = request.get_json()

        token = body.get("token", "").strip()

        start_date = body.get("start_date", "")
        end_date = body.get("end_date", "")

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "metric_types": "IMPRESSION,SAVE,OUTBOUND_CLICK,PIN_CLICK"
        }

        res = pinterest_get(
            "/user_account/analytics",
            token,
            params
        )

        totals = {
            "IMPRESSION": 0,
            "SAVE": 0,
            "OUTBOUND_CLICK": 0,
            "PIN_CLICK": 0
        }

        daily = res.get("all", {}).get(
            "daily_metrics",
            []
        )

        for day in daily:

            metrics = day.get("metrics", {})

            for k in totals:
                totals[k] += metrics.get(k, 0)

        return jsonify({
            "ok": True,
            "analytics": totals,
            "daily": daily
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        })

# =========================================================
# START SERVER
# =========================================================
if __name__ == "__main__":

    print("\n" + "="*55)
    print(" Pinterest Analytics Tool")
    print("="*55)
    print(" Server running at:")
    print(" http://localhost:5000")
    print("="*55 + "\n")

    app.run(
        debug=False,
        port=5000,
        host="0.0.0.0",
        threaded=True
    )