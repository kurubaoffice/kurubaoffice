class ContextManager:
    def __init__(self):
        self.history = {}

    def set(self, chat_id, key, value):
        if chat_id not in self.history:
            self.history[chat_id] = {}
        self.history[chat_id][key] = value

    def get(self, chat_id, key):
        return self.history.get(chat_id, {}).get(key)

context = ContextManager()
