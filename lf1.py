import boto3
import json
import re
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/222634405207/dining-bot"

ALLOWED_CUISINES = {"indian", "thai", "chinese", "mexican", "kosher", "continental"}

def validate_email(email):
    """Check if the given email is valid."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_time(dining_time):
    """Check if the given time is in 24-hour format (HH:MM)."""
    try:
        datetime.strptime(dining_time, "%H:%M")
        logger.info(f"Time validation passed for {dining_time}")
        return True
    except ValueError:
        return False

def validate_slots(slots):
    """Validate slots one by one and return the first missing/invalid slot immediately."""
    
    # Required slots
    required_slots = ["Cuisine", "NumberOfPeople", "DiningTime", "email", "Location"]
    logger.info(slots)
    for slot in required_slots:
        # Check if slot is missing
        if slot not in slots or not slots[slot] or "value" not in slots[slot]:
            return {"slot_to_elicit": slot, "error_message": None}

        if "interpretedValue" not in slots[slot]["value"]:
            return {"slot_to_elicit": slot, "error_message": f"Please provide a valid {slot}."}

        logger.info(slots[slot]["value"]["interpretedValue"])
        value = slots[slot]["value"]["interpretedValue"]
        
        # Validate each slot
        if slot == "Cuisine" and value.lower() not in ALLOWED_CUISINES:
            return {"slot_to_elicit": slot, "error_message": f"Invalid cuisine. Choose from {', '.join(ALLOWED_CUISINES)}."}

        if slot == "NumberOfPeople":
            try:
                num_people = int(value)
                if num_people < 1 or num_people > 100:
                    return {"slot_to_elicit": slot, "error_message": "Number of people must be between 1 and 100."}
            except ValueError:
                return {"slot_to_elicit": slot, "error_message": "Number of people must be a valid integer."}

        if slot == "DiningTime" and not validate_time(value):
            return {"slot_to_elicit": slot, "error_message": "Dining time must be in 24-hour format (HH:MM)."}

        if slot == "email" and not validate_email(value):
            return {"slot_to_elicit": slot, "error_message": "Please enter a valid email address."}

    return {"slot_to_elicit": None, "error_message": None}

def lambda_handler(event, context):
    """Lex bot Lambda fulfillment function with immediate error messages for invalid inputs."""
    intent = event.get("sessionState", {}).get("intent", {})
    logger.info(intent)
    slots = intent.get("slots", {})

    validation_result = validate_slots(slots)

    # If there's an issue with a slot, ask for it again and show the error message
    if validation_result["slot_to_elicit"]:
        response = {
            "sessionState": {
                "dialogAction": {
                    "type": "ElicitSlot",
                    "slotToElicit": validation_result["slot_to_elicit"]
                },
                "intent": intent
            }
        }

        if validation_result["error_message"]:  
            response["messages"] = [{
                "contentType": "PlainText",
                "content": validation_result["error_message"]
            }]

        return response


    # Extract valid slot values
    extracted_data = {
        "Cuisine": slots["Cuisine"]["value"]["interpretedValue"],
        "NumberOfPeople": slots["NumberOfPeople"]["value"]["interpretedValue"],
        "DiningTime": slots["DiningTime"]["value"]["interpretedValue"],
        "Email": slots["email"]["value"]["interpretedValue"],
        "Location": slots["Location"]["value"]["interpretedValue"],
    }
    logger.info(f"Extracted data: {extracted_data}")

    logger.info(session_attributes := event.get("sessionAttributes", {}))
    # Check if confirmation has already been given
    if intent.get("confirmationState") == "Denied":
        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": intent
            },
            "messages": [{"contentType": "PlainText", "content": "Reservation cancelled."}]
        }

    elif intent.get("confirmationState") != "Confirmed":
        session_attributes["extracted_data"] = json.dumps(extracted_data)

        confirmation_message = (
            f"You requested a table for {extracted_data['NumberOfPeople']} people at {extracted_data['DiningTime']} "
            f"for {extracted_data['Cuisine']} cuisine in {extracted_data['Location'].capitalize()}.\n"
            "Should I proceed with this reservation? (yes/no)"
        )

        return {
            "sessionState": {
                "dialogAction": {
                    "type": "ConfirmIntent"
                },
                "intent": intent,
                "sessionAttributes": session_attributes
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": confirmation_message
                }
            ]
        }

    # Send message to SQS
    else:
        try:
            sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(extracted_data)
            )
        except Exception as e:
            logger.error(f"SQS Error: {e}")
            return {
                "sessionState": {
                    "dialogAction": {"type": "Close"},
                    "intent": intent
                },
                "messages": [{"contentType": "PlainText", "content": "Failed to process your request."}]
            }

        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {"name": "DiningSuggestionsIntent", "state": "Fulfilled"}
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "Your dining request has been received! You will receive suggestions shortly."
                }
            ]
        }
