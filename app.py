import os
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# LOGIN
# ==========================
@app.route("/api/login", methods=["POST"])
def login():

    data = request.json

    user_id = data.get("user_id", "").strip()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    country = data.get("country", "").strip()

    if not user_id or not name or not email:
        return jsonify({
            "status": "error",
            "message": "Missing Details"
        }), 400

    if not user_id.startswith("+"):
        user_id = "+" + user_id

    try:

        existing = (
            supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if existing.data:

            return jsonify({
                "status": "success",
                "user": existing.data[0]
            })

        created = (
            supabase.table("profiles")
            .insert({
                "user_id": user_id,
                "name": name,
                "email": email,
                "country": country,
                "coins": 0
            })
            .execute()
        )

        return jsonify({
            "status": "success",
            "user": created.data[0]
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ==========================
# GET BALANCE
# ==========================
@app.route("/api/get-balance", methods=["POST"])
def get_balance():

    data = request.json

    user_id = data.get("user_id")

    if not user_id:

        return jsonify({
            "status": "error",
            "message": "User ID Missing"
        }), 400

    try:

        res = (
            supabase.table("profiles")
            .select("coins")
            .eq("user_id", user_id)
            .execute()
        )

        if not res.data:

            return jsonify({
                "status": "error",
                "message": "User Not Found"
            }), 404

        return jsonify({
            "status": "success",
            "coins": res.data[0]["coins"]
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ==========================
# COMPLETE ACTIVITY
# ==========================
@app.route("/api/complete-activity", methods=["POST"])
def complete_activity():

    data = request.json

    user_id = data.get("user_id")
    coins_to_add = int(data.get("coins", 0))
    activity_type = data.get("activity_type", "Unknown")

    if not user_id:

        return jsonify({
            "status": "error",
            "message": "User ID Missing"
        }), 400

    try:

        profile = (
            supabase.table("profiles")
            .select("coins")
            .eq("user_id", user_id)
            .execute()
        )

        if not profile.data:

            return jsonify({
                "status": "error",
                "message": "User Not Found"
            }), 404

        old_balance = int(profile.data[0]["coins"])

        new_balance = old_balance + coins_to_add

        (
            supabase.table("profiles")
            .update({
                "coins": new_balance
            })
            .eq("user_id", user_id)
            .execute()
        )

        try:

            supabase.table("user_activities").insert({

                "user_id": user_id,
                "activity_type": activity_type,
                "coins": coins_to_add

            }).execute()

        except:

            pass

        return jsonify({

            "status": "success",
            "new_balance": new_balance

        })

    except Exception as e:

        return jsonify({

            "status": "error",
            "message": str(e)

        }), 500


# ==========================
# WITHDRAW
# ==========================
@app.route("/api/withdraw", methods=["POST"])
def withdraw():

    data = request.json

    user_id = data.get("user_id")
    amount = int(data.get("amount", 0))
    upi = data.get("upi")

    try:

        profile = (
            supabase.table("profiles")
            .select("coins")
            .eq("user_id", user_id)
            .execute()
        )

        if not profile.data:

            return jsonify({

                "status": "error",
                "message": "User Not Found"

            }), 404

        balance = int(profile.data[0]["coins"])

        if balance < amount:

            return jsonify({

                "status": "error",
                "message": "Insufficient Coins"

            }), 400

        remaining = balance - amount

        (
            supabase.table("profiles")
            .update({
                "coins": remaining
            })
            .eq("user_id", user_id)
            .execute()
        )

        try:

            supabase.table("withdraw_requests").insert({

                "user_id": user_id,
                "upi": upi,
                "amount_requested": amount,
                "status": "PENDING"

            }).execute()

        except:

            pass

        return jsonify({

            "status": "success",
            "new_balance": remaining,
            "message": "Withdrawal Request Submitted"

        })

    except Exception as e:

        return jsonify({

            "status": "error",
            "message": str(e)

        }), 500


if __name__ == "__main__":
    app.run(debug=True)
