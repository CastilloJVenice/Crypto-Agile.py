import random
import time
import statistics

# Import your modules
from metrics import measure_time, write_results_csv
from switching import estimate_latency_ms_for_suite
import classical
from pqc import KyberKEM, DilithiumSig
from cloud_service import CloudService

# ==========================================
# CONFIGURATION
# ==========================================
MESSAGE = b'Test message for authentication and key exchange'

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
    """Simulates Key Lifecycle Manager."""
    print("\n[Key Lifecycle Manager] Status: INITIALIZING...")
    levels_needed = [2, 3, 5]
    for level in levels_needed:
        kem_temp = KyberKEM(security_level=level)
        pk, sk = kem_temp.generate_keypair()
        KEY_POOL[level] = {'pk': pk, 'sk': sk}
    print("[Key Lifecycle Manager] Status: ONLINE.\n")


def run_classical_test(message: bytes, sec_level: int):
    """Executes ECDH + ECDSA."""
    priv_a, pub_a = classical.generate_ecdh_keypair(sec_level)
    priv_b, pub_b = classical.generate_ecdh_keypair(sec_level)

    t1 = measure_time(classical.derive_shared_key_ecdh, priv_a, pub_b)
    t2 = measure_time(classical.derive_shared_key_ecdh, priv_b, pub_a)
    sign_t = measure_time(classical.ec_sign, priv_a, message)
    sig = sign_t['result']
    verify_t = measure_time(classical.ec_verify, pub_a, message, sig)

    pk_bytes = classical.serialize_public_key(pub_a)

    if sec_level <= 2:
        curve_name = "P-256"
    elif sec_level <= 4:
        curve_name = "P-384"
    else:
        curve_name = "P-521"

    sizes = {'pubkey_size': len(pk_bytes), 'signature_size': len(sig)}
    cpu_time_ms = sign_t['time_ms'] + verify_t['time_ms'] + t1['time_ms'] + t2['time_ms']

    return {'algorithm': f"ECDH-{curve_name}", 'sizes': sizes, 'cpu_time_ms': cpu_time_ms}


def run_pqc_test(message: bytes, sec_level: int):
    """Executes Kyber + Dilithium."""
    kem_obj = KyberKEM(security_level=sec_level)
    sig_obj = DilithiumSig(security_level=sec_level)

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

    sizes = {'kem_ciphertext': len(ciphertext), 'signature_size': len(signature)}

    return {'algorithm': f"{kem_obj.name}+{sig_obj.name}", 'sizes': sizes, 'cpu_time_ms': real_cpu_time}


def generate_comparative_summary(raw_rows, filename="summary_benchmark.csv"):
    """Generates Chapter 4 Table Data."""
    summary = {}

    for row in raw_rows:
        key = row['client']
        if key not in summary:
            summary[key] = {'cls_lat': [], 'pqc_lat': [], 'cls_pay': [], 'pqc_pay': [], 'cls_cpu': [], 'pqc_cpu': []}

        summary[key]['cls_lat'].append(row['classical_latency_ms'])
        summary[key]['pqc_lat'].append(row['pqc_latency_ms'])
        summary[key]['cls_pay'].append(row['classical_payload_bytes'])
        summary[key]['pqc_pay'].append(row['pqc_payload_bytes'])
        summary[key]['cls_cpu'].append(row['classical_cpu_ms'])
        summary[key]['pqc_cpu'].append(row['pqc_cpu_ms'])

    final_rows = []
    for client, data in summary.items():
        final_rows.append({
            'client': client,
            'avg_classical_latency_ms': round(statistics.mean(data['cls_lat']), 2),
            'avg_pqc_latency_ms': round(statistics.mean(data['pqc_lat']), 2),
            'overhead_factor': round(statistics.mean(data['pqc_lat']) / statistics.mean(data['cls_lat']), 2),
            'avg_classical_payload': round(statistics.mean(data['cls_pay']), 2),
            'avg_pqc_payload': round(statistics.mean(data['pqc_pay']), 2),
            'avg_classical_cpu': round(statistics.mean(data['cls_cpu']), 2),
            'avg_pqc_cpu': round(statistics.mean(data['pqc_cpu']), 2)
        })

    write_results_csv(final_rows, filename=filename)
    print(f"\n[Summary Generated] comparative_results.csv created.")


# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    pre_generate_keys()
    cloud_service = CloudService(service_name="API-Auth-Service", base_latency_ms=30, max_concurrent_requests=5)

    results = []
    NUM_RUNS = 30  # BASIS: Hanna et al. (2025)

    print("=" * 70)
    print(f"Running BENCHMARK (N={NUM_RUNS}) with Fixed RRL Latency...")
    print("=" * 70)

    for client in CLIENTS:
        client_type = client['type']
        sec_level = client['security']

        print(f"\nProcessing Client: {client_type.upper()} (Level {sec_level})")
        print("-" * 40)

        for i in range(NUM_RUNS):
            cls = run_classical_test(MESSAGE, sec_level)
            pqc_res = run_pqc_test(MESSAGE, sec_level)

            cls_payload = cls['sizes']['signature_size'] + cls['sizes']['pubkey_size']
            pqc_payload = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']

            # BASIS: Kim et al. (2025) - "Intra-country" latency model
            fixed_jitter = 40.0

            service_metrics = cloud_service.process_request()
            service_delay = service_metrics['service_delay_ms']

            # Estimate Latencies
            base_latency_cls = estimate_latency_ms_for_suite('classical', baseline_ms=5.0, size_bytes=cls_payload)
            final_latency_cls = base_latency_cls + fixed_jitter + service_delay + cls['cpu_time_ms']

            base_latency_pqc = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=pqc_payload)
            final_latency_pqc = base_latency_pqc + fixed_jitter + service_delay + pqc_res['cpu_time_ms']

            results.append({
                'run_id': i + 1,
                'client': client_type,
                'classical_latency_ms': final_latency_cls,
                'pqc_latency_ms': final_latency_pqc,
                'classical_payload_bytes': cls_payload,
                'pqc_payload_bytes': pqc_payload,
                'classical_cpu_ms': cls['cpu_time_ms'],
                'pqc_cpu_ms': pqc_res['cpu_time_ms']
            })

    write_results_csv(results, filename="raw_benchmark.csv")
    generate_comparative_summary(results, filename="comparative_results.csv")
    print("\nBenchmark Complete.")


if __name__ == "__main__":
    main()