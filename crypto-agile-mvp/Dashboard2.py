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
    'desktop': 3,
    'server': 5
}

# =========================
# STYLE
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Global Dark Mode */
    html, body, [class*="css"], .stMarkdown, label, p, h1, h2, h3, li {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }
    .stApp { background-color: #0e1117; }

    /* Sidebar Fix */
    [data-testid="stSidebar"] { background-color: #111827 !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    /* HIDE SIDEBAR CONTROLS */
    [data-testid="sidebar-collapsed-control"], button[kind="headerNoContext"] {
        display: none !important;
    }
    header { display: none !important; }

    /* EXPANDER FIX */
    [data-testid="stExpander"] {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #1f2937 !important;
        color: white !important;
    }
    [data-testid="stExpander"] summary:hover {
        background-color: #2d3748 !important;
    }
    [data-testid="stExpander"] summary p {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* DROPDOWN/SELECTBOX FIX */
    div[data-baseweb="select"] > div {
        background-color: #1f2937 !important;
        color: white !important;
        border: 1px solid #4b5563 !important;
    }

    div[data-baseweb="popover"] ul {
        background-color: #1f2937 !important;
        border: 1px solid #4b5563 !important;
    }
    div[data-baseweb="popover"] li {
        background-color: #1f2937 !important;
        color: white !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #7c3aed !important;
        color: white !important;
    }

    /* LATENCY INPUT FIX */
    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1px solid #4b5563 !important;
    }
    input[type="number"], div[data-baseweb="input"] input {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 600 !important;
    }

    /* BUTTONS */
    div.stButton > button {
        background-color: #7c3aed !important;
        color: white !important;
        width: 100%;
        margin-top: -10px !important;
    }

    [data-testid="stMetricValue"] {
        color: #a855f7 !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
    }

    .stDeployButton, footer {display: none !important;}
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

    # NEW CONSISTENT LOGIC:
    # We treat 'sim_latency' as the network baseline for EVERY mode.
    base_latency = sim_latency

    # Calculate handshake overhead
    service_delay = cloud_service.process_request()['service_delay_ms']
    crypto_math_time = pqc_res['cpu_time_ms']
    jitter = random.uniform(5, 20)

    # Final Latency = Network + Service + Crypto + Jitter
    final_latency = base_latency + service_delay + crypto_math_time + jitter

    # Decision Engine (The "Brain")
    start_perf = time.perf_counter()
    new_state, meta = decide_suite(st.session_state.current_state, sim_security, sim_device, final_latency)

    # Watchdog
    if new_state == "pqc" and final_latency > 500:
        new_state = "classical"
        meta["reason"] = "Watchdog Override"
        meta["sv_api"] = 0.0

    exec_time_ms = (time.perf_counter() - start_perf) * 1000
    st.session_state.current_state = new_state
    algo = pqc_res['algorithm'] if new_state == "pqc" else cls_res['algorithm']
    cpu_util = psutil.cpu_percent()

    return new_state, meta, algo, final_latency, exec_time_ms, cpu_util


# =========================
# SIDEBAR
# =========================
st.sidebar.header("Settings")
mode = st.sidebar.radio("Select System Mode",
                        ["Control Mode", "Simulation Mode", "Personal Mode", "Traffic Stream Mode"])

if mode == "Control Mode":
    device = st.sidebar.selectbox("Device Type", list(STUDY_CLIENTS.keys()))
    latency_in = st.sidebar.number_input("Network Latency (ms)", 0, 5000, 150)

    # MOVED TO DROPDOWN (EXPANDER) UNDER INPUT
    with st.sidebar.expander("Latency Threshold Interpretation", expanded=False):
        st.write("""
        - 0-100 ms: Optimal (Fast and stable)
        - 101-200 ms: Acceptable (Normal operation)
        - 201-500 ms: Degraded (Performance drop)
        - \\>500 ms: Critical (Fail-safe active)
        """)

    security_in = STUDY_CLIENTS[device]
    st.sidebar.markdown(f"Locked Security Level: {security_in}")
    num_requests = 1

elif mode == "Simulation Mode":
    num_requests = st.sidebar.slider("Requests to Send", 1, 20, 5)
elif mode == "Personal Mode":
    num_requests = 1
else:
    stream_speed = st.sidebar.slider("Traffic Speed (sec)", 0.5, 3.0, 1.5)

# SIDEBAR ACTIONS
if mode == "Traffic Stream Mode":
    if not st.session_state.streaming:
        if st.sidebar.button("Start Traffic"): st.session_state.streaming = True
    else:
        if st.sidebar.button("Stop Traffic"): st.session_state.streaming = False
else:
    if st.sidebar.button("Process Request"):
        batch = []
        for i in range(num_requests):
            if mode == "Simulation Mode":
                s_dev = random.choice(list(STUDY_CLIENTS.keys()))
                s_lat_in, s_sec = random.uniform(50, 500), STUDY_CLIENTS[s_dev]
                is_man = False
            elif mode == "Personal Mode":
                s_lat_in = get_real_latency()
                s_dev, s_sec = generalize_client(), STUDY_CLIENTS['desktop']
                is_man = False
            else:  # Control Mode
                s_lat_in, s_dev, s_sec = latency_in, device, security_in
                is_man = True

            new_st, meta, algo, f_lat, exec_ms, cpu_util = process_request(s_dev, s_lat_in, s_sec, is_manual=is_man)
            batch.append({
                "Req #": len(st.session_state.history) + i + 1,
                "Device": s_dev,
                "Input Latency": round(s_lat_in, 1),
                "Final Latency": round(f_lat, 1),
                "CPU %": cpu_util,
                "Sec": s_sec,
                "Mode": new_st,
                "Algorithm": algo,
                "SV Score": round(meta["sv_api"], 3)
            })
        st.session_state.history.extend(batch)
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Reset All Data"):
    st.session_state.history = []
    st.session_state.streaming = False
    st.rerun()

# =========================
# MAIN APP
# =========================
st.title("Crypto-Agile API Gateway")

tab_main, tab_about = st.tabs(["Dashboard", "System Info"])

with tab_main:
    # --- INSTRUCTIONS BOX ---
    with st.expander(f"Instructions for {mode}", expanded=True):
        if mode == "Control Mode":
            st.info(
                f"Control Mode: You are testing the {device}. Your manual latency of {latency_in}ms will be sent directly to the gateway.")
        elif mode == "Simulation Mode":
            st.info("Simulation Mode: Generates random users with security levels locked to their device type.")
        elif mode == "Personal Mode":
            st.info(
                f"Personal Mode: Testing your actual hardware. Security Level is set to {STUDY_CLIENTS['desktop']}.")
        else:
            st.info("Traffic Stream Mode: A live heartbeat of global requests.")

        st.markdown("### How does the system Think?")
        st.write("The system works like a Balance Scale:")
        col_lg1, col_lg2 = st.columns(2)
        with col_lg1:
            st.write("Side A: Performance")
            st.write(
                "If the network is slow (High Latency) or the device is weak (IoT), the system uses Classical encryption because it's fast.")
        with col_lg2:
            st.write("Side B: Security")
            st.write(
                "If the data is sensitive (High Security) and the device is strong (Server), the system uses PQC to protect against Quantum hackers.")
        st.write("The SV Score: This is the Weight. If the score is high, the scale tips toward PQC.")

    # --- LIVE GATEWAY STATUS COUNTERS ---
    st.markdown("### Live Gateway Status")

    if st.session_state.history:
        hist_df = pd.DataFrame(st.session_state.history)
        pqc_count = len(hist_df[hist_df["Mode"] == "pqc"])
        classical_count = len(hist_df[hist_df["Mode"] == "classical"])
    else:
        pqc_count, classical_count = 0, 0

    c_stat1, c_stat2 = st.columns(2)
    with c_stat1:
        st.metric("PQC Active Requests", pqc_count)
    with c_stat2:
        st.metric("Classical Active Requests", classical_count)

    st.markdown("---")

    # Handle Background Streaming
    if st.session_state.streaming and mode == "Traffic Stream Mode":
        s_device = random.choice(list(STUDY_CLIENTS.keys()))
        s_lat_in = random.uniform(50, 500)
        s_sec = STUDY_CLIENTS[s_device]
        new_st, meta, algo, f_lat, exec_ms, cpu_util = process_request(s_device, s_lat_in, s_sec)
        st.session_state.history.append({
            "Req #": len(st.session_state.history) + 1,
            "Device": s_device,
            "Input Latency": round(s_lat_in, 1),
            "Final Latency": round(f_lat, 1),
            "CPU %": cpu_util,
            "Sec": s_sec,
            "Mode": new_st,
            "Algorithm": algo,
            "SV Score": round(meta["sv_api"], 3)
        })
        time.sleep(stream_speed)
        st.rerun()

    # --- RESULTS ---
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        latest = df.iloc[-1]

        st.subheader("Decision Insight")
        col_m1, col_m2 = st.columns([1, 2])

        with col_m1:
            st.metric("Latest SV Score", latest["SV Score"])

        with col_m2:
            if latest["Mode"] == "pqc":
                st.success(
                    f"Latest Decision: PQC Activated (Request #{latest['Req #']})\n\nThe security level for this {latest['Device']} device is high enough and latency is manageable.")
            else:
                st.warning(
                    f"Latest Decision: Classical Maintained (Request #{latest['Req #']})\n\nThe system prioritized availability due to {latest['Final Latency']}ms final latency.")

        st.markdown("### Activity Data")
        tab_table, tab_trend = st.tabs(["Log History", "View Trends"])

        with tab_table:
            st.dataframe(df.sort_values("Req #", ascending=False), use_container_width=True, hide_index=True)

        with tab_trend:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=df["Req #"], y=df["SV Score"], mode='lines+markers', line=dict(color='#a855f7', width=3)))
            fig.update_layout(
                xaxis_title="Request Number (#)",
                yaxis_title="Security Value (SV Score)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

with tab_about:
    st.header("About the Crypto-Agile Gateway")
    st.write("""
    This project demonstrates a next-generation security layer for API Gateways.
As we move toward the 'Quantum Era', computers will become powerful enough to break current encryption (RSA/ECC),
making traditional security approaches unreliable. To address this, the system explores quantum-resistant cryptographic algorithms, such as lattice-based encryption,
which are designed to withstand attacks from quantum computers. By integrating these advanced techniques into API Gateway infrastructure,
the project aims to ensure long-term data protection, secure communication, and future-proof defenses against emerging computational threats.
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("The Agility Logic")
        st.write(
            "Agility means being able to switch algorithms without stopping the system. We use an **SV Score (Security Value)** formula to decide when to switch.")

    with col_b:
        st.subheader("The Algorithms")
        st.markdown("""
        * Kyber (KEM): Used for key exchange.
        * Dilithium (Sig): Used for digital signatures.
        * ECDSA: The current standard for mobile and IoT.
        """)