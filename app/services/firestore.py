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
            # 'merge=True' updates fields without overwriting the whole doc
            self.db.collection('users').document(uid).set(profile_data, merge=True)
            logger.info(f"✅ User {uid} profile updated successfully.")
        except Exception as e:
            logger.error(f"❌ Error upserting user {uid}: {e}")

    def get_chat_history(self, uid: str, chat_id: str):
        """
        Fetches the chat history for a specific session.
        Returns a list of message dicts: [{"role": "user", "content": "..."}, ...]
        """
        if not self.db: return []
        
        try:
            logger.info(f"📂 Fetching history for Chat ID: {chat_id} (User: {uid})")
            
            # Path: users/{uid}/chats/{chat_id}
            doc_ref = self.db.collection('users').document(uid).collection('chats').document(chat_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                history = data.get('history', [])
                logger.info(f"✅ History found. Loaded {len(history)} previous messages.")
                return history
            
            logger.info("ℹ️ No previous history found for this session. Starting fresh.")
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching history for chat {chat_id}: {e}")
            return []

    def save_interaction(self, uid: str, chat_id: str, new_messages: list):
        """
        Saves new messages and ENFORCES the 'Only Last 2' rule.
        new_messages: list of dicts [{"role": "...", "content": "..."}]
        """
        if not self.db: return
        
        try:
            logger.info(f"💾 Saving {len(new_messages)} new messages to Chat ID: {chat_id}")
            doc_ref = self.db.collection('users').document(uid).collection('chats').document(chat_id)
            
            # Transactional update to prevent race conditions
            @firestore.transactional
            def update_in_transaction(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                current_history = []
                
                if snapshot.exists:
                    current_history = snapshot.to_dict().get('history', [])
                
                # Append new messages (User + AI)
                updated_history = current_history + new_messages
                
                # --- THE ROLLING WINDOW LOGIC ---
                # Keep only the last 4 messages (2 User + 2 AI)
                if len(updated_history) > 4:
                    updated_history = updated_history[-4:]
                    logger.info("✂️ History pruned to last 4 messages.")
                
                transaction.set(ref, {
                    "history": updated_history,
                    "last_updated": firestore.SERVER_TIMESTAMP
                }, merge=True)

            transaction = self.db.transaction()
            update_in_transaction(transaction, doc_ref)
            logger.info(f"✅ Interaction saved successfully for {chat_id}.")
            
        except Exception as e:
            logger.error(f"❌ Error saving chat window: {e}")

firestore_service = FirestoreService()