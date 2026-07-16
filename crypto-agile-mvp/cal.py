import time
import classical
from pqc import KyberKEM, DilithiumSig


class CryptoAbstractionLayer:
    def __init__(self, key_pool_reference=None):
        # We will use this reference for Recommendation #3 later
        self.key_pool = key_pool_reference if key_pool_reference is not None else {}

    def execute(self, payload, state_mode, security_level):
        """
        Executes the cryptographic operations based on the state mode
        and returns the measured execution latency in milliseconds along with algorithm info.
        """
        start_time = time.perf_counter()

        if state_mode == 'pqc':
            # 1. KEM Operations (Kyber)
            kem = KyberKEM(security_level=security_level)

            # Use Pre-generated keys if available in pool, otherwise fallback
            if security_level in self.key_pool and self.key_pool[security_level]['kem']:
                pk, sk = self.key_pool[security_level]['kem'].pop(0)
            else:
                pk, sk = kem.generate_keypair()

            ciphertext, shared_secret = kem.encapsulate(pk)
            _ = kem.decapsulate(sk, ciphertext)

            # 2. Signature Operations (Dilithium)
            sig_agent = DilithiumSig(security_level=security_level)

            if security_level in self.key_pool and self.key_pool[security_level]['sig']:
                pk_sig, sk_sig = self.key_pool[security_level]['sig'].pop(0)
            else:
                pk_sig, sk_sig = sig_agent.generate_keypair()

            signature = sig_agent.sign(payload, sk_sig)
            _ = sig_agent.verify(payload, signature, pk_sig)

            algo_name = f"{kem.name} + {sig_agent.name}"

        else:
            # Classical Mode (ECDH + ECDSA)
            priv, pub = classical.generate_ecdh_keypair(security_level)
            _ = classical.derive_shared_key_ecdh(priv, pub)

            # Digital Signature simulation
            sig = classical.ec_sign(priv, payload)
            _ = classical.ec_verify(pub, payload, sig)

            curve_name = "P-256" if security_level <= 2 else "P-384" if security_level <= 4 else "P-521"
            algo_name = f"ECDH-{curve_name} + ECDSA"

        end_time = time.perf_counter()
        measured_latency = (end_time - start_time) * 1000

        return measured_latency, algo_name
