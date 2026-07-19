import os
import re
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper function to ensure user_id starts with '+'
def get_clean_uid(uid):
    uid = str(uid).strip()
    return uid if uid.startswith('+') else '+' + uid

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

    clean_user_id = get_clean_uid(user_id)
    
    try:
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-balance', methods=['POST'])
def get_balance():
    data = request.json
    uid = data.get('user_id')
    if not uid:
        return jsonify({"status": "error", "message": "User ID missing"}), 400
        
    clean_uid = get_clean_uid(uid)
    res = supabase.table('profiles').select('coins').eq('user_id', clean_uid).execute()
    
    if res.data:
        return jsonify({"status": "success", "coins": res.data[0]['coins']})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/api/complete-activity', methods=['POST'])
def complete_activity():
    data = request.json
    uid = data.get('user_id', '').strip()
    coins_to_add = int(data.get('coins', 0))
    activity_type = data.get('activity_type')
    
    if not uid:
        return jsonify({"status": "error", "message": "User ID missing"}), 400

    clean_uid = get_clean_uid(uid)

    try:
        profile = supabase.table('profiles').select('coins').eq('user_id', clean_uid).execute()

        if not profile.data:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Update coins via RPC
        supabase.rpc('add_coins', {
            'uid': clean_uid,
            'amount': coins_to_add
        }).execute()

        # Log activity
        supabase.table('user_activities').insert({
            'user_id': clean_uid,
            'activity_type': activity_type
        }).execute()

        # Fetch updated balance
        res = supabase.table('profiles').select('coins').eq('user_id', clean_uid).execute()
        new_balance = res.data[0]['coins'] if res.data else 0

        return jsonify({"status": "success", "new_balance": new_balance})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/withdraw', methods=['POST'])
def withdraw_money():
    data = request.json
    uid = data.get('user_id')
    amount = data.get('amount')
    upi = data.get('upi')
    
    clean_uid = get_clean_uid(uid)

    try:
        res = supabase.rpc('withdraw_coins', {'uid': clean_uid, 'amount_to_withdraw': amount}).execute()
        
        if res.data == True:
            supabase.table('withdraw_requests').insert({
                'user_id': clean_uid,
                'upi': upi,
                'amount_requested': amount,
                'status': 'PENDING'
            }).execute()
            return jsonify({"status": "success", "message": "Withdrawal request submitted!"})
        else:
            return jsonify({"status": "error", "message": "Insufficient coins or user not found"}), 400
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
