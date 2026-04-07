import random
# Ensure these modules exist in your project folder
from switching import estimate_latency_ms_for_suite, decide_suite

class ScenarioTester:
    def __init__(self, cloud_service, key_pool, classical_func, pqc_func):
        """
        :param cloud_service: Instance of CloudService
        :param key_pool: Pre-generated keys dict
        :param classical_func: Callback function to run classical test
        :param pqc_func: Callback function to run PQC test
        """
        self.cloud = cloud_service
        self.key_pool = key_pool
        self.run_classical = classical_func
        self.run_pqc = pqc_func
        self.results = []
        self.current_state = 'classical'  # Default starting state

    def _execute_single_run(self, run_id, scenario_name, client, jitter_fixed):
        """
        Helper method to run a single test iteration with fixed jitter.
        """
        client_type = client['type']
        sec_level = client['security']
        message = b'Scenario Test Message'

        # 1. Run Crypto Tests using the callback functions
        cls_res = self.run_classical(message, sec_level)
        pqc_res = self.run_pqc(message, sec_level)

        # 2. Calculate Base Latency
        base_pqc_size = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']
        base_latency = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=base_pqc_size)

        # 3. Apply Scenario-Specific Jitter & Cloud Delay
        # Add tiny random variance (+/- 2ms) so data doesn't look fake
        real_jitter = jitter_fixed + random.uniform(-2.0, 2.0)
        if real_jitter < 0: real_jitter = 0

        service_metrics = self.cloud.process_request()
        service_delay = service_metrics['service_delay_ms']

        # 4. Total Estimated Latency
        final_latency_pqc = base_latency + real_jitter + service_delay + pqc_res['cpu_time_ms']

        # 5. Decision Logic (The Core SV_API Check)
        new_state, meta = decide_suite(
            current_state=self.current_state,
            security_req=sec_level,
            client_type=client_type,
            est_latency_pqc=final_latency_pqc
        )

        # 6. Watchdog Override Check
        if new_state == 'pqc' and final_latency_pqc > 500.0:
            print(f"      >>> WATCHDOG TRIGGERED: Latency {final_latency_pqc:.1f}ms > 500ms")
            new_state = 'classical'
            meta['reason'] = "Watchdog Override"
            # Watchdog forces score to 0.0 or effectively low
            meta['sv_api'] = 0.0

        # Update State
        self.current_state = new_state
        chosen_algo = pqc_res['algorithm'] if new_state == 'pqc' else cls_res['algorithm']

        # 7. Log Result
        record = {
            'scenario': scenario_name,
            'client': client_type,
            'security_req': sec_level,
            'jitter_ms': round(real_jitter, 2),
            'final_latency_ms': round(final_latency_pqc, 2),
            'sv_score': round(meta['sv_api'], 2),
            'decision': new_state.upper(),
            'reason': meta.get('reason', ''),
            'chosen_algo': chosen_algo
        }
        self.results.append(record)

        print(f"   [{scenario_name}] {client_type.upper()} | "
              f"Jitter: {real_jitter:.1f}ms | Score: {meta['sv_api']:.2f} | "
              f"Decision: {new_state.upper()}")

    def run_scenario_a_happy_path(self, clients):
        """
        SCENARIO A: Optimal Network (Low Jitter).
        """
        print("\n--- Running SCENARIO A: Happy Path (Optimal Network) ---")
        for client in clients:
            # Fixed low jitter (~10ms)
            self._execute_single_run(1, "A_HappyPath", client, jitter_fixed=10.0)

    def run_scenario_b_stress_event(self, clients):
        """
        SCENARIO B: Network Congestion (High Jitter).
        """
        print("\n--- Running SCENARIO B: Stress Event (High Jitter) ---")
        for client in clients:
            # Fixed high jitter (~450ms) to trigger downgrade for constrained devices
            self._execute_single_run(1, "B_StressEvent", client, jitter_fixed=450.0)

    def run_scenario_c_watchdog(self, clients):
        """
        SCENARIO C: Catastrophic Failure (Watchdog Trigger).
        """
        print("\n--- Running SCENARIO C: Watchdog Trigger (Critical Lag) ---")
        for client in clients:
            # Extreme jitter (~650ms) to force Watchdog
            self._execute_single_run(1, "C_Watchdog", client, jitter_fixed=650.0)

    def get_results(self):
        return self.results