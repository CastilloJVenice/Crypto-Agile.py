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
# We must set this before any other streamlit commands
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
# Inject custom CSS to force a dark theme and fix visibility issues
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Global Dark Mode Enforcement: Force text to be white and background dark */
    html, body, [class*="css"], .stMarkdown, label, p, h1, h2, h3, li {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
    }
    .stApp { background-color: #0e1117; }

    /* Sidebar Styling to match true dark theme */
    [data-testid="stSidebar"] { background-color: #111827 !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    /* THE EXPANDER FIX (Instruction Box in Dashboard) */
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

    /* DROPDOWN/SELECTBOX FIX (e.g., Device Type) */
    div[data-baseweb="select"] > div {
        background-color: #1f2937 !important;
        color: white !important;
        border: 1px solid #4b5563 !important;
    }
    /* Style the pop-over list items from the dropdown */
    div[data-baseweb="popover"] ul {
        background-color: #1f2937 !important;
        border: 1px solid #4b5563 !important;
    }
    div[data-baseweb="popover"] li {
        color: white !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #374151 !important;
    }

    /* LATENCY INPUT FIX: Force text to be white for visibility in Dark Mode */
    div[data-baseweb="input"] {
        background-color: #1f2937 !important;
        border: 1px solid #4b5563 !important;
        border-radius: 8px !important;
    }
    
    /* Target inputs and ensure number input text specifically is white */
    input[type="number"], div[data-baseweb="input"] input {
        color: #ffffff !important; /* Visible White Text */
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* BUTTONS STYLING */
    div.stButton > button {
        background-color: #7c3aed !important; /* Vibrant Purple Action Color */
        color: white !important;
        width: 100%;
        font-weight: 700 !important;
        border-radius: 8px !important;
        margin-top: -10px !important; /* Adjust positioning */
    }

    /* Target standard Streamlit metrics to use purple highlighting */
    [data-testid="stMetricValue"] {
        color: #a855f7 !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
    }

    /* Hide standard Streamlit elements like Deploy button and default footer */
    .stDeployButton, footer { display: none !important; }
    
    /* SIDEBAR TOGGLE (Chevron Arrow) visibility: Set color to faint light gray */
    [data-testid="stSidebarCollapse"] button[kind="headerNoContext"] svg,
    button[kind="headerNoContext"] svg {
        fill: rgba(255, 255, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE & UTILS
# =========================
# Initialize necessary session state variables if they don't exist
if "history" not in st.session_state: st.session_state.history = []
if "current_state" not in st.session_state: st.session_state.current_state = "classical"
if "streaming" not in st.session_state: st.session_state.streaming = False

# Initialize the simulated Cloud Service delay tracker
cloud_service = CloudService(service_name="API-Auth-Service", base_latency_ms=30, max_concurrent_requests=5)

def get_real_latency():
    """Utility function to measure actual network latency to Google."""
    try:
        # Check platform to use correct ping command parameters
        param = "-n" if platform.system().lower() == "windows" else "-c"
        # Run a single ping test to Google
        output = subprocess.check_output(f"ping {param} 1 google.com", shell=True, timeout=2).decode()
        # Parse the output to extract the 'time=' value
        return float(output.split("time=")[-1].split("ms")[0].strip()) if "time=" in output else random.uniform(20, 50)
    except:
        # Fallback jitter if ping fails
        return random.uniform(80, 150)

def generalize_client():
    """Utility function to categorize current hardware environment."""
    os_name = platform.system().lower()
    if os_name in ["windows", "darwin"]:
        return "desktop"
    elif os_name == "linux":
        return "server"
    else:
        return "mobile"

def process_request(sim_device, sim_latency, sim_security, is_manual=False):
    """
    Simulates sending an API request.
    Calculates the final latency, takes a snapshot of CPU usage, and calls the 'decide_suite' brain.
    """
    # 1. Simulate the raw processing time of the two types of encryption
    cls_res = run_classical_test(MESSAGE, sim_security)
    pqc_res = run_pqc_test(MESSAGE, sim_security)

    # 2. Network + Service Logic to calculate the FINAL simulated handshake latency
    base_latency = sim_latency
    # Simulate additional processing delay from the "Cloud Service"
    service_delay = cloud_service.process_request()['service_delay_ms']
    crypto_math_time = pqc_res['cpu_time_ms']
    # Add random network fluctuation (jitter)
    jitter = random.uniform(5, 20)
    
    # Final Simulated Latency = Raw network baseline + software overheads
    final_latency = base_latency + service_delay + crypto_math_time + jitter

    # 3. Decision Logic Snapshotting
    # Record current CPU utilization *just before* the main brain runs.
    # This snapshot (cpu_usage) is specifically for the Log Table display.
    # The brain itself ('decide_suite') will use a *fresh* psutil.cpu_percent() internally
    # when calculating its mathematical formula (SV Score).
    cpu_usage = psutil.cpu_percent()

    start_perf = time.perf_counter()
    # Call the actual "SV API" Decision Engine (Brain) with current system metrics.
    new_state, meta = decide_suite(st.session_state.current_state, sim_security, sim_device, final_latency)
    
    # 4. Watchdog Fail-Safe (Emergency Override)
    # Even if the brain likes PQC, if the absolute total latency exceeds 500ms, 
    # we force Classical crypto to ensure the system doesn't hang.
    if new_state == "pqc" and final_latency > 500:
        new_state = "classical"
        meta["reason"] = "Watchdog Override"
        # Since this wasn't the brain's original choice, we reset SV score tracking for this row.
        meta["sv_api"] = 0.0
        
    # Calculate how long the internal brain logic actually took to compute.
    exec_time_ms = (time.perf_counter() - start_perf) * 1000

    st.session_state.current_state = new_state
    algo = pqc_res['algorithm'] if new_state == "pqc" else cls_res['algorithm']
    
    return new_state, meta, algo, final_latency, exec_time_ms, cpu_usage

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Settings")
mode = st.sidebar.radio("Select System Mode",
                        ["Control Mode", "Simulation Mode", "Personal Mode", "Traffic Stream Mode"])

if mode == "Control Mode":
    device = st.sidebar.selectbox("Device Type", list(STUDY_CLIENTS.keys()))
    # LATENCY INPUT FIX: Aligned with Device Type width and white text color enforced via CSS
    latency_in = st.sidebar.number_input("Network Latency (ms)", 0, 5000, 150)
    
    # Locked Security Level display based on device choice
    security_in = STUDY_CLIENTS[device]
    st.sidebar.markdown(f"Locked Security Level: {security_in}")
    num_requests = 1
    
elif mode == "Simulation Mode":
    num_requests = st.sidebar.slider("Requests to Send", 1, 20, 5)
elif mode == "Personal Mode":
    num_requests = 1
else:
    stream_speed = st.sidebar.slider("Traffic Speed (sec)", 0.5, 3.0, 1.5)

# Separator before action bar
st.sidebar.markdown("---")

# MOVED ACTION BAR: Reset Button now right next to Process Request Button in sidebar
col_sid1, col_sid2 = st.sidebar.columns([2, 1])

# Column 1: Process Request Button (Handles all logic and updates history)
if col_sid1.button("Process Request"):
    batch = []
    # personal mode and control mode only send one request, but simulation mode can send a batch.
    for i in range(num_requests):
        # Gather inputs based on mode
        if mode == "Simulation Mode":
            # Generate random device, latency, and locked security level
            s_dev = random.choice(list(STUDY_CLIENTS.keys()))
            s_lat_in, s_sec = random.uniform(50, 500), STUDY_CLIENTS[s_dev]
            is_man = False
        elif mode == "Personal Mode":
            # Test actual local environment
            s_lat_in = get_real_latency()
            s_dev, s_sec = generalize_client(), STUDY_CLIENTS['desktop']
            is_man = False
        else:  # Control Mode: Locked to user manual inputs
            s_lat_in, s_dev, s_sec = latency_in, device, security_in
            is_man = True

        # Process the full handshake and get metrics
        new_st, meta, algo, f_lat, exec_ms, cpu_util = process_request(s_dev, s_lat_in, s_sec, is_manual=is_man)
        
        # Append all relevant metrics to the batch for this row.
        # This structure defines the Log Table columns.
        batch.append({
            "Req #": len(st.session_state.history) + i + 1, 
            "Device": s_dev, 
            "Input Latency": round(s_lat_in, 1),
            "Final Latency": round(f_lat, 1),
            "CPU %": cpu_util, # Snapshotted pre-brain snapshot
            "Sec": s_sec, 
            "Mode": new_st, 
            "Algorithm": algo, 
            "SV Score": round(meta["sv_api"], 3)
        })
        
    # Add new results to main history and refresh counters
    st.session_state.history.extend(batch)
    st.rerun()

# Column 2: Reset Button (Clears history only)
if col_sid2.button("Reset All Data"):
    st.session_state.history = []
    st.session_state.streaming = False
    st.rerun()

# =========================
# MAIN APP
# =========================
st.title("Crypto-Agile API Gateway")

tab_main, tab_about = st.tabs(["Dashboard", "System Info"])

# 1. Main Dashboard Tab
with tab_main:
    # Instructions Box at top (now standardized look)
    with st.expander(f"Instructions for {mode}", expanded=True):
        if mode == "Control Mode":
            st.info(f"Control Mode: Testing {device}. Manual baseline of {latency_in}ms sent to gateway.")
        elif mode == "Simulation Mode":
            st.info("Simulation Mode: Generates random users with security levels locked to their device type.")
        elif mode == "Personal Mode":
            st.info(f"Personal Mode: Testing local hardware. Security Level set to {STUDY_CLIENTS['desktop']}.")
        else:
            st.info("Traffic Stream Mode: A live HEARTBEAT of global requests.")

        st.markdown("### How does the system Think?")
        st.write("The system works like a Balance Scale:")
        col_lg1, col_lg2 = st.columns(2)
        with col_lg1:
            st.write("Side A: Performance")
            st.write("If the network is slow or the device is weak, the system uses Classical encryption because it's fast.")
        with col_lg2:
            st.write("Side B: Security")
            st.write("If the data is sensitive and the device is strong, the system uses PQC to protect against Quantum hackers.")
        st.write("The SV Score: This is the Weight. If the score is high, the scale tips toward PQC.")

    # Gateway active request counters using purple highlighing
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

    # Display Results / Log Table if history exists
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        # Sort latest at top for visibility
        df_display = df.sort_values("Req #", ascending=False)
        latest = df.iloc[-1]

        # Latest Decision Metrics
        st.subheader("Decision Insight")
        col_m1, col_m2 = st.columns([1, 2])

        # metric display using purple highlighting
        with col_m1:
            st.metric("Latest SV Score", latest["SV Score"])

        # Restored original detailed success/warning messages
        with col_m2:
            if latest["Mode"] == "pqc":
                st.success(f"Latest Decision: PQC Activated (Request #{latest['Req #']}). Security and latency optimal.")
            else:
                st.warning(f"Latest Decision: Classical Maintained (Request #{latest['Req #']}). Priority: Availability.")

        # Data Visualization Area
        st.markdown("### Activity Data")
        tab_table, tab_trend = st.tabs(["Log History", "View Trends"])
        
        # Log Table - sorting newest requests to the top
        with tab_table:
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Plotly graph for SV Score trends
        with tab_trend:
            fig = go.Figure()
            # Standard dataframe 'df' is chronologically sorted, perfect for a trend graph
            fig.add_trace(go.Scatter(x=df["Req #"], y=df["SV Score"], mode='lines+markers', line=dict(color='#a855f7', width=3)))
            # Transparent styling to blend with dashboard
            fig.update_layout(xaxis_title="Request Number (#)", yaxis_title="Security Value (SV Score)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=300)
            st.plotly_chart(fig, use_container_width=True)

# 2. System Info Tab - Full, preserved project descriptions
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
    # Preservation of the core math logic descriptions
    with col_a:
        st.subheader("The Agility Logic")
        st.write("Agility means being able to switch algorithms without stopping the system. We use an SV Score (Security Value) formula to decide when to switch.")

    with col_b:
        st.subheader("The Algorithms")
        st.markdown("""
        * Kyber (KEM): Used for key exchange.
        * Dilithium (Sig): Used for digital signatures.
        * ECDSA: The current standard for mobile and IoT.
        """)
