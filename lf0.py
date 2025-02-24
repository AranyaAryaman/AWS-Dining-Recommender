import json
import logging
import boto3
import uuid
import time
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lex_client = boto3.client("lexv2-runtime", region_name="us-east-1")  # Update region

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    start_time = time.time()

    try:
        session_id = "dd79ac39-775e-4bb7-bfd9-a634f41cf3a8";
        if "messages" in event and isinstance(event["messages"], list) and len(event["messages"]) > 0:
            user_message = event["messages"][0].get("unstructured", {}).get("text", "").strip()
        else:
            return generate_response(["Invalid request. No message provided."], session_id)

        if not user_message:
            return generate_response(["Message is empty."], session_id)
        logger.info(f"Session ID: {session_id}")
        # Call Amazon Lex with the sessionId
        lex_response = lex_client.recognize_text(
            botId="XFTIXXB037",
            botAliasId="TSTALIASID",
            localeId="en_US",
            sessionId=session_id,
            text=user_message
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Lex API response time: {elapsed_time:.2f} seconds")
        logger.info(f"Lex Intent: {lex_response.get('sessionState', {}).get('intent', {}).get('name')}")
        logger.info(f"Lex Slots: {lex_response.get('sessionState', {}).get('intent', {}).get('slots')}")

        # Extract bot messages (handling multiple responses)
        lex_messages = lex_response.get("messages", [])
        logger.info(f"Lex Messages: {lex_messages}")
        # Check if Lex is eliciting a slot (waiting for user input)
        bot_texts = [msg["content"] for msg in lex_messages] if lex_messages else ["Sorry, I didn’t understand that."]

        return generate_response(bot_texts, session_id)

    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        return generate_response([f"An error occurred: {str(e)}"], session_id)

def generate_response(bot_texts, session_id):
    """Formats response for API Gateway with multiple messages."""
    return {
        "messages": [
            {
                "type": "unstructured",
                "unstructured": {
                    "id": session_id,
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat()
                }
            } for text in bot_texts
        ]
    }
