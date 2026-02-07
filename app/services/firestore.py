from google.cloud import firestore
from app.core.config import settings
from app.core.logger import logger

class FirestoreService:
    def __init__(self):
        try:
            logger.info(f"🔥 Initializing Firestore Client for Project: {settings.GOOGLE_CLOUD_PROJECT}")
            self.db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            logger.info("✅ Firestore Client Connected.")
        except Exception as e:
            logger.error(f"❌ Firestore Init Failed: {e}")
            self.db = None

    def upsert_user(self, uid: str, profile_data: dict):
        """Syncs user profile data."""
        if not self.db: 
            logger.warning("⚠️ Firestore not connected. Skipping user upsert.")
            return

        try:
            logger.info(f"👤 Syncing profile for User: {uid} | Role: {profile_data.get('role')}")
            self.db.collection('users').document(uid).set(profile_data, merge=True)
        except Exception as e:
            logger.error(f"❌ Error upserting user {uid}: {e}")

    def get_chat_history(self, uid: str, chat_id: str):
        """
        Fetches the FULL history but returns ONLY the last 2 interactions (4 messages).
        """
        if not self.db: return []
        
        try:
            logger.info(f"📂 Fetching history for Chat ID: {chat_id}")
            
            doc_ref = self.db.collection('users').document(uid).collection('chats').document(chat_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                full_history = data.get('history', [])
                
                # --- CHANGE: SLICE HERE, NOT IN DB ---
                # Take only the last 4 messages for the AI Context
                recent_history = full_history[-4:] if len(full_history) > 4 else full_history
                
                logger.info(f"✅ Loaded {len(full_history)} total msgs. Returning last {len(recent_history)}.")
                return recent_history
            
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching history for chat {chat_id}: {e}")
            return []

    def save_interaction(self, uid: str, chat_id: str, new_messages: list):
        """
        Saves new messages by APPENDING them to the full history.
        Does NOT delete old messages.
        """
        if not self.db: return
        
        try:
            logger.info(f"💾 Saving {len(new_messages)} new messages to Chat ID: {chat_id}")
            doc_ref = self.db.collection('users').document(uid).collection('chats').document(chat_id)
            
            @firestore.transactional
            def update_in_transaction(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                current_history = []
                
                if snapshot.exists:
                    current_history = snapshot.to_dict().get('history', [])
                
                # --- CHANGE: APPEND ONLY (NO DELETION) ---
                updated_history = current_history + new_messages
                
                transaction.set(ref, {
                    "history": updated_history,
                    "last_updated": firestore.SERVER_TIMESTAMP
                }, merge=True)

            transaction = self.db.transaction()
            update_in_transaction(transaction, doc_ref)
            logger.info(f"✅ Interaction saved. Total history length is now growing.")
            
        except Exception as e:
            logger.error(f"❌ Error saving chat: {e}")

firestore_service = FirestoreService()