
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app, db                 # <- dein Modul mit dem globalen Flask app
from managers.availability_manager import AvailabilityManager

# --- Logging Setup ---
import logging
# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,  # oder DEBUG, wenn du mehr Details willst
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    with app.app_context():
        manager = AvailabilityManager()
        try:
            results = manager.ensure_auto_availability_for_all(days_ahead=365)
            logger.info("Auto-Availability run finished: added=%s skipped=%s",
                        results.get("added"), results.get("skipped"))
        except Exception as e:
            logger.exception("Auto-Availability run failed")