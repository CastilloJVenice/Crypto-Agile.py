import oqs

# ==========================================
# KYBER KEM WRAPPER (OQS VERSION)
# ==========================================
class KyberKEM:
    def __init__(self, security_level=2):
        # We only need the STRING name for OQS
        if security_level <= 2:
            self.name = "Kyber512"
        elif security_level <= 4:
            self.name = "Kyber768"
        else:
            self.name = "Kyber1024"
        
    def generate_keypair(self):
        with oqs.KeyEncapsulation(self.name) as kem:
            public_key = kem.generate_keypair()
            # Export is needed to store the key in your main3.py KEY_POOL
            private_key = kem.export_secret_key()
            return public_key, private_key

    def encapsulate(self, public_key):
        with oqs.KeyEncapsulation(self.name) as kem:
            ciphertext, shared_secret = kem.encaps_secret(public_key)
            return ciphertext, shared_secret

# ==========================================
# DILITHIUM SIG WRAPPER (OQS VERSION)
# ==========================================
class DilithiumSig:
    def __init__(self, security_level=2):
        if security_level <= 2:
            self.name = "Dilithium2"
        elif security_level <= 4:
            self.name = "Dilithium3"
        else:
            self.name = "Dilithium5"

    def generate_keypair(self):
        with oqs.Signature(self.name) as sig:
            public_key = sig.generate_keypair()
            private_key = sig.export_secret_key()
            return public_key, private_key

    def sign(self, message, secret_key):
        # Re-initialize the sig object with the exported secret key
        with oqs.Signature(self.name, secret_key) as sig:
            return sig.sign(message)

    def verify(self, message, signature, public_key):
        with oqs.Signature(self.name) as sig:
            return sig.verify(message, signature, public_key)
