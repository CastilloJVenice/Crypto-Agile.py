import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --------------------------------
# GLOBAL PLOT STYLE (THESIS READY)
# --------------------------------

plt.rcParams['font.family'] = 'Courier New'
plt.rcParams['text.color'] = 'black'
plt.rcParams['axes.labelcolor'] = 'black'
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'
plt.rcParams['axes.titlecolor'] = 'black'
plt.rcParams['font.weight'] = 'bold'

# --------------------------------
# SV_API MODEL
# --------------------------------

def sv_api(B, WR, WC, WL, Rquant, Pcost, Plat):
    return B + (WR * Rquant) - (WC * Pcost) - (WL * Plat)

# --------------------------------
# SIMULATION PARAMETERS
# --------------------------------

iterations = 1000
B = 0.5

# Random simulation inputs
Rquant_values = np.random.uniform(0.2, 1.0, iterations)
Plat_values = np.random.uniform(0.0, 1.0, iterations)
Pcost_values = np.random.uniform(0.0, 0.9, iterations)

# --------------------------------
# HYSTERESIS CONFIGURATIONS
# --------------------------------

hysteresis_tests = [
    (0.45, 0.55),
    (0.40, 0.60),
    (0.35, 0.65),
    (0.30, 0.70)
]

results = []

# --------------------------------
# CONTROL-THEORETIC TESTING LOOP
# --------------------------------

for LOWER, UPPER in hysteresis_tests:

    state = 0          # 0 = classical crypto
                       # 1 = PQC mode

    switches = 0
    pqc_count = 0

    for i in range(iterations):

        score = sv_api(
            B,
            1.0,
            0.4,
            0.4,
            Rquant_values[i],
            Pcost_values[i],
            Plat_values[i]
        )

        previous_state = state

        # hysteresis switching logic
        if state == 0 and score >= UPPER:
            state = 1

        elif state == 1 and score <= LOWER:
            state = 0

        # detect switching
        if state != previous_state:
            switches += 1

        if state == 1:
            pqc_count += 1

    oscillation_rate = switches / iterations
    pqc_ratio = pqc_count / iterations

    results.append({
        "Lower Threshold": LOWER,
        "Upper Threshold": UPPER,
        "Band Width": UPPER - LOWER,
        "Switch Count": switches,
        "Oscillation Rate": oscillation_rate,
        "PQC Activation Ratio": pqc_ratio
    })

# --------------------------------
# CREATE RESULTS TABLE
# --------------------------------

df = pd.DataFrame(results)

print("\nHysteresis Stability Test Results\n")
print(df)

# --------------------------------
# GRAPH 1: BAND WIDTH VS OSCILLATION
# --------------------------------

plt.figure(figsize=(8,5))

band_widths = df["Band Width"]
oscillation = df["Oscillation Rate"]

plt.plot(
    band_widths,
    oscillation,
    marker='o',
    linewidth=2.5,
    color='black'
)

plt.xlabel("Hysteresis Band Width")
plt.ylabel("Oscillation Rate")
plt.title("Effect of Hysteresis Band Width on Switching Stability")

plt.grid(True, linestyle=':', linewidth=0.7)

plt.savefig("hysteresis_band_stability.png", dpi=300, bbox_inches='tight')
plt.show()

# --------------------------------
# GRAPH 2: SWITCH COUNT COMPARISON
# --------------------------------

plt.figure(figsize=(8,5))

labels = [
    "0.45–0.55",
    "0.40–0.60",
    "0.35–0.65",
    "0.30–0.70"
]

switches = df["Switch Count"]

plt.bar(labels, switches, color='gray')

plt.xlabel("Hysteresis Threshold Pair")
plt.ylabel("Number of Mode Switches")
plt.title("Switching Stability Across Hysteresis Configurations")

plt.savefig("hysteresis_switching_comparison.png", dpi=300, bbox_inches='tight')
plt.show()