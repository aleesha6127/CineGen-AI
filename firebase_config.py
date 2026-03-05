import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

# Firebase Web Config (for reference / client-side)
FIREBASE_WEB_CONFIG = {
    "apiKey": "AIzaSyBJsDXSpVsHPQjgNP94ApZhPX3t9hlQpK0",
    "authDomain": "cinegen-ai-d4310.firebaseapp.com",
    "projectId": "cinegen-ai-d4310",
    "storageBucket": "cinegen-ai-d4310.firebasestorage.app",
    "messagingSenderId": "1011310004856",
    "appId": "1:1011310004856:web:1899b9864c142ef2fabb8d",
    "measurementId": "G-LRTVWLF13W"
}

# Initialize Firebase Admin SDK
def init_firebase():
    """Initialize Firebase Admin SDK using Application Default Credentials or service account."""
    service_account_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
    else:
        # If no service account is found, return None. 
        # ApplicationDefault() often crashes if not perfectly configured.
        return None
    
    app = firebase_admin.initialize_app(cred, {
        "projectId": FIREBASE_WEB_CONFIG["projectId"]
    })
    return app


def get_db():
    """Get Firestore client."""
    return firestore.client()


def verify_token(id_token):
    """Verify Firebase ID token and return decoded token."""
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        return None
