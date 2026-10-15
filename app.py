from flask import Flask, render_template_string, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret-global-99a71d'

DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_name TEXT NOT NULL,
            manager_name TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            activity_field TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# قالب HTML بین‌المللی و فوق‌العاده مدرن (Global Enterprise B2B UI/UX)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Production & Trade Network | شبکه هوشمند توسعه تولید</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: {
                            50: '#ecfdf5',
                            500: '#10b981',
                            600: '#059669',
                            900: '#064e3b',
                            950: '#022c22',
                        }
                    }
                }
            }
        }
    </script>
    <!-- Vazirmatn Font -->
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body {
            font-family: 'Vazirmatn', sans-serif;
            background: radial-gradient(circle at 50% -20%, #064e3b 0%, #090d16 60%, #020617 100%);
            min-height: 100vh;
        }
        .glass-panel {
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .glass-input {
            background: rgba(2, 6, 23, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .glass-input:focus {
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
            background: rgba(2, 6, 23, 0.9);
        }
        .glow-effect {
            box-shadow: 0 0 40px -10px rgba(16, 185, 129, 0.3);
        }
    </style>
</head>
<body class="text-slate-100 flex flex-col min-h-screen antialiased selection:bg-emerald-500 selection:text-slate-950">

    <!-- Top Global Header -->
    <header class="glass-panel border-b border-slate-800/80 sticky top-0 z-50 px-6 py-4">
        <div class="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-emerald-700 flex items-center justify-center text-slate-950 font-black text-2xl shadow-lg glow-effect">
                    ص
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold tracking-wider">GLOBAL B2B HUB</span>
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    </div>
                    <h1 class="text-base sm:text-lg font-black tracking-tight text-white mt-0.5">شبکه هوشمند توسعه تولید و تجارت</h1>
                </div>
            </div>
            
            <nav class="flex items-center gap-1 sm:gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800 text-xs font-medium">
                <a href="/" class="px-4 py-2 rounded-lg bg-emerald-500 text-slate-950 font-bold shadow-md shadow-emerald-500/20 transition">ثبت کارگاه و واحد</a>
                <a href="#" class="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition">کاتالوگ بین‌المللی</a>
                <a href="#" class="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition">پنل مدیریت هوشمند</a>
            </nav>
        </div>
    </header>

    <!-- Main Enterprise Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex-grow w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        <!-- Left Sidebar: Ecosystem Guides & Global Metrics -->
        <div class="lg:col-span-4 space-y-6">
            <div class="glass-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden">
                <div class="absolute -top-24 -left-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
                
                <h2 class="text-base font-bold text-emerald-400 mb-2 flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    پروتکل ثبت و اتصال زنجیره تامین
                </h2>
                <p class="text-xs text-slate-400 leading-relaxed mb-8">
                    با ورود به این شبکه بین‌المللی، واحدهای تولیدی خرد و کارگاهی به سیستم جامع لجستیک، استانداردسازی صادرات و بازارهای B2B متصل می‌شوند.
                </p>

                <!-- Step Timeline -->
                <div class="space-y-6 relative before:absolute before:right-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
                    <div class="relative flex items-start gap-4">
                        <div class="w-8 h-8 rounded-xl bg-emerald-500 text-slate-950 font-bold flex items-center justify-center shrink-0 z-10 shadow-lg shadow-emerald-500/30 text-xs">01</div>
                        <div>
                            <h3 class="text-xs font-bold text-white tracking-wide">ثبت مشخصات فنی و اهراز هویت</h3>
                            <p class="text-[11px] text-slate-400 mt-1">تایید هویت واحد تولیدی، استان و حوزه تخصصی.</p>
                        </div>
                    </div>

                    <div class="relative flex items-start gap-4 opacity-60">
                        <div class="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 font-bold flex items-center justify-center shrink-0 z-10 border border-slate-700 text-xs">02</div>
                        <div>
                            <h3 class="text-xs font-bold text-white tracking-wide">بارگذاری کاتالوگ و ظرفیت عرضه</h3>
                            <p class="text-[11px] text-slate-400 mt-1">تعیین ظرفیت ماهانه و استانداردهای کیفی محصول.</p>
                        </div>
                    </div>

                    <div class="relative flex items-start gap-4 opacity-60">
                        <div class="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 font-bold flex items-center justify-center shrink-0 z-10 border border-slate-700 text-xs">03</div>
                        <div>
                            <h3 class="text-xs font-bold text-white tracking-wide">اتصال مستقیم به تجار و RFQ جهانی</h3>
                            <p class="text-[11px] text-slate-400 mt-1">دریافت سفارشات عمده و تسهیلات صادراتی.</p>
                        </div>
                    </div>
                </div>

                <div class="mt-8 pt-6 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                    <span>وضعیت شبکه:</span>
                    <span class="text-emerald-400 font-bold flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span> پایدار و امن (SSL)
                    </span>
                </div>
            </div>
        </div>

        <!-- Main Form Panel -->
        <div class="lg:col-span-8">
            <div class="glass-panel rounded-3xl p-6 sm:p-10 relative">
                <div class="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-teal-400 to-transparent rounded-t-3xl"></div>

                <div class="mb-8">
                    <div class="flex items-center justify-between">
                        <h2 class="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-3">
                            <span class="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
                            </span>
                            ثبت اطلاعات کارگاه یا واحد تولیدی
                        </h2>
                        <span class="text-xs text-slate-400 hidden sm:block">* تکمیل فیلدهای ستاره‌دار الزامی است</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-2">اطلاعات وارد شده پس از راستی‌آزمایی در پروفایل رسمی صادرکنندگان و شبکه بازار قرار می‌گیرد.</p>
                </div>

                {% with messages = get_flashed_messages(with_categories=true) %}
                  {% if messages %}
                    {% for category, message in messages %}
                      <div class="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-3 animate-fade-in">
                        <svg class="w-5 h-5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <span>{{ message }}</span>
                      </div>
                    {% endfor %}
                  {% endif %}
                {% endwith %}

                <form method="POST" action="/" class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">نام کارگاه یا واحد تولیدی <span class="text-emerald-400">*</span></label>
                        <input type="text" name="workshop_name" required placeholder="مثال: کارگاه تخصصی سفال پارسی" 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">نام مسئول / مدیر واحد <span class="text-emerald-400">*</span></label>
                        <input type="text" name="manager_name" required placeholder="نام و نام خانوادگی مدیر مسئول" 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">استان استقرار <span class="text-emerald-400">*</span></label>
                        <select name="province" required class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white focus:outline-none cursor-pointer">
                            <option value="" disabled selected class="bg-slate-900">انتخاب استان...</option>
                            <option value="تهران" class="bg-slate-900">تهران</option>
                            <option value="اصفهان" class="bg-slate-900">اصفهان</option>
                            <option value="خراسان رضوی" class="bg-slate-900">خراسان رضوی</option>
                            <option value="فارس" class="bg-slate-900">فارس</option>
                            <option value="یزد" class="bg-slate-900">یزد</option>
                            <option value="کرمان" class="bg-slate-900">کرمان</option>
                            <option value="گیلان" class="bg-slate-900">گیلان</option>
                            <option value="مازندران" class="bg-slate-900">مازندران</option>
                            <option value="سایر" class="bg-slate-900">سایر استان‌ها</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">شهرستان / منطقه صنعتی <span class="text-emerald-400">*</span></label>
                        <input type="text" name="city" required placeholder="مثال: کاشان، میبد، شیراز..." 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">حوزه تخصصی فعالیت <span class="text-emerald-400">*</span></label>
                        <input type="text" name="activity_field" required placeholder="صنایع دستی، فرش، سفال، تولیدات خرد..." 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-2">شماره تماس / تلفن همراه <span class="text-emerald-400">*</span></label>
                        <input type="text" name="phone" required placeholder="09123456789" 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none" dir="ltr">
                    </div>

                    <div class="sm:col-span-2">
                        <label class="block text-xs font-bold text-slate-300 mb-2">آدرس دقیق پستی</label>
                        <input type="text" name="address" placeholder="استان، شهر، خیابان اصلی، پلاک، کد پستی..." 
                               class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-white placeholder-slate-500 focus:outline-none">
                    </div>

                    <div class="sm:col-span-2">
                        <label class="block text-xs font-bold text-slate-300 mb-2">توضیحات تکمیلی و ظرفیت تولید ماهانه</label>
                        <textarea name="description" rows="3" placeholder="شرح مختصر محصولات، حجم تولید ماهانه و نیازمندی‌های توسعه‌ای..." 
                                  class="w-full glass-input rounded-2xl p-4 text-xs text-white placeholder-slate-500 focus:outline-none resize-none"></textarea>
                    </div>

                    <div class="sm:col-span-2 pt-4">
                        <button type="submit" class="w-full py-4 rounded-2xl bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 text-slate-950 font-black text-sm tracking-wide shadow-xl shadow-emerald-900/40 hover:brightness-110 active:scale-[0.99] transition flex items-center justify-center gap-3 group">
                            <span>ثبت اطلاعات کارگاه و ورود به شبکه بازار B2B</span>
                            <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                        </button>
                    </div>
                </form>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="glass-panel border-t border-slate-800/80 py-6 text-center text-xs text-slate-400 mt-auto">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p>شبکه هوشمند توسعه تولید و رفع موانع | سامانه ملی اتصال زنجیره تامین صنایع خرد و خانگی</p>
            <p class="text-emerald-400/80 font-mono text-[11px]">Render Cloud Deployment • v2.4 Enterprise</p>
        </div>
    </footer>

</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        workshop_name = request.form.get('workshop_name')
        manager_name = request.form.get('manager_name')
        province = request.form.get('province')
        city = request.form.get('city')
        activity_field = request.form.get('activity_field')
        phone = request.form.get('phone')
        address = request.form.get('address')
        description = request.form.get('description')

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO workshops (workshop_name, manager_name, province, city, activity_field, phone, address, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (workshop_name, manager_name, province, city, activity_field, phone, address, description))
        conn.commit()
        conn.close()

        flash('اطلاعات کارگاه با موفقیت در پایگاه داده مرکزی ثبت شد و پروتکل اتصال فعال گردید.', 'success')
        return redirect(url_for('index'))

    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
