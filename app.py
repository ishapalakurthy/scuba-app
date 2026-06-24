import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_searchbox import st_searchbox
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from datetime import date, datetime

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DB_PATH = "dives.db"

# ── Database ──────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS dives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, location TEXT NOT NULL,
        depth_m REAL NOT NULL, duration_min INTEGER NOT NULL,
        animals TEXT, notes TEXT, lat REAL, lon REAL)''')
    conn.commit(); conn.close()

def add_dive(d, loc, dep, dur, ani, notes, lat, lon):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO dives(date,location,depth_m,duration_min,animals,notes,lat,lon) VALUES(?,?,?,?,?,?,?,?)",
        (d, loc, dep, dur, ani, notes, lat, lon))
    conn.commit(); conn.close()

def update_dive(id_, d, loc, dep, dur, ani, notes, lat, lon):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE dives SET date=?,location=?,depth_m=?,duration_min=?,animals=?,notes=?,lat=?,lon=? WHERE id=?",
        (d, loc, dep, dur, ani, notes, lat, lon, id_))
    conn.commit(); conn.close()

def delete_dive(id_):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM dives WHERE id=?", (id_,))
    conn.commit(); conn.close()

def get_all_dives():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM dives ORDER BY date DESC", conn)
    conn.close()
    return df

def fmt_date(d):
    """Convert YYYY-MM-DD stored string to MM-DD-YYYY for display."""
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%m-%d-%Y")
    except Exception:
        return d

# ── Geocoding ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_location_suggestions(query: str):
    if len(query) < 2:
        return []
    try:
        geo = Nominatim(user_agent="scuba_logger_v2")
        results = geo.geocode(query, exactly_one=False, limit=6, timeout=10)
        if results:
            return [(r.address, (r.address, r.latitude, r.longitude)) for r in results]
    except GeocoderTimedOut:
        pass
    return []

# ── Session state ─────────────────────────────────────────────────────────────

if "editing_dive_id" not in st.session_state:
    st.session_state["editing_dive_id"] = None

# ── Searchbox style (ocean theme) ─────────────────────────────────────────────

SEARCHBOX_STYLES = {
    "wrapper": {"backgroundColor": "transparent"},
    "searchbox": {
        "control": {
            "backgroundColor": "rgba(10, 37, 64, 0.85)",
            "borderColor": "rgba(0, 212, 255, 0.3)",
            "borderRadius": "8px",
            "color": "#e0f2fe",
        },
        "menuList": {
            "backgroundColor": "#0a2540",
            "border": "1px solid rgba(0, 212, 255, 0.3)",
            "borderRadius": "8px",
        },
        "option": {
            "color": "#e0f2fe",
            "backgroundColor": "#0a2540",
            "highlightColor": "rgba(0, 212, 255, 0.18)",
        },
        "singleValue": {"color": "#e0f2fe"},
        "input":       {"color": "#e0f2fe"},
        "placeholder": {"color": "#7dd3fc"},
    },
}

# ── Page config & CSS ─────────────────────────────────────────────────────────

st.set_page_config(page_title="Scuba Dive Log", page_icon="🤿", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Inter', sans-serif !important;
}
h1, h2, h3, h4, .big-title {
    font-family: 'Playfair Display', serif !important;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #020c1b 0%, #0a2540 60%, #0c3b5e 100%);
}
[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; }
[data-testid="stSidebar"] { background: rgba(2,18,40,.85); }
h1,h2,h3,label,p,span,div { color: #e0f2fe !important; }
.big-title {
    text-align: center; font-size: 3rem; font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #00e5ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle {
    text-align: center; color: #7dd3fc !important;
    font-size: 1.1rem; margin-top: 4px; margin-bottom: 1.5rem;
}
.stat-box {
    background: rgba(0,180,255,.08);
    border: 1px solid rgba(0,212,255,.25);
    border-radius: 14px; padding: 18px 10px; text-align: center;
}
.stat-num { font-size: 2rem; font-weight: 700; color: #38bdf8 !important; }
.stat-lbl { font-size: .82rem; color: #93c5fd !important; }
.stTabs [data-baseweb="tab"] { font-size: 1rem; color: #7dd3fc !important; }
.stTabs [aria-selected="true"] { color: #00e5ff !important; border-bottom: 2px solid #00e5ff; }
:root [data-testid="baseButton-primary"] {
    background: linear-gradient(90deg, #0ea5e9, #0284c7) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
}
:root [data-testid="baseButton-primary"]:hover { opacity: .85 !important; }

button[kind="secondary"] {
    background-color: transparent !important;
    border: none !important;
    color: white !important;
    box-shadow: none !important;
    padding: 0 !important;
}
button[kind="secondary"]:hover {
    background-color: transparent !important;
    border: none !important;
}
input, textarea {
    background: rgba(2,18,40,.6) !important;
    color: #e0f2fe !important;
    border-color: rgba(0,212,255,.3) !important;
}
div[data-baseweb="select"] { background: rgba(2,18,40,.6) !important; }
div[data-baseweb="select"] span { color: #e0f2fe !important; }
.col-header { font-size: .78rem; font-weight: 700; color: #7dd3fc !important;
              text-transform: uppercase; letter-spacing: .05em; }
.dive-row { font-size: .93rem; padding: 2px 0; }
.edit-panel {
    background: rgba(0, 120, 180, 0.12);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 12px; padding: 20px 18px; margin: 6px 0 10px 0;
}
.loc-badge {
    background: rgba(0,212,255,.10); border: 1px solid rgba(0,212,255,.3);
    border-radius: 8px; padding: 7px 12px; font-size: .88rem; margin-bottom: 10px;
}
</style>""", unsafe_allow_html=True)

init_db()

# ── JS: strip dark box from secondary buttons after every Streamlit render ────
# CSS can't reliably override Streamlit's emotion-cache styles; inline styles can.
components.html("""
<script>
(function () {
    function fix() {
        const doc = window.parent.document;
        doc.querySelectorAll('[data-testid="baseButton-secondary"]').forEach(btn => {
            ['background','background-color','border','box-shadow','outline'].forEach(p =>
                btn.style.setProperty(p, 'transparent' === p || p==='background-color' ? 'transparent'
                    : p==='border'||p==='box-shadow'||p==='outline' ? 'none' : 'transparent', 'important'));
            btn.style.setProperty('background',       'transparent', 'important');
            btn.style.setProperty('background-color', 'transparent', 'important');
            btn.style.setProperty('border',           'none',        'important');
            btn.style.setProperty('box-shadow',       'none',        'important');
            btn.style.setProperty('outline',          'none',        'important');
            btn.style.setProperty('padding',          '2px 4px',     'important');
            btn.querySelectorAll('div').forEach(d => {
                d.style.setProperty('background',       'transparent', 'important');
                d.style.setProperty('background-color', 'transparent', 'important');
                d.style.setProperty('border',           'none',        'important');
                d.style.setProperty('box-shadow',       'none',        'important');
                d.style.setProperty('border-radius',    '0',           'important');
            });
            const p = btn.querySelector('p');
            if (p) {
                p.style.setProperty('filter',    'grayscale(1) brightness(10)', 'important');
                p.style.setProperty('color',     'white',  'important');
                p.style.setProperty('margin',    '0',      'important');
                p.style.setProperty('font-size', '1.1rem', 'important');
            }
        });
    }
    fix();
    new MutationObserver(fix).observe(window.parent.document.body,
        { childList: true, subtree: true });
})();
</script>
""", height=0, scrolling=False)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<div class="big-title">🤿 Scuba Dive Log</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Track your underwater adventures around the world</div>', unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────

df = get_all_dives()
n = len(df)

c1, c2, c3, c4 = st.columns(4)
for col, num, lbl in [
    (c1, n, "Total Dives"),
    (c2, f"{df['depth_m'].max():.0f} m" if n else "—", "Max Depth"),
    (c3, f"{int(df['duration_min'].sum())} min" if n else "0 min", "Time Underwater"),
    (c4, df['location'].nunique() if n else 0, "Unique Locations"),
]:
    col.markdown(
        f'<div class="stat-box"><div class="stat-num">{num}</div><div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_map, tab_log, tab_add = st.tabs(["🗺️  World Map", "📋  Dive Log", "➕  Log a Dive"])

# ─── World Map ────────────────────────────────────────────────────────────────
with tab_map:
    st.markdown("### Dive Locations")
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    mapped = df.dropna(subset=["lat", "lon"]) if n else pd.DataFrame()
    for _, row in mapped.iterrows():
        animals = row["animals"] or "None recorded"
        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:210px;color:#111;">
            <h4 style="margin:0 0 8px;color:#005f99;">🤿 {row['location']}</h4>
            <p style="margin:4px 0;"><b>📅 Date:</b> {fmt_date(row['date'])}</p>
            <p style="margin:4px 0;"><b>⬇️ Depth:</b> {row['depth_m']} m</p>
            <p style="margin:4px 0;"><b>⏱ Duration:</b> {row['duration_min']} min</p>
            <p style="margin:4px 0;"><b>🐠 Animals:</b> {animals}</p>
            {"<p style='margin:4px 0;'><b>📝 Notes:</b> " + row['notes'] + "</p>" if row['notes'] else ""}
        </div>"""
        folium.CircleMarker(
            location=[row["lat"], row["lon"]], radius=10,
            color="#00e5ff", fill=True, fill_color="#0284c7", fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"🤿 {row['location']}  |  {row['depth_m']} m  |  {row['duration_min']} min",
        ).add_to(m)
    st_folium(m, use_container_width=True, height=520)
    if n and len(mapped) < n:
        st.info(f"{n - len(mapped)} dive(s) have no coordinates and aren't shown on the map.")
    if not n:
        st.info("No dives yet — log your first dive in the ➕ tab!")

# ─── Dive Log ─────────────────────────────────────────────────────────────────
with tab_log:
    st.markdown("### All Logged Dives")
    if not n:
        st.info("No dives logged yet.")
    else:
        # Column header row
        COL_W = [1.6, 2.6, 1, 1.2, 2.4, 0.35, 0.35]
        h = st.columns(COL_W)
        for col, label in zip(h, ["Date", "Location", "Depth", "Duration", "Animals Seen", "", ""]):
            col.markdown(f'<div class="col-header">{label}</div>', unsafe_allow_html=True)
        st.divider()

        for _, row in df.iterrows():
            dive_id    = int(row["id"])
            is_editing = st.session_state["editing_dive_id"] == dive_id

            # ── Data row ──────────────────────────────────────────────────────
            cols = st.columns(COL_W)
            cols[0].markdown(f'<div class="dive-row">{fmt_date(row["date"])}</div>', unsafe_allow_html=True)
            loc_display = row["location"][:38] + ("…" if len(row["location"]) > 38 else "")
            cols[1].markdown(f'<div class="dive-row">{loc_display}</div>', unsafe_allow_html=True)
            cols[2].markdown(f'<div class="dive-row">{row["depth_m"]} m</div>', unsafe_allow_html=True)
            cols[3].markdown(f'<div class="dive-row">{int(row["duration_min"])} min</div>', unsafe_allow_html=True)
            cols[4].markdown(f'<div class="dive-row">{row["animals"] or "—"}</div>', unsafe_allow_html=True)

            with cols[5]:
                if st.button("✎", key=f"edit_btn_{dive_id}", help="Edit this dive"):
                    if is_editing:
                        st.session_state["editing_dive_id"] = None
                    else:
                        prev = st.session_state["editing_dive_id"]
                        if prev and f"edit_sb_{prev}" in st.session_state:
                            del st.session_state[f"edit_sb_{prev}"]
                        st.session_state["editing_dive_id"] = dive_id
                    st.rerun()

            with cols[6]:
                if st.button("✕", key=f"del_btn_{dive_id}", help="Delete this dive"):
                    delete_dive(dive_id)
                    if st.session_state["editing_dive_id"] == dive_id:
                        st.session_state["editing_dive_id"] = None
                    st.rerun()

            # ── Inline edit panel ─────────────────────────────────────────────
            if is_editing:
                st.markdown('<div class="edit-panel">', unsafe_allow_html=True)

                st.markdown(
                    f'<div class="loc-badge">📍 Current location: <b>{row["location"][:80]}</b></div>',
                    unsafe_allow_html=True)

                edit_loc = st_searchbox(
                    fetch_location_suggestions,
                    key=f"edit_sb_{dive_id}",
                    placeholder="Type to change location (leave blank to keep current)…",
                    label="Change Location",
                    debounce=350,
                    style_overrides=SEARCHBOX_STYLES,
                )

                ec1, ec2 = st.columns(2)
                with ec1:
                    e_date   = st.date_input("Date",
                                              value=pd.to_datetime(row["date"]).date(),
                                              key=f"e_date_{dive_id}")
                    e_depth  = st.number_input("Max Depth (m)", min_value=0.0, max_value=350.0,
                                                value=float(row["depth_m"]), step=0.5,
                                                key=f"e_depth_{dive_id}")
                with ec2:
                    e_dur    = st.number_input("Duration (min)", min_value=1, max_value=300,
                                                value=int(row["duration_min"]),
                                                key=f"e_dur_{dive_id}")
                    e_animals = st.text_input("Animals Seen", value=row["animals"] or "",
                                               key=f"e_ani_{dive_id}")
                e_notes = st.text_area("Notes", value=row["notes"] or "", height=75,
                                        key=f"e_notes_{dive_id}")

                sv_col, cx_col = st.columns(2)
                with sv_col:
                    if st.button("💾 Save Changes", key=f"save_{dive_id}", use_container_width=True, type="primary"):
                        if edit_loc:
                            loc_name, lat, lon = edit_loc
                        else:
                            loc_name, lat, lon = row["location"], row["lat"], row["lon"]
                        update_dive(dive_id, str(e_date), loc_name, e_depth,
                                    e_dur, e_animals, e_notes, lat, lon)
                        st.session_state["editing_dive_id"] = None
                        st.rerun()
                with cx_col:
                    if st.button("✕ Cancel", key=f"cancel_{dive_id}", use_container_width=True):
                        st.session_state["editing_dive_id"] = None
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

            st.divider()

# ─── Log a Dive ───────────────────────────────────────────────────────────────
with tab_add:
    st.markdown("### Log a New Dive")

    log_loc = st_searchbox(
        fetch_location_suggestions,
        key="log_searchbox",
        placeholder="Start typing a location…",
        label="Location",
        debounce=350,
        clear_on_submit=False,
        style_overrides=SEARCHBOX_STYLES,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        log_date    = st.date_input("Date", value=date.today(), key="log_date")
        log_depth   = st.number_input("Max Depth (m)", min_value=0.0, max_value=350.0,
                                       value=18.0, step=0.5, key="log_depth")
    with col_b:
        log_dur     = st.number_input("Duration (minutes)", min_value=1, max_value=300,
                                       value=45, key="log_dur")
        log_animals = st.text_input("Animals Seen",
                                     placeholder="e.g. sea turtle, manta ray, clownfish",
                                     key="log_animals")
    log_notes = st.text_area("Notes", placeholder="Visibility, water temp, conditions…",
                               height=90, key="log_notes")

    if st.button("🤿 Log This Dive", use_container_width=True, key="log_submit", type="primary"):
        if not log_loc:
            st.error("Please type and select a location from the dropdown first.")
        else:
            loc_name, lat, lon = log_loc
            add_dive(str(log_date), loc_name, log_depth, log_dur,
                     log_animals, log_notes, lat, lon)
            st.success("✅ Dive logged and pinned to the map!")
            st.rerun()
