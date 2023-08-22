import mysql.connector
from mysql.connector import Error
from datetime import datetime
import re
import random
from src.db.db_config import db_config
import spacy

# Initialize a dictionary to accumulate parameters
accumulated_params = {}

nlp = spacy.load("en_core_web_sm")

class DBConnector:
    def __init__(self, db_config):
        self.db_config = db_config

    # When a new interaction occurs, update the accumulated parameters
    def update_accumulated_params(self, parameters):
        for key, value in parameters.items():
            if key in accumulated_params:
                # Check if the existing value is a string
                if isinstance(accumulated_params[key], list):
                    accumulated_params[key].append(value)
                else:
                    accumulated_params[key] = [accumulated_params[key], value]
            else:
                accumulated_params[key] = value

    # Insert into the database (e.g., at the end of a conversation)
    def insert_user_interaction(self, user_id, parameters):
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Fetch guide_id based on language
            # Handle "preferredLanguage" parameter
            preferred_languages = accumulated_params.get("preferredLanguage", [])
            preferred_languages = [str(lang) for lang in preferred_languages if lang]
            language = ", ".join(preferred_languages)

            guide_query = "SELECT guide_id FROM guide WHERE language_spoken LIKE %s"
            cursor.execute(guide_query, ("%" + language + "%",))
            guide_id_result = cursor.fetchone()

            # Check if a guide was found
            if guide_id_result:
                guide_id = guide_id_result[0]
            else:
                guide_id = None
            
            for _ in cursor:
                pass
            
            if "person" in parameters:
                name = parameters["person"].get("name")
            else:
                name = None

            user_id = random.randint(1, 10000)
            email = accumulated_params.get("email", "")
            
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
            
            booking_date = accumulated_params.get("date", "")

            if booking_date and isinstance(booking_date, str):
                formatted_booking_date = datetime.fromisoformat(booking_date)
                formatted_booking_date = formatted_booking_date.strftime('%Y-%m-%d')
            else:
                formatted_booking_date = None
            
            duration_list = accumulated_params.get("duration", [])
            if isinstance(duration_list, list):
                durations = [str(item.get('amount', '')) for item in duration_list]
                duration = ", ".join(durations)
            else:
                duration = None

            # Create a SQL query to insert or update user interactions into the 'booking' table
            insert_query = """
            INSERT INTO booking (user_id, guide_id, name, email, language, booking_date, duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                user_id,
                guide_id,
                name,
                email,
                language,
                formatted_booking_date,
                duration
            )

            cursor.execute(insert_query, values)
            connection.commit()
        except Error as error:
            print("Error:", error)
        finally:
            cursor.close()
            connection.close()