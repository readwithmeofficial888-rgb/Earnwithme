
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

    clean_user_id = user_id if user_id.startswith('+') else '+' + user_id
    
    try:
        # Check if user exists
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
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID missing"}), 400
        
    res = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()
    if res.data:
        return jsonify({"status": "success", "coins": res.data[0]['coins']})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/api/complete-activity', methods=['POST'])
def complete_activity():
    data = request.json
    user_id = data.get('user_id')
    coins_to_add = data.get('coins', 0)
    activity_type = data.get('activity_type')
    
    if not user_id:
        return jsonify({"status": "error", "message": "User ID missing"}), 400

    try:
        # Using RPC to update coins safely (requires function 'add_coins' in Supabase)
        # SQL: update profiles set coins = coins + amount where user_id = uid;

        # 👇 YE CODE YAHAN PASTE KARNA HAI
        profile = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()

        if not profile.data:
            return jsonify({"status": "error", "message": "User not found"}), 404

        current_coins = int(profile.data[0]['coins'])
        new_balance = current_coins + int(coins_to_add)

        supabase.table('profiles').update({
            'coins': new_balance
        }).eq('user_id', user_id).execute()

        # 👇 Iske baad tumhara ye code waise hi rahega
        supabase.table('user_activities').insert({
            'user_id': user_id,
            'activity_type': activity_type
        }).execute()

        res = supabase.table('profiles').select('coins').eq('user_id', user_id).execute()
        new_balance = res.data[0]['coins'] if res.data else 0

        return jsonify({"status": "success", "new_balance": new_balance})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/withdraw', methods=['POST'])
def withdraw_money():
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount')
    upi = data.get('upi')

    try:
        # Supabase RPC call (ensure 'withdraw_coins' function is created in SQL Editor)
        res = supabase.rpc('withdraw_coins', {'uid': user_id, 'amount_to_withdraw': amount}).execute()
        
        # Agar RPC 'true' return karta hai, tabhi aage badhein
        if res.data == True:
            supabase.table('withdraw_requests').insert({
                'user_id': user_id,
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
