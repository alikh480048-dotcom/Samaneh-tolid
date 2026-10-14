import os
from flask import Flask, send_from_directory, jsonify, request

app = Flask(__name__, static_folder='.')

@app.route('/')
def home():
    # باز کردن صفحه اصلی سامانه
    return send_from_directory('.', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "active", "service": "Samaneh-tolid Backend"})

# مسیر دریافت فرم‌های ثبت‌نام یا رفع موانع
@app.route('/api/submit', methods=['POST'])
def handle_submit():
    data = request.json or {}
    return jsonify({
        "status": "success",
        "message": "اطلاعات با موفقیت در موتور سامانه ثبت شد.",
        "received": data
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
