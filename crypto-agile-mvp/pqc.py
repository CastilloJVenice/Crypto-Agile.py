from kyber_py.kyber import Kyber512, Kyber768, Kyber1024
from dilithium_py.dilithium import Dilithium2, Dilithium3, Dilithium5

# ==========================================
# KYBER KEM WRAPPER (kyber-py VERSION)
# ==========================================
class KyberKEM:
    def __init__(self, security_level=2):
        if security_level <= 2:
            self.alg = Kyber512
            self.name = "Kyber512"
        elif security_level <= 4:
            self.alg = Kyber768
            self.name = "Kyber768"
        else:
            self.alg = Kyber1024
            self.name = "Kyber1024"

    def generate_keypair(self):
        pk, sk = self.alg.keygen()
        return pk, sk

    def encapsulate(self, public_key):
        shared_secret, ciphertext = self.alg.encaps(public_key)
        return ciphertext, shared_secret

    def decapsulate(self, secret_key, ciphertext):
        return self.alg.decaps(secret_key, ciphertext)


# ==========================================
# DILITHIUM SIG WRAPPER (dilithium-py VERSION)
# ==========================================
class DilithiumSig:
    def __init__(self, security_level=2):
        if security_level <= 2:
            self.alg = Dilithium2
            self.name = "Dilithium2"
        elif security_level <= 4:
            self.alg = Dilithium3
            self.name = "Dilithium3"
        else:
            self.alg = Dilithium5
            self.name = "Dilithium5"

    def generate_keypair(self):
        pk, sk = self.alg.keygen()
        return pk, sk

    def sign(self, message: bytes, secret_key: bytes) -> bytes:
        if isinstance(message, str):
            message = message.encode('utf-8')
        return self.alg.sign(secret_key, message)

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        if isinstance(message, str):
            message = message.encode('utf-8')
        return self.alg.verify(public_key, message, signature)
