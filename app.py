import streamlit as st
import requests
import json
import time
import folium
from streamlit_folium import folium_static
from datetime import datetime
import urllib.parse
import base64

# ============================================
# 🔑 CREDENTIALS (dari Streamlit Secrets)
# ============================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    API_KEY_FIX = st.secrets["GEMINI_API_KEY"]
except:
    SUPABASE_URL = "https://your-project.supabase.co"
    SUPABASE_KEY = "your-anon-key"
    API_KEY_FIX = "your-gemini-key"

# ============================================
# 🗄️ SUPABASE HELPER FUNCTIONS
# ============================================
def supabase_request(endpoint, method="GET", data=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        if response.status_code in [200, 201, 204]:
            return response.json() if response.text else []
        else:
            st.error(f"Supabase Error {response.status_code}: {response.text}")
            return []
    except Exception as e:
        st.error(f"Supabase Error: {e}")
        return []

def load_all_warung():
    data = supabase_request("warung?order=id.asc")
    return data

def save_warung(warung):
    if warung.get('id') is None:
        warung.pop('id', None)
    existing = supabase_request(f"warung?nama=eq.{warung['nama']}&lokasi=eq.{warung['lokasi']}")
    if existing:
        warung_id = existing[0]['id']
        supabase_request(f"warung?id=eq.{warung_id}", method="PATCH", data=warung)
    else:
        supabase_request("warung", method="POST", data=warung)

def delete_warung(warung_id):
    supabase_request(f"warung?id=eq.{warung_id}", method="DELETE")

def get_next_id():
    data = supabase_request("warung?select=id&order=id.desc&limit=1")
    if data:
        return data[0]['id'] + 1
    return 1

# ============================================
# 📦 LOAD DATA
# ============================================
if 'warung_ciledug' not in st.session_state:
    st.session_state.warung_ciledug = load_all_warung()

# ============================================
# 🗺️ MAP
# ============================================
def tampilkan_map(warung_list):
    center_lat = -6.2186
    center_lon = 106.7012
    try:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
        for w in warung_list:
            lat = w.get('lat')
            lon = w.get('lon')
            if lat is not None and lon is not None:
                try:
                    lat = float(lat)
                    lon = float(lon)
                except:
                    continue
                status = w.get('status', '')
                if "Underrated" in status:
                    color, icon = 'purple', 'star'
                elif "Hidden Gem" in status:
                    color, icon = 'blue', 'info-sign'
                elif "Legend" in status:
                    color, icon = 'orange', 'fire'
                elif "Viral" in status:
                    color, icon = 'red', 'bullhorn'
                else:
                    color, icon = 'green', 'ok'
                popup_text = f"""
                <b>{w['nama']}</b><br>
                📍 {w['lokasi']}<br>
                💰 {w['harga']}<br>
                ⭐ {w['rating']}<br>
                🏷️ {status}
                """
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=w['nama'],
                    icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
                ).add_to(m)
        return m
    except:
        return None

# ============================================
# 📍 KONFIGURASI
# ============================================
WILAYAH_CILEDUG = [
    "Semua Ciledug Raya",
    "Karang Mulya", "Karang Timur", "Karang Sari",
    "Sudimara Barat", "Sudimara Timur", "Sudimara Selatan", "Sudimara Jaya",
    "Paninggilan", "Paninggilan Utara",
    "Tajur", "Parung Serab",
    "Larangan Selatan", "Larangan Utara", "Larangan Indah",
    "Petukangan", "Jurang Mangu", "Parigi", "Pondok Kacang", "Pondok Betung",
    "Ciledug"
]

KATEGORI = [
    "Mie Ayam", "Nasi Goreng", "Bakso", "Sate", "Nasi Uduk", 
    "Gado-gado", "Soto", "Padang", "Pecel Ayam", "Pecel Lele", 
    "Ayam Goreng", "Seafood", "Bubur Ayam", "Ketupat Sayur",
    "Nasi Bebek", "Lainnya"
]

STATUS_WARUNG = [
    "💎 Underrated",
    "⭐ Hidden Gem", 
    "🔥 Legend",
    "👍 Review Bagus",
    "📱 Viral"
]

# ============================================
# 🔍 FUNGSI CARI
# ============================================
def deteksi_kategori_dari_prompt(prompt):
    prompt_lower = prompt.lower()
    keyword_map = {
        "nasi bebek": "Nasi Bebek", "bebek": "Nasi Bebek",
        "mie ayam": "Mie Ayam", "mie": "Mie Ayam",
        "nasi goreng": "Nasi Goreng",
        "bakso": "Bakso",
        "sate": "Sate",
        "nasi uduk": "Nasi Uduk", "uduk": "Nasi Uduk",
        "gado-gado": "Gado-gado", "gado": "Gado-gado",
        "soto": "Soto",
        "padang": "Padang",
        "pecel ayam": "Pecel Ayam",
        "pecel lele": "Pecel Lele", "lele": "Pecel Lele",
        "ayam goreng": "Ayam Goreng",
        "bubur ayam": "Bubur Ayam", "bubur": "Bubur Ayam",
        "ketupat": "Ketupat Sayur",
    }
    for keyword, kategori in keyword_map.items():
        if keyword in prompt_lower:
            return kategori
    return None

def cari_warung(lokasi_user, prompt_user):
    semua_warung = []
    kategori_terdeteksi = deteksi_kategori_dari_prompt(prompt_user)
    for warung in st.session_state.warung_ciledug:
        cocok = True
        if lokasi_user != "Semua Ciledug Raya":
            if lokasi_user.lower() not in warung["lokasi"].lower():
                cocok = False
        if kategori_terdeteksi:
            if warung["kategori"].lower() != kategori_terdeteksi.lower():
                cocok = False
        if cocok:
            semua_warung.append(warung)
    urutan_prioritas = {
        "💎 Underrated": 1, "⭐ Hidden Gem": 2,
        "🔥 Legend": 3, "👍 Review Bagus": 4, "📱 Viral": 5
    }
    semua_warung = sorted(semua_warung, key=lambda x: urutan_prioritas.get(x.get("status", ""), 99))
    return semua_warung, kategori_terdeteksi

# ============================================
# 🤖 PANGGIL AI (FIX: TIMEOUT 60s + RETRY 3x)
# ============================================
def panggil_ai(api_key, data_warung, prompt_user, lokasi_user):
    if not data_warung:
        return "Maaf, belum ada data warung yang cocok. Bantu kami tambahkan data ya! 🙏"
    
    prompt = f"""
Kamu adalah asisten kuliner Ciledug Raya yang RAMAH, JUJUR, dan ADIL.

LOKASI: {lokasi_user if lokasi_user else "Ciledug Raya"}
PERTANYAAN: {prompt_user}

DATA WARUNG:
{json.dumps(data_warung, indent=2, ensure_ascii=False)}

TUGAS:
1. Rekomendasi berdasarkan data di atas
2. PRIORITAS: Underrated → Hidden Gem → Legend → Review Bagus → Viral
3. Sebutkan kelebihan, kekurangan, jadwal buka
4. Gaya bahasa santai seperti ngobrol sama tetangga

JAWABAN:
"""
    
    model = "gemini-3.6-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    # 🔥 COBA 3x DENGAN TIMEOUT 60 DETIK
    for percobaan in range(3):
        try:
            time.sleep(2)  # Jeda antar percobaan
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                hasil = response.json()
                return hasil['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"❌ **Error Gemini API**\n\nStatus: {response.status_code}\n\n{response.text[:300]}"
                
        except requests.exceptions.Timeout:
            if percobaan < 2:
                continue  # Coba lagi
            else:
                return "❌ **Koneksi Timeout**\n\nServer Gemini tidak merespon setelah 60 detik.\n\n💡 Coba lagi nanti atau cari di jam yang lebih sepi ya! 🙏"
                
        except Exception as e:
            return f"❌ **Error Koneksi:** {str(e)}"
    
    return "❌ Gagal setelah 3 kali percobaan. Coba lagi nanti."

# ============================================
# 🏠 TAMPILAN UTAMA
# ============================================
st.set_page_config(page_title="Ciledug Food AI", page_icon="🍲", layout="wide")

st.markdown("""
    <style>
    .main-title {
        font-size: 64px !important;
        font-weight: 900 !important;
        color: #D97706;
        text-align: center;
        margin-top: 10px;
        letter-spacing: -1px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .sub-title {
        text-align: center;
        color: #4B5563;
        font-style: italic;
        margin-bottom: 20px;
        font-size: 18px;
    }
    .footer {
        text-align: center;
        color: #6B7280;
        font-size: 12px;
        margin-top: 20px;
    }
    .gmaps-link {
        display: inline-block;
        background: #4285F4;
        color: white !important;
        padding: 6px 14px;
        border-radius: 20px;
        text-decoration: none;
        font-size: 13px;
        margin-top: 6px;
    }
    .gmaps-link:hover {
        background: #3367D6;
        color: white !important;
    }
    .total-warung {
        text-align: center;
        font-size: 20px;
        color: #4B5563;
        margin-bottom: 10px;
        font-weight: 500;
    }
    @media (max-width: 600px) {
        .main-title { font-size: 40px !important; }
        .sub-title { font-size: 14px !important; }
        .stTextInput input { font-size: 16px !important; }
        .stTextArea textarea { font-size: 16px !important; }
        .stButton button {
            font-size: 16px !important;
            padding: 12px !important;
        }
        .total-warung { font-size: 16px; }
    }
    </style>
""", unsafe_allow_html=True)

# ===== LOGO + JUDUL + SUBTITLE =====
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

try:
    logo_base64 = get_base64_image("Images/logo.png")
    st.markdown(f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
        <img src="data:image/png;base64,{logo_base64}" width="70" style="display: block; margin: 0 auto;">
        <h1 class="main-title" style="margin-top: 5px; text-align: center;">Ciledug Food AI</h1>
        <p class="sub-title" style="text-align: center; color: #4B5563; font-style: italic; margin-top: -10px; font-size: 18px;">Dari warga Ciledug Raya, untuk warga Ciledug Raya</p>
    </div>
    """, unsafe_allow_html=True)
except:
    st.markdown('<p style="text-align: center; font-size: 48px; margin-bottom: -15px;">🍲</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title" style="text-align: center;">Ciledug Food AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title" style="text-align: center; color: #4B5563; font-style: italic; font-size: 18px;">Dari warga Ciledug Raya, untuk warga Ciledug Raya</p>', unsafe_allow_html=True)

st.markdown("---")

# ============================================
# 🗂️ TAB
# ============================================
tab1, tab2, tab3 = st.tabs(["🔍 Cari Kuliner", "➕ Rekomendasikan Tempat", "📋 Admin Panel"])

# ============================================
# TAB 1: CARI KULINER
# ============================================
with tab1:
    st.markdown("### 🗺️ Cari Kuliner")
    st.caption("💡 Cukup tulis makanan yang kamu cari, AI akan mencarikan untukmu!")
    
    with st.form("search_form"):
        lokasi = st.selectbox("📍 Lokasi Pencarian Kuliner:", WILAYAH_CILEDUG, index=0)
        prompt_user = st.text_area("💬 Mau makan apa?", 
                                   placeholder="Contoh: 'Cari nasi bebek enak buat makan malam'", 
                                   height=80)
        submitted = st.form_submit_button("🔍 Cari Rekomendasi", use_container_width=True)
    
    if submitted and prompt_user:
        with st.spinner("🔍 Mencari kuliner..."):
            warung_ditemukan, kategori_terdeteksi = cari_warung(lokasi, prompt_user)
            if warung_ditemukan:
                if kategori_terdeteksi:
                    st.info(f"🔍 Menemukan {len(warung_ditemukan)} {kategori_terdeteksi} di **{lokasi}**")
                else:
                    st.info(f"🔍 Menemukan {len(warung_ditemukan)} kuliner di **{lokasi}**")
                
                jawaban_ai = panggil_ai(API_KEY_FIX, warung_ditemukan, prompt_user, lokasi)
                st.markdown("### 🤖 Rekomendasi AI:")
                st.markdown(jawaban_ai)
                
                st.markdown("---")
                st.markdown(f"### 📋 Detail Kuliner yang Ditemukan ({len(warung_ditemukan)} tempat)")
                
                for w in warung_ditemukan:
                    status = w.get("status", "👍 Review Bagus")
                    if "Underrated" in status:
                        badge, bg = "💎 Underrated", "#F3E8FF"
                    elif "Hidden Gem" in status:
                        badge, bg = "⭐ Hidden Gem", "#DBEAFE"
                    elif "Legend" in status:
                        badge, bg = "🔥 Legend", "#FEF3C7"
                    elif "Viral" in status:
                        badge, bg = "📱 Viral", "#FEE2E2"
                    else:
                        badge, bg = "👍 Review Bagus", "#D1FAE5"
                    
                    gmaps_link = ""
                    lat = w.get('lat')
                    lon = w.get('lon')
                    alamat = w.get('alamat', w.get('lokasi', ''))
                    if lat and lon:
                        gmaps_link = f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" class="gmaps-link">🗺️ Buka di Google Maps</a>'
                    elif alamat and alamat != "Belum ada info":
                        alamat_encode = urllib.parse.quote(alamat)
                        gmaps_link = f'<a href="https://www.google.com/maps/search/?api=1&query={alamat_encode}" target="_blank" class="gmaps-link">🗺️ Buka di Google Maps</a>'
                    else:
                        query = f"{w['nama']} {w['lokasi']}"
                        gmaps_link = f'<a href="https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}" target="_blank" class="gmaps-link">🗺️ Buka di Google Maps</a>'
                    
                    st.markdown(f"""
                    <div style="background: {bg}; padding: 14px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid {bg};">
                        <b>{w['nama']}</b> <span style="background: {bg}; padding: 2px 10px; border-radius: 12px; font-size: 12px; border: 1px solid #ddd;">{badge}</span><br>
                        📍 {w['lokasi']} | 💰 {w['harga']} | ⭐ {w['rating']}<br>
                        📅 {w.get('jadwal_buka', w.get('jam_buka', 'Tidak ada info'))}<br>
                        📝 {w.get('review_warga', '')}<br>
                        {gmaps_link}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 🗺️ Peta Lokasi Kuliner")
                ada_koordinat = any(w.get('lat') and w.get('lon') for w in warung_ditemukan)
                if ada_koordinat:
                    try:
                        m = tampilkan_map(warung_ditemukan)
                        if m:
                            folium_static(m, width=700, height=400)
                    except:
                        st.info("📝 Tidak ada koordinat valid.")
                else:
                    st.info("📝 Belum ada koordinat. Tambahkan di Admin Panel.")
            else:
                st.warning("😔 Belum ada kuliner yang cocok.")
    elif submitted and not prompt_user:
        st.warning("⚠️ Tuliskan makanan yang kamu cari dulu ya!")

# ============================================
# TAB 2: REKOMENDASIKAN TEMPAT
# ============================================
with tab2:
    st.markdown("### ➕ Rekomendasikan Tempat Kuliner")
    st.info("📝 Bantu warga Ciledug menemukan tempat kuliner favoritmu! Data akan tersimpan permanen di Supabase Cloud.")
    with st.form("tambah_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("🏪 Nama Tempat *")
            lokasi = st.selectbox("📍 Lokasi *", WILAYAH_CILEDUG[1:])
            kategori = st.selectbox("🍽️ Kategori *", KATEGORI)
            alamat = st.text_input("📌 Alamat Lengkap *")
        with col2:
            harga = st.text_input("💰 Kisaran Harga *")
            jam = st.text_input("🕐 Jam Buka")
            jadwal = st.text_input("📅 Jadwal Buka Lengkap *")
            kontak = st.text_input("📞 Kontak")
            rating = st.slider("⭐ Rating", 1.0, 5.0, 4.0, 0.1)
        
        st.markdown("#### 🏷️ Status")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            s_underrated = st.checkbox("💎 Underrated (Enak, rating rendah)")
            s_hidden = st.checkbox("⭐ Hidden Gem (Enak, jarang diketahui)")
            s_legend = st.checkbox("🔥 Legend (Jualan > 10 tahun)")
        with col_s2:
            s_review = st.checkbox("👍 Review Bagus (Rating Google bagus)")
            s_viral = st.checkbox("📱 Viral (Lagi ramai medsos)")
        
        if s_underrated:
            status = "💎 Underrated"
        elif s_hidden:
            status = "⭐ Hidden Gem"
        elif s_legend:
            status = "🔥 Legend"
        elif s_review:
            status = "👍 Review Bagus"
        elif s_viral:
            status = "📱 Viral"
        else:
            status = "👍 Review Bagus"
        
        st.markdown("#### 🗺️ Koordinat (Opsional)")
        st.caption("Cari di Google Maps: Klik kanan lokasi → 'Koordinat'")
        col_lat, col_lon = st.columns(2)
        with col_lat:
            lat = st.text_input("Latitude", placeholder="-6.2186")
        with col_lon:
            lon = st.text_input("Longitude", placeholder="106.7012")
        
        kelebihan = st.text_area("✅ Kelebihan")
        kekurangan = st.text_area("❌ Kekurangan")
        review = st.text_area("💬 Review Warga")
        pengisi = st.text_input("👤 Nama Pengisi")
        
        submitted = st.form_submit_button("✅ Simpan", use_container_width=True)
        if submitted:
            if not nama or not lokasi or not kategori or not harga or not alamat or not jadwal:
                st.warning("⚠️ Isi semua field bertanda *")
            else:
                try:
                    lat_val = float(lat) if lat else None
                except:
                    lat_val = None
                try:
                    lon_val = float(lon) if lon else None
                except:
                    lon_val = None
                data_baru = {
                    "id": get_next_id(),
                    "nama": nama, "lokasi": lokasi, "kategori": kategori,
                    "harga": harga, "kelebihan": kelebihan or "Belum ada info",
                    "kekurangan": kekurangan or "Belum ada info", "rating": rating,
                    "status": status, "jam_buka": jam or jadwal, "jadwal_buka": jadwal,
                    "review_warga": review or "Belum ada review", "alamat": alamat,
                    "kontak": kontak or "-", "lat": lat_val, "lon": lon_val,
                    "ditambahkan_oleh": pengisi or "Warga Ciledug",
                    "tanggal_ditambahkan": datetime.now().strftime("%Y-%m-%d")
                }
                save_warung(data_baru)
                st.session_state.warung_ciledug = load_all_warung()
                st.success(f"✅ **{nama}** berhasil ditambahkan! Total kuliner: {len(st.session_state.warung_ciledug)}")
                st.balloons()

# ============================================
# TAB 3: ADMIN PANEL
# ============================================
with tab3:
    st.markdown("### 📋 Admin Panel - Kelola Data Kuliner")
    st.warning("⚠️ Perubahan akan tersimpan permanen di Supabase Cloud!")
    if not st.session_state.warung_ciledug:
        st.info("Belum ada data.")
    else:
        daftar_warung = [f"{w['id']}. {w['nama']} ({w['lokasi']})" for w in st.session_state.warung_ciledug]
        pilihan = st.selectbox("Pilih tempat kuliner:", daftar_warung)
        if pilihan:
            warung_id = int(pilihan.split('.')[0])
            warung = next((w for w in st.session_state.warung_ciledug if w["id"] == warung_id), None)
            if warung:
                st.markdown("---")
                st.markdown(f"### 📝 Edit: {warung['nama']}")
                with st.form("edit_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nama_edit = st.text_input("Nama", value=warung["nama"])
                        lokasi_edit = st.selectbox("Lokasi", WILAYAH_CILEDUG[1:], 
                                                   index=WILAYAH_CILEDUG[1:].index(warung["lokasi"]) if warung["lokasi"] in WILAYAH_CILEDUG[1:] else 0)
                        kategori_edit = st.selectbox("Kategori", KATEGORI,
                                                     index=KATEGORI.index(warung["kategori"]) if warung["kategori"] in KATEGORI else 0)
                        alamat_edit = st.text_input("Alamat", value=warung.get("alamat", ""))
                    with col2:
                        harga_edit = st.text_input("Harga", value=warung["harga"])
                        jam_edit = st.text_input("Jam Buka", value=warung.get("jam_buka", ""))
                        jadwal_edit = st.text_input("Jadwal Buka", value=warung.get("jadwal_buka", ""))
                        kontak_edit = st.text_input("Kontak", value=warung.get("kontak", ""))
                        rating_edit = st.slider("Rating", 1.0, 5.0, float(warung["rating"]), 0.1)
                    status_options = ["💎 Underrated", "⭐ Hidden Gem", "🔥 Legend", "👍 Review Bagus", "📱 Viral"]
                    status_edit = st.selectbox("Status", status_options, 
                                               index=status_options.index(warung["status"]) if warung["status"] in status_options else 3)
                    st.markdown("#### 🗺️ Koordinat")
                    col_lat2, col_lon2 = st.columns(2)
                    with col_lat2:
                        lat_edit = st.text_input("Latitude", value=str(warung.get('lat', '')) if warung.get('lat') else "")
                    with col_lon2:
                        lon_edit = st.text_input("Longitude", value=str(warung.get('lon', '')) if warung.get('lon') else "")
                    kelebihan_edit = st.text_area("Kelebihan", value=warung.get("kelebihan", ""))
                    kekurangan_edit = st.text_area("Kekurangan", value=warung.get("kekurangan", ""))
                    review_edit = st.text_area("Review Warga", value=warung.get("review_warga", ""))
                    col_save, col_delete = st.columns(2)
                    with col_save:
                        save_clicked = st.form_submit_button("💾 Simpan", use_container_width=True)
                    with col_delete:
                        delete_clicked = st.form_submit_button("🗑️ Hapus", use_container_width=True, type="secondary")
                    if save_clicked:
                        if not nama_edit or not lokasi_edit or not kategori_edit or not harga_edit:
                            st.warning("⚠️ Isi semua field penting!")
                        else:
                            try:
                                lat_val = float(lat_edit) if lat_edit else None
                            except:
                                lat_val = None
                            try:
                                lon_val = float(lon_edit) if lon_edit else None
                            except:
                                lon_val = None
                            warung["nama"] = nama_edit
                            warung["lokasi"] = lokasi_edit
                            warung["kategori"] = kategori_edit
                            warung["harga"] = harga_edit
                            warung["alamat"] = alamat_edit
                            warung["jam_buka"] = jam_edit
                            warung["jadwal_buka"] = jadwal_edit
                            warung["kontak"] = kontak_edit
                            warung["rating"] = rating_edit
                            warung["status"] = status_edit
                            warung["lat"] = lat_val
                            warung["lon"] = lon_val
                            warung["kelebihan"] = kelebihan_edit
                            warung["kekurangan"] = kekurangan_edit
                            warung["review_warga"] = review_edit
                            warung["ditambahkan_oleh"] = "Admin (Edited)"
                            warung["tanggal_ditambahkan"] = datetime.now().strftime("%Y-%m-%d")
                            save_warung(warung)
                            st.session_state.warung_ciledug = load_all_warung()
                            st.success("✅ Data berhasil diperbarui!")
                            st.rerun()
                    if delete_clicked:
                        confirm = st.checkbox("✅ Yakin hapus?")
                        if confirm:
                            delete_warung(warung_id)
                            st.session_state.warung_ciledug = load_all_warung()
                            st.success("🗑️ Tempat kuliner berhasil dihapus!")
                            st.rerun()

# ============================================
# 💰 DONASI
# ============================================
st.markdown("---")
st.markdown("""
    <div style="background: #FEF3C7; padding: 20px; border-radius: 12px; border: 1px solid #F59E0B; text-align: center;">
        <p style="font-weight: bold; color: #B45309; font-size: 16px;">❤️ Dukung Aplikasi Ini Tetap Gratis & Bebas Iklan</p>
        <p style="font-size: 13px; color: #78350F;">Aplikasi ini 100% gratis untuk warga Ciledug Raya. Kalau bermanfaat, traktir admin kopi ☕</p>
        <a href="https://trakteer.id/garda_digital" target="_blank" style="background: #F59E0B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">☕ Traktir Kopi di Trakteer</a>
    </div>
""", unsafe_allow_html=True)

st.markdown('<p class="footer">📦 Ramah HP | Dibuat dengan ❤️ oleh Garda Digital Indonesia untuk warga Ciledug Raya © 2026</p>', unsafe_allow_html=True)