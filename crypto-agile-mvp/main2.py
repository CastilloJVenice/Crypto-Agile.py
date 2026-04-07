import random
import csv
import time
from cryptography.hazmat.primitives import serialization

# Import your modules
from metrics import measure_time, write_results_csv
from switching import estimate_latency_ms_for_suite, decide_suite
import classical
from pqc import KyberKEM, DilithiumSig

# Prepare test message
MESSAGE = b'Test message for authentication and key exchange'

# Test cases
CLIENTS = [
    {'type': 'iot', 'security': 2},
    {'type': 'mobile', 'security': 3},
    {'type': 'desktop', 'security': 4},
    {'type': 'server', 'security': 5}
]


# --- Classical test ---
def run_classical_test(message: bytes, sec_level: int):
    priv_a, pub_a = classical.generate_ecdh_keypair(sec_level)
    priv_b, pub_b = classical.generate_ecdh_keypair(sec_level)

    t1 = measure_time(classical.derive_shared_key_ecdh, priv_a, pub_b)
    t2 = measure_time(classical.derive_shared_key_ecdh, priv_b, pub_a)
    sign_t = measure_time(classical.ec_sign, priv_a, message)
    sig = sign_t['result']
    verify_t = measure_time(classical.ec_verify, pub_a, message, sig)

    pk_bytes = classical.serialize_public_key(pub_a)
    sk_bytes = classical.serialize_private_key(priv_a)

    if sec_level <= 2:
        curve_name = "P-256"
    elif sec_level <= 4:
        curve_name = "P-384"
    else:
        curve_name = "P-521"

    sizes = {'pubkey_size': len(pk_bytes), 'privkey_size': len(sk_bytes), 'signature_size': len(sig)}
    cpu_time_ms = sign_t['time_ms'] + verify_t['time_ms'] + t1['time_ms'] + t2['time_ms']

    return {
        'algorithm': f"ECDH-{curve_name} + ECDSA",
        'sizes': sizes,
        'cpu_time_ms': cpu_time_ms,
    }


# --- PQC test (STANDARD MODE: Generate Keys Every Time) ---
def run_pqc_test(message: bytes, sec_level: int):
    kem_obj = KyberKEM(security_level=sec_level)
    sig_obj = DilithiumSig(security_level=sec_level)

    # Start Timer (Standard mode includes the slow key generation)
    t_start = time.perf_counter()

    # 1. Generate Keypair
    pk, sk = kem_obj.generate_keypair()
    # 2. Encapsulate
    ciphertext, shared_secret = kem_obj.encapsulate(pk)

    t_end = time.perf_counter()
    real_cpu_time = (t_end - t_start) * 1000.0

    # 3. Sign & Verify
    pk_sig, sk_sig = sig_obj.generate_keypair()
    signature = sig_obj.sign(message, sk_sig)
    verify_ok = sig_obj.verify(message, signature, pk_sig)

    sizes = {'kem_ciphertext': len(ciphertext), 'signature_size': len(signature)}
    algo_name = f"{kem_obj.name} + {sig_obj.name}"

    return {
        'algorithm': algo_name,
        'signature_valid': verify_ok,
        'sizes': sizes,
        'cpu_time_ms': real_cpu_time,
    }


# --- Main ---
def main():
    results = []
    print("Running Crypto-Agile MVP (Standard Mode - main2.py)...")
    print("=" * 70)

    CURRENT_STATE = 'classical'
    NUM_RUNS = 5

    for client in CLIENTS:
        client_type = client['type']
        sec_level = client['security']

        print(f"\nProcessing Client: {client_type.upper()} (Level {sec_level})")
        print("-" * 40)

        for i in range(NUM_RUNS):
            cls = run_classical_test(MESSAGE, sec_level)
            pqc_res = run_pqc_test(MESSAGE, sec_level)

            base_pqc_size = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']
            base_latency = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=base_pqc_size)

            network_jitter = random.uniform(0, 1000.0)
            final_latency_pqc = base_latency + network_jitter + pqc_res['cpu_time_ms']

            new_state, meta = decide_suite(
                current_state=CURRENT_STATE,
                security_req=sec_level,
                client_type=client_type,
                est_latency_pqc=final_latency_pqc
            )

            # Watchdog
            WATCHDOG_LIMIT_MS = 500.0
            if new_state == 'pqc' and final_latency_pqc > WATCHDOG_LIMIT_MS:
                print(f"   [Run {i + 1}] !!! WATCHDOG: Latency ({final_latency_pqc:.1f}ms) > 500ms. Fallback.")
                new_state = 'classical'
                meta['reason'] = "Watchdog Override"
                meta['sv_api'] = 0.0

            CURRENT_STATE = new_state
            chosen_algo = pqc_res['algorithm'] if new_state == 'pqc' else cls['algorithm']

            print(
                f"   [Run {i + 1}] Jitter={network_jitter:.1f}ms | Score={meta['sv_api']:.2f} | Action={new_state.upper()}")

            row = {
                'run_id': i + 1,
                'client': client_type,
                'security_req': sec_level,
                'jitter_ms': network_jitter,
                'final_latency': final_latency_pqc,
                'start_state': CURRENT_STATE,
                'new_state': new_state,
                'chosen_algorithm': chosen_algo,
                'sv_score': meta['sv_api'],
                'decision_reason': meta['reason'],
                'pqc_sig_size': pqc_res['sizes']['signature_size'],
                'cls_sig_size': cls['sizes']['signature_size']
            }
            results.append(row)


    write_results_csv(results, filename="results1.csv")
    print("\n" + "=" * 70)
    print(f"Completed {len(results)} total simulations. Results saved to results1.csv")


if __name__ == "__main__":
    main()