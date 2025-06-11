import sys
import os

# Add the project root directory to the Python path
# This assumes the script is in 'project_root/scripts/'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


import argparse
import logging
import json

from core.config import settings
from core.db_manager import get_db_connection, update_human_review_status

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def provide_strategic_direction(review_id: int, direction: str) -> None:
    """Provide strategic direction for an agent's decision by updating the human review queue.
    
    Args:
        review_id: The ID of the strategic direction request to respond to.
        direction: The human guidance/direction to provide to the agent.
    """
    logger.info(f"Providing strategic direction for review ID: {review_id}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the strategic direction request exists and is pending
        cursor.execute(
            "SELECT task_type, data_for_review, status FROM human_review_queue WHERE review_id = ?", 
            (review_id,)
        )
        result = cursor.fetchone()
        
        if result is None:
            logger.warning(f"Strategic direction request with ID {review_id} not found.")
            print(f"Error: Strategic direction request with ID {review_id} not found.")
            return
        
        task_type, data_for_review, current_status = result
        
        if task_type != "strategic_direction":
            logger.warning(f"Review ID {review_id} is not a strategic direction request (type: {task_type}).")
            print(f"Error: Review ID {review_id} is not a strategic direction request.")
            return
        
        if current_status != "pending_direction":
            logger.warning(f"Strategic direction request {review_id} is not pending (status: {current_status}).")
            print(f"Error: Strategic direction request {review_id} is not pending.")
            return

        # Parse the original request to show context
        try:
            request_data = json.loads(data_for_review)
            print(f"\n📋 STRATEGIC DIRECTION REQUEST #{review_id}")
            print(f"🔍 Situation Analysis: {request_data.get('situation_analysis', 'N/A')}")
            print(f"🤔 Uncertainty: {request_data.get('uncertainty_reason', 'N/A')}")
            print(f"💡 Proposed Actions:")
            for i, action in enumerate(request_data.get('proposed_actions', []), 1):
                print(f"    {i}. {action}")
            print(f"\n✅ Human Direction: {direction}")
            print("=" * 60)
        except json.JSONDecodeError:
            logger.warning("Could not parse request data for display")

        # Update the review status with the strategic direction
        update_human_review_status(review_id, "direction_provided", reviewer_notes=direction)
        
        logger.info(f"Successfully provided strategic direction for review ID: {review_id}")
        print(f"Strategic direction successfully provided for review ID {review_id}.")
        print(f"The agent will receive guidance: '{direction}'")
        
    except Exception as e:
        logger.error(f"Failed to provide strategic direction for review ID {review_id}: {e}")
        print(f"Error providing strategic direction for review ID {review_id}: {e}")
    finally:
        if conn:
            conn.close()


def list_pending_strategic_requests() -> None:
    """List all pending strategic direction requests."""
    logger.info("Listing pending strategic direction requests")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT review_id, data_for_review, reason_for_review, created_at 
               FROM human_review_queue 
               WHERE task_type = 'strategic_direction' AND status = 'pending_direction'
               ORDER BY created_at ASC"""
        )
        results = cursor.fetchall()
        
        if not results:
            print("No pending strategic direction requests found.")
            return
        
        print(f"\n📋 PENDING STRATEGIC DIRECTION REQUESTS ({len(results)})")
        print("=" * 80)
        
        for review_id, data_for_review, reason, created_at in results:
            print(f"\n🆔 Request ID: {review_id}")
            print(f"🕒 Created: {created_at}")
            print(f"❓ Reason: {reason}")
            
            try:
                request_data = json.loads(data_for_review)
                print(f"🔍 Situation: {request_data.get('situation_analysis', 'N/A')[:100]}...")
                print(f"💡 Proposed Actions:")
                for i, action in enumerate(request_data.get('proposed_actions', []), 1):
                    print(f"    {i}. {action}")
            except json.JSONDecodeError:
                print("⚠️ Could not parse request details")
            
            print("-" * 40)
        
        print(f"\nTo provide direction: python scripts/provide_strategic_direction.py <review_id> \"<direction>\"")
        
    except Exception as e:
        logger.error(f"Failed to list pending strategic requests: {e}")
        print(f"Error listing pending strategic requests: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Provide strategic direction to the autonomous agent when it requests guidance."
    )
    parser.add_argument("review_id", nargs='?', type=int, help="The ID of the strategic direction request to respond to.")
    parser.add_argument("direction", nargs='?', type=str, help="The strategic direction/guidance to provide to the agent.")
    parser.add_argument("--list", action="store_true", help="List all pending strategic direction requests.")

    args = parser.parse_args()

    # Ensure the database path is configured
    if not settings.sqlite_db_path:
        logger.error("Database path not configured. Ensure SQLITE_DB_PATH is set in .env")
        print("Error: Database path not configured. Ensure SQLITE_DB_PATH is set in .env")
        sys.exit(1)

    if args.list:
        list_pending_strategic_requests()
    elif args.review_id and args.direction:
        provide_strategic_direction(args.review_id, args.direction)
    else:
        # If no arguments or incomplete arguments, show pending requests and usage
        print("Strategic Direction Provider for X Agentic Unit")
        print("=" * 50)
        list_pending_strategic_requests()
        print(f"\nUsage:")
        print(f"  List pending requests: python {sys.argv[0]} --list")
        print(f"  Provide direction: python {sys.argv[0]} <review_id> \"<direction>\"")
        print(f"\nExample:")
        print(f"  python {sys.argv[0]} 42 \"Focus on content research - try finding AI ethics discussions\"") 