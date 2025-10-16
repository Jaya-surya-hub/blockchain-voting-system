import face_recognition
import numpy as np
import cv2
import base64

class FaceRecognition:
    
    @staticmethod
    def capture_and_encode(image_data):
        """Capture face from webcam and encode"""
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(image_data.split(',')[1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Find face encodings
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) > 0:
                return face_encodings[0].tolist()
            return None
        except Exception as e:
            print(f"Face encoding error: {e}")
            return None
    
    @staticmethod
    def verify_face(stored_encoding, live_encoding):
        """Verify if two face encodings match"""
        try:
            stored = np.array(stored_encoding)
            live = np.array(live_encoding)
            
            distance = face_recognition.face_distance([stored], live)[0]
            threshold = 0.6
            
            return distance < threshold
        except Exception as e:
            print(f"Face verification error: {e}")
            return False
