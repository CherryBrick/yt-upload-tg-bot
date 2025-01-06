import os 


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "scripts", "download_and_refresh.sh")
APPROVED_USERS_FILE = os.path.join(BASE_DIR, "db", "approved_users.json")
PENDING_REQUESTS_FILE = os.path.join(BASE_DIR, "db", "pending_requests.json")
