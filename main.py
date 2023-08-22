from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.db.db_connector import DBConnector
from src.db.db_config import db_config
from datetime import datetime
import logging
import random
import spacy

app = FastAPI()

logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)

# Define a request schema to specify the expected format of the request data
class DialogflowRequest(BaseModel):
    queryResult: dict

db_connector = DBConnector(db_config)

# Define a route to handle Dialogflow webhook requests
@app.post("/")
async def dialogflow_webhook(request_data: DialogflowRequest):
    try:
        # Extract intent and parameters from request_data
        query_result = request_data.queryResult
        intent_display_name = query_result.get("intent", {}).get("displayName")
        parameters = query_result.get("parameters", {})

        # Call the function to update accumulated parameters
        db_connector.update_accumulated_params(parameters) 

        user_id = random.randint(1, 10000)
        # Call the function to insert user interaction into the database
        db_connector.insert_user_interaction(user_id, parameters)

        # Define logic for each intent based on its display name
        response = handle_intent(intent_display_name, parameters)

        return {"fulfillmentText": response}

    except KeyError as e:
        # Handle missing keys in the request data
        raise HTTPException(status_code=400, detail=f"Missing key in request data: {e}")
    
    except Exception as e:
        # Handle exceptions gracefully
        logger.exception("An error occurred")
        raise HTTPException(status_code=500, detail=str(e))

def extract_date(text):
    # Initialize the date variable
    booking_date = None

    # Process the text with spaCy
    doc = nlp(text)

    # Iterate through named entities to find dates
    for ent in doc.ents:
        if ent.label_ == "DATE":
            booking_date = ent.text
            break  # Stop searching after the first date is found

    return booking_date

# Function to handle each intent with its parameters
def handle_intent(intent_display_name, parameters):
    if "changeintention" in parameters:
        # If "changeintention" parameter is detected, route to "ChangeDate" or "ChangeGuide"
        change_intention = parameters["changeintention"]
        if change_intention == "date":
            date = parameters.get("date")
            db_connector.insert_user_interaction(intent_display_name, date)
            return change_booking_date(date, change_intention)
        elif change_intention == "guide":
            change_guide = parameters.get("languagePreference")
            db_connector.insert_user_interaction(intent_display_name, change_guide)
            return change_guide_language(change_guide)
    
    if intent_display_name == "LanguagePreference":
        preferred_language = parameters.get("preferredLanguage")
        db_connector.insert_user_interaction(intent_display_name, preferred_language)
        return set_language_preference(preferred_language)

    elif intent_display_name == "TourGuideAvailability":
        #date_time = parameters.get("date-time")
        date = parameters.get("date")
        #date_period = parameters.get("date-period")
        
        # Process each parameter with spaCy to extract dates
        date = extract_date(date)

        #db_connector.insert_user_interaction(intent_display_name, date_time)
        db_connector.insert_user_interaction(intent_display_name, date)
        #db_connector.insert_user_interaction(intent_display_name, date_period)

        return check_tour_guide_availability(date)

    elif intent_display_name == "GuideDuration":
        duration = parameters.get("duration")
        #date_time = parameters.get("date-time")

        #db_connector.insert_user_interaction(intent_display_name, date_time)
        db_connector.insert_user_interaction(intent_display_name, duration)

        return get_guide_duration(duration)

    elif intent_display_name == "SendReceipt":
        get_email = parameters.get("email")
        person_name = parameters.get("person")

        db_connector.insert_user_interaction(intent_display_name, get_email)
        db_connector.insert_user_interaction(intent_display_name, person_name)

        return send_receipt(get_email, person_name)

    elif intent_display_name == "UserConfirmation":
        return "To finalize your booking, kindly share your name and email address so I can forward you the summary."

    elif intent_display_name == "Default Welcome Intent":
        return "Hey there! Interested in exploring Bali with a guide? I'm here to make it easy for you to book local guides who speak English, Bahasa, Chinese, Korean, or Japanese!"

    else:
        # Handle unrecognized intent
        return "I'm not sure how to respond to that."

# Implement custom logic for each intent
def set_language_preference(preferred_language):
    # Implement language preference logic (e.g., save to user profile and database)
    if isinstance(preferred_language, list) and len(preferred_language) > 0:
        preferred_language = preferred_language[0]
    return f"Sure! {preferred_language}-speaking guide will be arranged for you. When do you plan to schedule your tour?."
    
def get_guide_duration(duration):
    # Ensure duration is a list of dictionaries
    if isinstance(duration, list) and len(duration) > 0:
        # Extract the 'amount' and 'unit' from the first dictionary
        amount = int(duration[0].get('amount', 0))
        unit = duration[0].get('unit', '')

        # Format the duration as 'amount unit'
        formatted_duration = f"{amount} {unit}"

        # Implement availability checking logic
        return f"Understood. Checking tour guide availability for {formatted_duration}. In order to finish up your booking, we need your name and email address. This will enable us to send you a summary."
    else:
        # Handle the case where 'duration' is not in the expected format
        return "I'm sorry, I couldn't understand the duration. Please provide it in a valid format, such as '5 days'."

def check_tour_guide_availability(date):
    # Format the date_time to a more user-friendly format
    formatted_date_time = format_date(date)
    return f"Sure, we can help you find guides on {formatted_date_time}. Please specify the duration of the tour in day(s)."

def format_date(date_str):
    try:
        # Parse the input date string into a datetime object
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")

        # Format the datetime object as desired (e.g., "4 May 2063")
        formatted_date = date_obj.strftime("%d %B %Y")

        return formatted_date
    except ValueError:
        return date_str

def change_booking_date(date, change_intention):
    # Implement booking date change logic
    return f"Alright, I've modified your booking date to {date}. What's the expected duration of the tour in day(s)?"
    

def change_guide_language(change_guide, change_intention):
    # Implement guide languange change logic
    return f"Okay, I've updated your guide language preference to {change_guide}. Is there anything else related to language or date you'd like to address?"

def send_receipt(get_email, person_name):
    # Implement sending receipt logic (e.g., send an email receipt)
    if isinstance(person_name, list) and len(person_name) > 0:
        person_name = person_name[0]

    # Check if person_name is a dictionary and contains the 'name' key
    if isinstance(person_name, dict) and 'name' in person_name:
        person_name = person_name['name']
        
    return f"Thanks {person_name} for choosing our services. Your booking summary and payment information will be sent to {get_email} within the next 24 hours. Have a fantastic day and make the most of your Bali adventure!"

def insert_user_interaction(parameters):
    try:
        # Check if "user_id" exists in parameters
        if "user_id" in parameters:
            user_id = int(parameters["user_id"])
        else:
            user_id = int(uuid.uuid4()) 

    except Exception as e:
        # Handle exceptions gracefully
        raise e 



# Handle CORS (Cross-Origin Resource Sharing) if needed
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start the FastAPI application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)