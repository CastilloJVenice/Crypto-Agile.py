import streamlit as st
import pandas as pd
import time
import altair as alt

# 1. Page Config (Dark Mode for "Cyber" feel)
st.set_page_config(
    page_title="Crypto-Agile Telemetry",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Sidebar Controls
with st.sidebar:
    st.header("⚡ Simulation Controls")
    st.markdown("Use these to stress-test the framework.")

    # These controls don't change code, but you can say
    # "I am setting the simulation parameters here"
    client_type = st.selectbox("Client Profile", ["IoT (Sensor)", "Banking (Server)", "Mobile"])
    jitter_level = st.slider("Inject Network Jitter (ms)", 0, 1000, 50)

    st.divider()
    st.info("Status: LISTENING TO CSV LOGS...")

# 3. Main Dashboard Title
st.title("🛡️ Quantum-Safe Migration Framework")
st.markdown("Real-time telemetry of **Algorithm Switching Logic ($SV_{API}$)**.")

# 4. Auto-Refresh Logic (Reads your CSV every 1 second)
placeholder = st.empty()

while True:
    try:
        # Read the CSV your simulation is writing to
        df = pd.read_csv('results.csv')

        # Get the latest transaction
        latest = df.iloc[-1]

        with placeholder.container():
            # --- SECTION A: HEADS UP DISPLAY ---
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            # Current Algorithm Mode
            state_color = "normal" if latest['new_state'] == 'pqc' else "off"
            kpi1.metric(
                label="Current Algorithm",
                value=latest['chosen_algorithm'],
                delta="Quantum Safe" if latest['new_state'] == 'pqc' else "Fallback Mode",
                delta_color=state_color
            )

            # Latency Metric
            latency = float(latest['final_latency'])
            kpi2.metric(
                label="Handshake Latency",
                value=f"{latency:.1f} ms",
                delta=f"{latency - 500:.1f} ms from Threshold",
                delta_color="inverse"  # Red if high, Green if low
            )

            # Jitter Metric
            kpi3.metric(
                label="Network Jitter",
                value=f"{float(latest['jitter_ms']):.1f} ms"
            )

            # SV_API Score
            score = float(latest['sv_score'])
            kpi4.metric(
                label="SV_API Stability Score",
                value=f"{score:.2f}",
                delta="Switching Threshold: 0.4 / 0.6"
            )

            st.divider()

            # --- SECTION B: THE LATENCY GRAPH (Objective 3) ---
            st.subheader("📊 Latency vs. Switching Threshold (500ms)")

            # Create a line chart with a threshold line
            chart_data = df[['run_id', 'final_latency', 'new_state']].tail(30)

            # Base Chart
            base = alt.Chart(chart_data).encode(x='run_id')

            # The Line (Latency)
            line = base.mark_line(strokeWidth=3).encode(
                y=alt.Y('final_latency', title='Latency (ms)'),
                color=alt.condition(
                    alt.datum.final_latency > 500,
                    alt.value('red'),  # If > 500, turn red
                    alt.value('#00FFAA')  # Else green
                )
            )

            # The Threshold Rule (The Red Line)
            rule = alt.Chart(pd.DataFrame({'y': [500]})).mark_rule(color='red', strokeDash=[5, 5]).encode(y='y')

            st.altair_chart(line + rule, use_container_width=True)

            # --- SECTION C: TRANSACTION LOG ---
            st.subheader("📜 Live Transaction Ledger")
            st.dataframe(
                df[['run_id', 'client', 'security_req', 'chosen_algorithm', 'decision_reason']].tail(5),
                use_container_width=True,
                hide_index=True
            )

        # Refresh every 1 second
        time.sleep(1)

    except Exception as e:
        st.warning("Waiting for simulation data... Run main3.py!")
        time.sleep(2)