import streamlit as st
import time
import random
import pandas as pd
import plotly.graph_objects as go
import platform
import subprocess
import psutil

# IMPORT YOUR FRAMEWORK
from main3 import run_classical_test, run_pqc_test, MESSAGE
from switching import decide_suite, estimate_latency_ms_for_suite
from cloud_service import CloudService

# =========================
# CONFIG & STUDY DATA
# =========================
st.set_page_config(page_title="Crypto-Agile Simulator", layout="wide")

STUDY_CLIENTS = {
    'iot': 2,
    'mobile': 3,
    'desktop': 4,
    'server': 5
}

# =========================
# STYLE (VISIBILITY OVERHAUL)
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, label, p, h1, h2, h3, li {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }
    .stApp { background-color: #0e1117; }

    /* FIX: Sidebar Text Visibility */
    [data-testid="stSidebar"] { background-color: #111827 !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    /* FIX: Expander (Instructions) Visibility */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border-radius: 8px !important;
    }
    .streamlit-expanderHeader p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    .streamlit-expanderHeader svg { fill: #000000 !important; }

    /* FIX: Dropdowns (Selectbox) Container Visibility */
    div[data-baseweb="select"] > div {
        background-color: #1f2937 !important;
        color: white !important;
        border: 1px solid #4b5563 !important;
    }

    /* CRITICAL FIX: Dropdown List (The part that pops out) */
    /* This targets the floating popover to keep it dark */
    div[data-baseweb="popover"] ul {
        background-color: #1f2937 !important;
        border: 1px solid #4b5563 !important;
    }
    div[data-baseweb="popover"] li {
        color: white !important;
        background-color: #1f2937 !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #7c3aed !important;
    }

    /* FIX: Input Boxes (Latency) Visibility */
    div[data-baseweb="input"] {
        background-color: #1f2937 !important;
        border: 1px solid #4b5563 !important;
    }
    /* Force text color inside input for all browsers */
    input { 
        color: white !important; 
        -webkit-text-fill-color: white !important; 
    }

    /* FIX: Process Request Button Visibility */
    div.stButton > button {
        background-color: #7c3aed !important;
        color: white !important;
        border: 1px solid #9f67ff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        height: 3em !important;
    }

    /* FIX: Metric (SV Score) Visibility */
    [data-testid="stMetricValue"] {
        color: #a855f7 !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
    }

    .stDeployButton, footer, header {display: none !important;}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE & UTILS
# =========================
if "history" not in st.session_state: st.session_state.history = []
if "current_state" not in st.session_state: st.session_state.current_state = "classical"
if "streaming" not in st.session_state: st.session_state.streaming = False

cloud_service = CloudService(service_name="API-Auth-Service", base_latency_ms=30, max_concurrent_requests=5)


def get_real_latency():
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        output = subprocess.check_output(f"ping {param} 1 google.com", shell=True, timeout=2).decode()
        return float(output.split("time=")[-1].split("ms")[0].strip()) if "time=" in output else random.uniform(20, 50)
    except:
        return random.uniform(80, 150)


def generalize_client():
    os_name = platform.system().lower()
    return "desktop" if os_name in ["windows", "darwin"] else "server" if os_name == "linux" else "mobile"


def process_request(sim_device, sim_latency, sim_security, is_manual=False):
    cls_res = run_classical_test(MESSAGE, sim_security)
    pqc_res = run_pqc_test(MESSAGE, sim_security)

    if is_manual:
        final_latency = sim_latency
    else:
        base_pqc_size = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']
        base_latency = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=base_pqc_size)
        service_delay = cloud_service.process_request()['service_delay_ms']
        final_latency = base_latency + random.uniform(5, 20) + service_delay + pqc_res['cpu_time_ms']

    start_perf = time.perf_counter()
    new_state, meta = decide_suite(st.session_state.current_state, sim_security, sim_device, final_latency)
    exec_time_ms = (time.perf_counter() - start_perf) * 1000

    st.session_state.current_state = new_state
    algo = pqc_res['algorithm'] if new_state == "pqc" else cls_res['algorithm']
    return new_state, meta, algo, final_latency, exec_time_ms


# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Settings")
mode = st.sidebar.radio("Select System Mode",
                        ["Control Mode", "Simulation Mode", "Personal Mode", "Traffic Stream Mode"])
st.sidebar.markdown("---")

if mode == "Control Mode":
    device = st.sidebar.selectbox("Device Type", list(STUDY_CLIENTS.keys()))
    latency_in = st.sidebar.number_input("Network Latency (ms)", 0, 5000, 150)
    security_in = STUDY_CLIENTS[device]
    st.sidebar.markdown(f"**Locked Security Level:** {security_in}")
    num_requests = 1
elif mode == "Simulation Mode":
    num_requests = st.sidebar.slider("Requests to Send", 1, 20, 5)
elif mode == "Personal Mode":
    num_requests = 1
else:
    stream_speed = st.sidebar.slider("Traffic Speed (sec)", 0.5, 3.0, 1.5)

if st.sidebar.button("🗑️ Reset All Data"):
    st.session_state.history = []
    st.session_state.streaming = False
    st.rerun()

# =========================
# MAIN APP
# =========================
st.title("🛡️ Crypto-Agile API Gateway")

tab_main, tab_about = st.tabs(["🖥️ Dashboard", "ℹ️ System Info"])

with tab_main:
    # --- INSTRUCTIONS BOX ---
    with st.expander(f"📥 Instructions for {mode}", expanded=True):
        if mode == "Control Mode":
            st.info(
                f"🔧 **Control Mode:** You are testing the **{device}**. Your manual latency of **{latency_in}ms** will be sent directly to the gateway.")
        elif mode == "Simulation Mode":
            st.info("🎲 **Simulation Mode:** Generates random users with security levels locked to their device type.")
        elif mode == "Personal Mode":
            st.info(
                f"💻 **Personal Mode:** Testing your actual hardware. Security Level is set to **{STUDY_CLIENTS['desktop']}**.")
        else:
            st.info("🚀 **Traffic Stream Mode:** A live 'Heartbeat' of global requests.")

        st.markdown("### 🧠 How does the system 'Think'?")
        st.write("The system works like a **Balance Scale**:")
        col_lg1, col_lg2 = st.columns(2)
        with col_lg1:
            st.write("⚖️ **Side A: Performance**")
            st.write(
                "If the network is slow (High Latency) or the device is weak (IoT), the system uses **Classical** encryption because it's fast.")
        with col_lg2:
            st.write("🛡️ **Side B: Security**")
            st.write(
                "If the data is sensitive (High Security) and the device is strong (Server), the system uses **PQC** to protect against Quantum hackers.")
        st.write("🎯 **The SV Score:** This is the 'Weight'. If the score is high, the scale tips toward **PQC**.")

    st.subheader(f"Current State: :blue[{st.session_state.current_state.upper()}]")

    # --- ACTIONS ---
    if mode == "Traffic Stream Mode":
        c1, c2 = st.columns(2)
        if c1.button("▶️ Start Traffic"): st.session_state.streaming = True
        if c2.button("⏹️ Stop Traffic"): st.session_state.streaming = False

        placeholder = st.empty()
        while st.session_state.streaming:
            s_device = random.choice(list(STUDY_CLIENTS.keys()))
            s_lat = random.uniform(50, 500)
            s_sec = STUDY_CLIENTS[s_device]
            new_st, meta, algo, f_lat, exec_ms = process_request(s_device, s_lat, s_sec)
            st.session_state.history.append({
                "Req #": len(st.session_state.history) + 1, "Device": s_device, "Latency": round(f_lat, 1),
                "Sec": s_sec, "Mode": new_st, "Algorithm": algo, "SV Score": round(meta["sv_api"], 3)
            })
            df = pd.DataFrame(st.session_state.history)
            with placeholder.container():
                st.info(f"📡 **Incoming:** {s_device.upper()} → Authenticated via **{algo}**")
                st.dataframe(df.sort_values("Req #", ascending=False).head(8), use_container_width=True,
                             hide_index=True)
            time.sleep(stream_speed)
    else:
        if st.button("🚀 Process Request"):
            batch = []
            for i in range(num_requests):
                if mode == "Simulation Mode":
                    s_dev = random.choice(list(STUDY_CLIENTS.keys()))
                    s_lat, s_sec = random.uniform(50, 500), STUDY_CLIENTS[s_dev]
                    is_man = False
                elif mode == "Personal Mode":
                    s_dev, s_lat, s_sec = generalize_client(), get_real_latency(), STUDY_CLIENTS['desktop']
                    is_man = False
                else:  # Control Mode
                    s_dev, s_lat, s_sec = device, latency_in, security_in
                    is_man = True

                new_st, meta, algo, f_lat, exec_ms = process_request(s_dev, s_lat, s_sec, is_manual=is_man)
                batch.append({
                    "Req #": len(st.session_state.history) + i + 1, "Device": s_dev, "Latency": round(f_lat, 1),
                    "Sec": s_sec, "Mode": new_st, "Algorithm": algo, "SV Score": round(meta["sv_api"], 3)
                })
            st.session_state.history.extend(batch)

    # --- RESULTS ---
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        latest = df.iloc[-1]

        st.markdown("---")
        st.subheader("🧐 Decision Insight")
        col_m1, col_m2 = st.columns([1, 2])

        with col_m1:
            st.metric("Latest SV Score", latest["SV Score"])

        with col_m2:
            if latest["Mode"] == "pqc":
                st.success(
                    f"**PQC Activated (Request #{latest['Req #']})**\n\nThe security level for this {latest['Device']} is high enough and latency is manageable. The system has successfully deployed quantum-resistant encryption.")
            else:
                st.warning(
                    f"**Classical Maintained (Request #{latest['Req #']})**\n\nThe system prioritized availability. Given the latency of {latest['Latency']}ms, PQC would have caused a timeout or poor user experience.")

        st.subheader("📋 Log History")
        st.dataframe(df.sort_values("Req #", ascending=False), use_container_width=True, hide_index=True)

        with st.expander("📈 View Trends", expanded=False):
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=df["Req #"], y=df["SV Score"], mode='lines+markers', line=dict(color='#a855f7', width=3)))
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                              height=300)
            st.plotly_chart(fig, use_container_width=True)

with tab_about:
    st.header("🔐 About the Crypto-Agile Gateway")
    st.write("""
    This project demonstrates a next-generation security layer for API Gateways. 
    As we move toward the 'Quantum Era', computers will become powerful enough to break current encryption (RSA/ECC).
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("The Agility Logic")
        st.write(
            "Agility means being able to switch algorithms without stopping the system. We use an **SV Score (Security Value)** formula to decide when to switch.")

    with col_b:
        st.subheader("The Algorithms")
        st.markdown("""
        * **Kyber (KEM):** Used for key exchange.
        * **Dilithium (Sig):** Used for digital signatures.
        * **ECDSA:** The current standard for mobile and IoT.
        """)