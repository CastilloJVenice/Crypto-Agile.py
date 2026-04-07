import numpy as np
import matplotlib.pyplot as plt
import random

# ===============================
# CONFIGURATION
# ===============================

BASE_SCORE = 0.5
WR = 1.0
WC = 0.4
WL = 0.4

THRESHOLD_HIGH = 0.6
THRESHOLD_LOW = 0.4

SIMULATION_STEPS = 30

# Device Profiles
DEVICE_PROFILES = {
    "IoT": 0.9,
    "Mobile": 0.5,
    "Server": 0.0
}

# ===============================
# SV_API SIMULATION
# ===============================

def run_simulation(device_type="Mobile",
                   wr=WR, wc=WC, wl=WL):

    sv_api_list = []
    mode_list = []

    current_mode = "Classical"
    pcost = DEVICE_PROFILES[device_type]

    for t in range(SIMULATION_STEPS):

        # Simulated NIST security level (1–5)
        risk_level = random.randint(1, 5)
        rquant = risk_level / 5.0

        # Simulated latency (0–500 ms)
        latency = random.uniform(50, 500)
        plat = latency / 500

        # SV_API formula
        sv_api = BASE_SCORE + (wr * rquant) - (wc * pcost) - (wl * plat)

        sv_api_list.append(sv_api)

        # Hysteresis switching
        if current_mode == "Classical" and sv_api >= THRESHOLD_HIGH:
            current_mode = "PQC"
        elif current_mode == "PQC" and sv_api <= THRESHOLD_LOW:
            current_mode = "Classical"

        mode_list.append(current_mode)

    return {
        "sv_api": sv_api_list,
        "mode": mode_list
    }

# ===============================
# CONTROL THEORY VISUALIZATION
# ===============================

def plot_sv_api_with_thresholds(results):
    plt.figure()
    plt.plot(results["sv_api"])
    plt.axhline(THRESHOLD_HIGH)
    plt.axhline(THRESHOLD_LOW)
    plt.xlabel("Time Step")
    plt.ylabel("SV_API Score")
    plt.title("SV_API with Hysteresis Thresholds")
    plt.show()

def plot_switching_state(results):
    mode_numeric = [1 if m == "PQC" else 0 for m in results["mode"]]

    plt.figure()
    plt.step(range(len(mode_numeric)), mode_numeric)
    plt.xlabel("Time Step")
    plt.ylabel("Mode (1 = PQC, 0 = Classical)")
    plt.title("Cryptographic Mode Switching Timeline")
    plt.show()

# ===============================
# SENSITIVITY ANALYSIS
# ===============================

def sensitivity_analysis(device_type="Mobile"):
    security_weights = np.linspace(0.6, 1.4, 15)
    pqc_activation_percent = []

    for w in security_weights:
        results = run_simulation(device_type=device_type,
                                 wr=w, wc=WC, wl=WL)

        pqc_count = results["mode"].count("PQC")
        percent_active = pqc_count / len(results["mode"]) * 100

        pqc_activation_percent.append(percent_active)

    plt.figure()
    plt.plot(security_weights, pqc_activation_percent)
    plt.xlabel("Security Weight (WR)")
    plt.ylabel("PQC Activation Percentage")
    plt.title("Sensitivity Analysis of Security Weight")
    plt.show()

# ===============================
# TORNADO ANALYSIS
# ===============================

def tornado_analysis(device_type="Mobile"):
    base_results = run_simulation(device_type)
    base_switches = base_results["mode"].count("PQC")

    variations = {
        "WR +20%": (WR * 1.2, WC, WL),
        "WC +20%": (WR, WC * 1.2, WL),
        "WL +20%": (WR, WC, WL * 1.2),
    }

    impacts = []

    for label, (wr, wc, wl) in variations.items():
        result = run_simulation(device_type, wr, wc, wl)
        switches = result["mode"].count("PQC")
        impacts.append(switches - base_switches)

    plt.figure()
    plt.barh(list(variations.keys()), impacts)
    plt.xlabel("Change in PQC Activations")
    plt.title("Tornado Sensitivity Analysis")
    plt.show()

# ===============================
# MAIN EXECUTION
# ===============================

if __name__ == "__main__":

    results = run_simulation(device_type="Mobile")

    plot_sv_api_with_thresholds(results)
    plot_switching_state(results)

    sensitivity_analysis(device_type="Mobile")
    tornado_analysis(device_type="Mobile")