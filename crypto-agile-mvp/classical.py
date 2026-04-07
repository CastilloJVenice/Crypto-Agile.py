from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
#import classical modules (ECDH, ECDSA)


#Select curves based on the security level. the higher the security level, the higher the curve
#assign levels to each client, for e.g if client has level 2 security, assign level 1 ECC).
def get_curve_for_security(level):
    if level <= 2:
        return ec.SECP256R1() # Matches Kyber512 strength
    elif level <= 4:
        return ec.SECP384R1() # Matches Kyber768 strength
    else:
        return ec.SECP521R1() # Matches Kyber1024 strength

#Generate keypair (public / private keys) for key exchange (Elliptic-curve Diffie-Hellman (ECDH))
def generate_ecdh_keypair(security_level=1):
    curve = get_curve_for_security(security_level)
    priv = ec.generate_private_key(curve)
    pub = priv.public_key()
    return priv, pub

#The handshake. combines public key + private key to make a shared secret
def derive_shared_key_ecdh(priv, peer_pub, length=32):
    shared = priv.exchange(ec.ECDH(), peer_pub)
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=b'ecdh derived')
    return hkdf.derive(shared)


#Assign Digital signatures to verify identity
def ec_sign(private_key, message):
    return private_key.sign(message, ec.ECDSA(hashes.SHA256()))

def ec_verify(public_key, message, signature):
    try:
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except:
        return False

# Serialization functions
def serialize_public_key(pub):
    return pub.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)

def serialize_private_key(priv):
    return priv.private_bytes(encoding=serialization.Encoding.DER, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())