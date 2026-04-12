import oqs
import time

#selects kyber based on security level
class KyberKEM:
    def __init__(self, security_level=1):
        """
        Dynamically selects the algorithm based on Security Level.
        Level 1 -> Kyber512 (NIST L1)
        Level 3 -> Kyber768 (NIST L3)
        Level 5 -> Kyber1024 (NIST L5)
        """
        if security_level <= 2:
            self.alg = Kyber512
            self.name = "Kyber512"
        elif security_level <= 4:
            self.alg = Kyber768
            self.name = "Kyber768"
        else:
            self.alg = Kyber1024
            self.name = "Kyber1024"
#self explanatory
    def generate_keypair(self):
        pk, sk = self.alg.keygen()
        return pk, sk

#Handshake, quantum equivalent to classical counter part of 'derive shared key'
    def encapsulate(self, public_key):
        shared_secret, ciphertext = self.alg.encaps(public_key)
        return ciphertext, shared_secret

    def decapsulate(self, secret_key, ciphertext):
        return self.alg.decaps(secret_key, ciphertext)

#Dilithium class for signature
class DilithiumSig:
    def __init__(self, security_level=1):
        """
        Dynamically selects Dilithium parameter set.
        Level 1-2 -> Dilithium2
        Level 3-4 -> Dilithium3
        Level 5   -> Dilithium5
        """
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

#for digital signatures, quantum safe replacement of ECDSA
    def sign(self, message: bytes, secret_key: bytes) -> bytes:
        if isinstance(message, str):
            message = message.encode('utf-8')
        return self.alg.sign(secret_key, message)

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        if isinstance(message, str):
            message = message.encode('utf-8')
        return self.alg.verify(public_key, message, signature)
