from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import csv
from datetime import datetime

app = Flask(__name__)
CORS(app)

PINTEREST_API = "https://api.pinterest.com/v5"


# =========================
# HELPERS
# =========================

def pinterest_get(endpoint, token, params=None):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{PINTEREST_API}{endpoint}"

    r = requests.get(
        url,
        headers=headers,
        params=params
    )

    print("REQUEST URL:", r.url)
    print("STATUS:", r.status_code)

    if r.status_code >= 400:
        try:
            error_text = r.text.encode("utf-8", errors="ignore").decode("utf-8")
        except:
            error_text = "Pinterest API Error"

        raise Exception(f"Pinterest API Error {r.status_code}: {error_text}")

    return r.json()


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

    except Exception as e:
        print("BOARD ANALYTICS ERROR:", str(e))

        return {
            "board_id": board_id,
            "error": str(e),
            "analytics": {
                "IMPRESSION": 0,
                "SAVE": 0,
                "OUTBOUND_CLICK": 0,
                "PIN_CLICK": 0
            }
        }


# =========================
# FRONTEND
# =========================

@app.route("/")
def home():
    return send_file("dashboard.html")


# =========================
# TEST TOKEN
# =========================

@app.route("/api/test-token", methods=["POST"])
def test_token():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        data = pinterest_get(
            "/user_account",
            token
        )

        return jsonify({
            "ok": True,
            "account": data
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# GET BOARDS
# =========================

@app.route("/api/boards", methods=["POST"])
def get_boards():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        data = pinterest_get(
            "/boards",
            token
        )

        return jsonify({
            "ok": True,
            "items": data.get("items", [])
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# BOARD PINS
# =========================

@app.route("/api/board-pins", methods=["POST"])
def board_pins():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()
        board_id = body.get("board_id")

        data = pinterest_get(
            f"/boards/{board_id}/pins",
            token
        )

        return jsonify({
            "ok": True,
            "items": data.get("items", [])
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# BOARD ANALYTICS
# =========================

@app.route("/api/board-analytics", methods=["POST"])
def board_analytics():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        board_id = body.get("board_id")

        start_date = body.get("start_date")
        end_date = body.get("end_date")

        result = fetch_board_analytics(
            board_id,
            token,
            start_date,
            end_date
        )

        return jsonify({
            "ok": True,
            "analytics": result
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# PIN ANALYTICS
# =========================

@app.route("/api/pin-analytics", methods=["POST"])
def pin_analytics():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        pin_id = body.get("pin_id")

        start_date = body.get("start_date")
        end_date = body.get("end_date")

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "metric_types": "IMPRESSION,SAVE,OUTBOUND_CLICK,PIN_CLICK"
        }

        res = pinterest_get(
            f"/pins/{pin_id}/analytics",
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

        return jsonify({
            "ok": True,
            "analytics": totals
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# MULTI BOARD ANALYTICS
# =========================

@app.route("/api/multi-board-analytics", methods=["POST"])
def multi_board_analytics():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        board_ids = body.get("board_ids", [])

        start_date = body.get("start_date")
        end_date = body.get("end_date")

        results = []

        for board_id in board_ids:

            result = fetch_board_analytics(
                board_id,
                token,
                start_date,
                end_date
            )

            results.append(result)

        return jsonify({
            "ok": True,
            "results": results
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# ACCOUNT ANALYTICS
# =========================

@app.route("/api/account-analytics", methods=["POST"])
def account_analytics():

    try:
        body = request.get_json()

        token = body.get("token", "").strip()

        start_date = body.get("start_date")
        end_date = body.get("end_date")

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

        return jsonify({
            "ok": True,
            "analytics": res
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# EXPORT CSV
# =========================

@app.route("/api/export-csv", methods=["POST"])
def export_csv():

    try:
        body = request.get_json()

        rows = body.get("rows", [])

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "Board Name",
            "Impressions",
            "Saves",
            "Outbound Clicks",
            "Pin Clicks"
        ])

        for row in rows:

            writer.writerow([
                row.get("board_name"),
                row.get("IMPRESSION"),
                row.get("SAVE"),
                row.get("OUTBOUND_CLICK"),
                row.get("PIN_CLICK")
            ])

        mem = io.BytesIO()
        mem.write(output.getvalue().encode("utf-8"))
        mem.seek(0)

        filename = f"pinterest_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
