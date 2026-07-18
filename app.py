import os
import re
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# --- Supabase Configuration ---
SUPABASE_URL = "SUPABASE_URL"
SUPABASE_KEY = "SUPABASE_KEY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    country = data.get('country', '').strip()

    if not user_id or not name or not email:
        return jsonify({"status": "error", "message": "Mobile, Name aur Email teeno zaroori hain!"}), 400

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"status": "error", "message": "🚨 Invalid Email Format!"}), 400

    clean_number = user_id.replace('+', '')
    if not clean_number.isdigit():
        return jsonify({"status": "error", "message": "🚨 Invalid Mobile Number!"}), 400

    try:
        clean_user_id = user_id if user_id.startswith('+') else '+' + user_id
        res = supabase.table('profiles').select('*').eq('user_id', clean_user_id).execute()
        
        if res.data:
            return jsonify({"status": "success", "user": res.data[0]})
        else:
            new_user = supabase.table('profiles').insert({
                'user_id': clean_user_id,
                'name': name,
                'email': email,
                'country': country,
                'coins': 0
            }).execute()
            return jsonify({"status": "success", "user": new_user.data[0]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/claim', methods=['POST'])
def claim_reward():
    data = request.json
    user_id = data.get('user_id')
    reward = data.get('reward', 0)
    try:
        res = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()
        if not res.data:
            return jsonify({"status": "error", "message": "User not found"}), 404
            
        new_balance = res.data[0].get('coins', 0) + reward
        supabase.table('profiles').update({'coins': new_balance}).eq('user_id', user_id).execute()
        return jsonify({"status": "success", "new_balance": new_balance})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/withdraw', methods=['POST'])
def withdraw_money():
    data = request.json
    user_id = data.get('user_id')
    upi = data.get('upi')
    phonepe = data.get('phonepe')
    paytm = data.get('paytm')
    amount = data.get('amount')

    try:
        supabase.table('withdraw_requests').insert({
            'user_id': user_id,
            'upi': upi,
            'phonepe': phonepe,
            'paytm': paytm,
            'amount_requested': amount,
            'status': 'PENDING'
        }).execute()
        
        return jsonify({"status": "success", "message": "Withdrawal request bheji gayi!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# [NOTE: link-bank endpoint yahan se hata diya gaya hai]

@app.route('/api/exchange', methods=['POST'])
def execute_exchange():
    data = request.json
    user_id = data.get('user_id')
    payout_amount = data.get('amount')

    if not user_id or payout_amount not in [10, 50, 100]:
        return jsonify({"status": "error", "message": "Invalid request!"}), 400

    try:
        res = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()
        if not res.data:
            return jsonify({"status": "error", "message": "User profile nahi mila!"}), 404

        current_coins = res.data[0].get('coins', 0)
        required_coins = payout_amount * 100

        if current_coins < required_coins:
            return jsonify({"status": "error", "message": "Insufficient Coins!"}), 400

        new_balance = current_coins - required_coins
        supabase.table('profiles').update({'coins': new_balance}).eq('user_id', user_id).execute()

        supabase.table('exchange_requests').insert({
            "user_id": user_id,
            "amount_rs": payout_amount,
            "coins_deducted": required_coins,
            "status": f"₹{payout_amount} PENDING"
        }).execute()

        return jsonify({"status": "success", "message": "Exchange processing me hai!", "new_balance": new_balance})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    try:
        supabase.table("feedback").insert({
            "user_id": data.get("user_id"),
            "message": f"{data.get('rating')}\n{data.get('message')}"
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-balance', methods=['POST'])
def get_balance():
    data = request.json
    res = supabase.table('profiles').select('coins').eq('user_id', data.get('user_id')).execute()
    if res.data:
        return jsonify({"status": "success", "coins": res.data[0]['coins']})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/api/complete-activity', methods=['POST'])
def complete_activity():
    data = request.json
    user_id = data.get('user_id')
    try:
        res = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()
        current_coins = res.data[0].get('coins', 0)
        new_balance = current_coins + data.get('coins', 0)
        supabase.table('profiles').update({'coins': new_balance}).eq('user_id', user_id).execute()
        supabase.table('user_activities').insert({'user_id': user_id, 'activity_type': data.get('activity_type')}).execute()
        return jsonify({"status": "success", "new_balance": new_balance})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
