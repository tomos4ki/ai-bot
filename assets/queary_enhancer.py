
import sqlite3
from datetime import datetime

class MessageDatabase:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY , 
                user_id TEXT,
                message TEXT,
                response TEXT,
                date TEXT
            );
            """)
        self.conn.commit()


    def add_message(self, user_id, message, response):
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO messages (user_id, message, response, date) VALUES (?, ?, ?, ?)";
        """,(user_id, message, response, date))
        self.conn.commit()

    def get_messages(self, user_id):
        self.cursor.execute("""
            SELECT * FROM messages WHERE user_id = ?;
        """, (user_id,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()



class GEminiConerstationHandler:
    def __init__(self):
        self.conversation_history = {}

    def add_message(self, user_id, message):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append(message)

    def get_conversation_history(self, user_id):
        messages = self.db.get_messages(user_id)
        conversation_history = []
        for message in messages:
            conversation_history.append(message[2])
        return conversation_history

    def update_conversation_history(self, user_id, new_history):
        self.conversation_history[user_id] = new_history

class close_db():
    def __init__(self, db):
        self.db = db
    def __enter__(self):
        return self.db
    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()


# CONDENSE_PROMPT_SYSTEM_TEMPLATE = (
#     "Given the following conversation between a user and an AI assistant and a follow up "
#     "question from user, rephrase the follow up question to be a standalone question. Ensure "
#     "that the standalone question summarizes the conversation and completes the follow up "
#     "question with all the necessary context."
#     + """
# Chat History:
#   {chat_history}
# """
# )
# CONDENSE_PROMPT_USER_TEMPLATE = """Follow Up Input: {question}
#   Standalone question:"""