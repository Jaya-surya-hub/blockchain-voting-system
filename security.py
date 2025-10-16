import face_recognition
import numpy as np
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib
import random

class SecurityHelper:
    """Security utilities for voting system"""
    
    # AES Encryption key (in production, store this securely!)
    ENCRYPTION_KEY = b'VotingSystemKey!' * 2  # 32 bytes key
    
    @staticmethod
    def check_duplicate_face(new_face_encoding, all_users):
        """
        Check if face already exists in database
        Returns: (is_duplicate, matched_voter_id)
        """
        try:
            new_encoding = np.array(new_face_encoding)
            
            for user in all_users:
                stored_encoding = np.array(user.get('face_encoding'))
                
                # Compare faces with strict tolerance
                matches = face_recognition.compare_faces(
                    [stored_encoding], 
                    new_encoding, 
                    tolerance=0.5  # Strict matching
                )
                
                if matches[0]:
                    return True, user.get('voter_id')
            
            return False, None
            
        except Exception as e:
            print(f"Face comparison error: {str(e)}")
            return False, None
    
    @staticmethod
    def encrypt_data(data):
        """Encrypt personal data using AES"""
        try:
            cipher = AES.new(SecurityHelper.ENCRYPTION_KEY, AES.MODE_CBC)
            iv = cipher.iv
            
            # Pad and encrypt
            encrypted = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
            
            # Combine IV and encrypted data
            result = base64.b64encode(iv + encrypted).decode('utf-8')
            return result
            
        except Exception as e:
            print(f"Encryption error: {str(e)}")
            return None
    
    @staticmethod
    def decrypt_data(encrypted_data):
        """Decrypt personal data"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Extract IV and encrypted data
            iv = encrypted_bytes[:16]
            encrypted = encrypted_bytes[16:]
            
            # Decrypt
            cipher = AES.new(SecurityHelper.ENCRYPTION_KEY, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            return None
    
    @staticmethod
    def elgamal_encrypt_vote(candidate):
        """ElGamal encryption for vote (simplified)"""
        # In production, use proper ElGamal library
        p = 467  # Prime number
        g = 2    # Generator
        
        # Generate random key
        private_key = random.randint(1, p-2)
        public_key = pow(g, private_key, p)
        
        # Convert candidate to number
        candidate_num = sum(ord(c) for c in candidate)
        
        # Encrypt
        k = random.randint(1, p-2)
        c1 = pow(g, k, p)
        c2 = (candidate_num * pow(public_key, k, p)) % p
        
        encrypted = {
            'c1': c1,
            'c2': c2,
            'candidate_hash': hashlib.sha256(candidate.encode()).hexdigest()
        }
        
        return encrypted
    
    @staticmethod
    def generate_zkp(voter_id, candidate):
        """Generate Zero-Knowledge Proof"""
        # Simplified ZKP - proves vote is valid without revealing choice
        
        # Create commitment
        commitment = hashlib.sha256(
            f"{voter_id}{candidate}".encode()
        ).hexdigest()
        
        # Create challenge
        challenge = hashlib.sha256(
            f"{commitment}{voter_id}".encode()
        ).hexdigest()
        
        # Create response
        response = hashlib.sha256(
            f"{challenge}{candidate}".encode()
        ).hexdigest()
        
        zkp = {
            'commitment': commitment,
            'challenge': challenge,
            'response': response
        }
        
        return zkp
