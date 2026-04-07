import csv
import time
import random

# Import your modules
from metrics import measure_time
from switching import estimate_latency_ms_for_suite
import classical
from pqc import KyberKEM, DilithiumSig
from cloud_service import CloudService
from scenario_manager import ScenarioTester  # This imports the file above

# ==========================================
# CONFIGURATION
# ==========================================
MESSAGE = b'Test message for scenario analysis'

CLIENTS = [
    {'type': 'iot', 'security': 2},
    {'type': 'mobile', 'security': 3},
    {'type': 'desktop', 'security': 4},
    {'type': 'server', 'security': 5}
]

KEY_POOL = {}


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def pre_generate_keys():
    print("\n[Key Lifecycle Manager] Status: INITIALIZING...")
    levels_needed = [2, 3, 5]
    for level in levels_needed:
        kem_temp = KyberKEM(security_level=level)
        pk, sk = kem_temp.generate_keypair()
        KEY_POOL[level] = {'pk': pk, 'sk': sk}
        print(f"   >>> Generated {kem_temp.name} Keys (Level {level}). [READY]")
    print("[Key Lifecycle Manager] Status: ONLINE.\n")


def run_classical_test(message: bytes, sec_level: int):
    # Dummy wrapper to match your previous classical logic
    priv_a, pub_a = classical.generate_ecdh_keypair(sec_level)
    priv_b, pub_b = classical.generate_ecdh_keypair(sec_level)

    t1 = measure_time(classical.derive_shared_key_ecdh, priv_a, pub_b)
    t2 = measure_time(classical.derive_shared_key_ecdh, priv_b, pub_a)

    sign_t = measure_time(classical.ec_sign, priv_a, message)
    sig = sign_t['result']
    verify_t = measure_time(classical.ec_verify, pub_a, message, sig)

    pk_bytes = classical.serialize_public_key(pub_a)
    sk_bytes = classical.serialize_private_key(priv_a)

    curve_name = "P-256" if sec_level <= 2 else ("P-384" if sec_level <= 4 else "P-521")

    sizes = {
        'pubkey_size': len(pk_bytes),
        'privkey_size': len(sk_bytes),
        'signature_size': len(sig)
    }

    cpu_time_ms = sign_t['time_ms'] + verify_t['time_ms'] + t1['time_ms'] + t2['time_ms']

    return {
        'algorithm': f"ECDH-{curve_name} + ECDSA",
        'sizes': sizes,
        'cpu_time_ms': cpu_time_ms
    }


def run_pqc_test(message: bytes, sec_level: int):
    kem_obj = KyberKEM(security_level=sec_level)
    sig_obj = DilithiumSig(security_level=sec_level)

    # Use key pool if available
    pool_level = 3 if sec_level == 4 else sec_level
    if pool_level in KEY_POOL:
        pk = KEY_POOL[pool_level]['pk']
    else:
        pk, _ = kem_obj.generate_keypair()

    t_start = time.perf_counter()
    ciphertext, shared_secret = kem_obj.encapsulate(pk)
    t_end = time.perf_counter()
    real_cpu_time = (t_end - t_start) * 1000.0

    pk_sig, sk_sig = sig_obj.generate_keypair()
    signature = sig_obj.sign(message, sk_sig)
    verify_ok = sig_obj.verify(message, signature, pk_sig)

    sizes = {
        'kem_ciphertext': len(ciphertext),
        'signature_size': len(signature)
    }

    return {
        'algorithm': f"{kem_obj.name} + {sig_obj.name}",
        'signature_valid': verify_ok,
        'sizes': sizes,
        'cpu_time_ms': real_cpu_time
    }


# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    pre_generate_keys()

    cloud_service = CloudService(
        service_name="API-Auth-Service",
        base_latency_ms=30,
        max_concurrent_requests=5
    )

    print("Initializing Scenario Tester...")
    print("=" * 70)

    # Initialize the Tester Class
    tester = ScenarioTester(
        cloud_service=cloud_service,
        key_pool=KEY_POOL,
        classical_func=run_classical_test,
        pqc_func=run_pqc_test
    )

    # --- RUN THE 3 SCENARIOS ---
    tester.run_scenario_a_happy_path(CLIENTS)
    tester.run_scenario_b_stress_event(CLIENTS)
    tester.run_scenario_c_watchdog(CLIENTS)

    # --- SAVE RESULTS ---
    results = tester.get_results()
    filename = "scenario_evidence_sop2.csv"

    headers = [
        'scenario', 'client', 'security_req', 'jitter_ms',
        'final_latency_ms', 'sv_score', 'decision',
        'reason', 'chosen_algo'
    ]

    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[SUCCESS] Exported evidence to '{filename}'")
        print(f"Total Tests Run: {len(results)}")
    except IOError as e:
        print(f"\n[ERROR] Could not write CSV file: {e}")


if __name__ == "__main__":
    main()