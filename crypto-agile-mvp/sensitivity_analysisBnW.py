import numpy as np
import matplotlib.pyplot as plt

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

B = 0.5
iterations = 1000

Rquant_values = np.random.uniform(0.2, 1.0, iterations)
Plat_values = np.random.uniform(0.0, 1.0, iterations)
Pcost_values = np.random.uniform(0.0, 0.9, iterations)

UPPER = 0.6
LOWER = 0.4

# --------------------------------
# PARAMETER SWEEP
# --------------------------------

weight_range = np.linspace(0, 1.5, 40)

wr_activation = []
wc_activation = []
wl_activation = []

for w in weight_range:

    pqc_count = 0
    for i in range(iterations):

        score = sv_api(B, w, 0.4, 0.4,
                       Rquant_values[i],
                       Pcost_values[i],
                       Plat_values[i])

        if score >= UPPER:
            pqc_count += 1

    wr_activation.append(pqc_count / iterations)

for w in weight_range:

    pqc_count = 0
    for i in range(iterations):

        score = sv_api(B, 1.0, w, 0.4,
                       Rquant_values[i],
                       Pcost_values[i],
                       Plat_values[i])

        if score >= UPPER:
            pqc_count += 1

    wc_activation.append(pqc_count / iterations)

for w in weight_range:

    pqc_count = 0
    for i in range(iterations):

        score = sv_api(B, 1.0, 0.4, w,
                       Rquant_values[i],
                       Pcost_values[i],
                       Plat_values[i])

        if score >= UPPER:
            pqc_count += 1

    wl_activation.append(pqc_count / iterations)

# --------------------------------
# GRAPH 1: SENSITIVITY ANALYSIS
# --------------------------------

plt.figure(figsize=(8,5))

plt.plot(weight_range, wr_activation,
         color='#0b6623', linewidth=2.5, label='Risk Weight (WR)')

plt.plot(weight_range, wc_activation,
         color='#555555', linewidth=2.5, label='Cost Weight (WC)')

plt.plot(weight_range, wl_activation,
         color='#8b0000', linewidth=2.5, label='Latency Weight (WL)')

plt.axvline(1.0, linestyle='--', color='black', linewidth=2,
            label='Chosen WR = 1.0')

plt.axvline(0.4, linestyle=':', color='black', linewidth=2,
            label='Chosen WC/WL = 0.4')

plt.xlabel("Weight Value")
plt.ylabel("PQC Activation Rate")
plt.title("Sensitivity Analysis of SV_API Policy Weights")
plt.rcParams['font.weight'] = 'bold'

plt.legend(frameon=False)

plt.savefig("sensitivity_weights.png", dpi=300, bbox_inches='tight')
plt.show()

# --------------------------------
# GRAPH 2: PARAMETER INFLUENCE
# --------------------------------

wr_effect = max(wr_activation) - min(wr_activation)
wc_effect = max(wc_activation) - min(wc_activation)
wl_effect = max(wl_activation) - min(wl_activation)

labels = ["Risk", "Cost", "Latency"]
effects = [wr_effect, wc_effect, wl_effect]

plt.figure(figsize=(8,5))

plt.barh(labels, effects,
         color=['#0b6623', '#555555', '#8b0000'])

plt.xlabel("Activation Change")
plt.title("Relative Parameter Influence on SV_API")
plt.rcParams['font.weight'] = 'bold'

plt.savefig("parameter_influence.png", dpi=300, bbox_inches='tight')
plt.show()

# --------------------------------
# GRAPH 3: BALANCED REGION TEST
# --------------------------------

balance_scores = []

wr_test = np.linspace(0.5, 1.2, 20)

for wr in wr_test:

    pqc_count = 0

    for i in range(iterations):

        score = sv_api(B, wr, 0.4, 0.4,
                       Rquant_values[i],
                       Pcost_values[i],
                       Plat_values[i])

        if score >= UPPER:
            pqc_count += 1

    balance_scores.append(pqc_count / iterations)

plt.figure(figsize=(8,5))

plt.plot(wr_test, balance_scores,
         color='#0b6623', linewidth=2.5)

plt.axvline(1.0, linestyle='--', color='black', linewidth=2,
            label="Chosen WR")

plt.xlabel("Risk Weight")
plt.ylabel("PQC Activation Rate")
plt.title("Balanced Region of Risk Weight")
plt.rcParams['font.weight'] = 'bold'

plt.legend(frameon=False)

plt.savefig("balance_region.png", dpi=300, bbox_inches='tight')
plt.show()

# --------------------------------
# GRAPH 4: HYSTERESIS STABILITY
# --------------------------------

scores = []

for i in range(200):

    R = np.random.uniform(0.2, 1.0)
    P = np.random.uniform(0.0, 0.9)
    L = np.random.uniform(0.0, 1.0)

    score = sv_api(B, 1.0, 0.4, 0.4, R, P, L)
    scores.append(score)

plt.figure(figsize=(8,5))

plt.plot(scores, color='#0b6623', linewidth=2.5, label="SV_API Score")

plt.axhline(UPPER, linestyle='--', color='#8b0000',
            linewidth=2, label="Upgrade Threshold")

plt.axhline(LOWER, linestyle='--', color='#555555',
            linewidth=2, label="Downgrade Threshold")

plt.xlabel("Simulation Time")
plt.ylabel("SV_API Score")
plt.title("Hysteresis Stability of the Adaptive Model")
plt.rcParams['font.weight'] = 'bold'

plt.legend(frameon=False)

plt.savefig("hysteresis_stability.png", dpi=300, bbox_inches='tight')
plt.show()