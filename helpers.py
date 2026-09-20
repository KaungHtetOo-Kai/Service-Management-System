import requests

from flask import redirect, render_template, session
from functools import wraps
from datetime import datetime

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def map_position(position_input: str):
    """
    Takes a string form input ('1', '2', etc.) and returns 
    the corresponding database TEXT value or None if invalid.
    """
    # Clean up any accidental leading/trailing spaces
    input = str(position_input).strip()
    
    position_mapping = {
        '0': 'Admin',
        '1': 'Manager',
        '2': 'Engineer',
        '3': 'Receptionist',
        '4': 'Store Executive'
    }
    
    # Return the mapped value, or None if the key doesn't exist
    return position_mapping.get(input, None)

def map_department(department_input: str):
    """
    Takes a string form input ('1', '2', etc.) and returns 
    the corresponding database TEXT value or None if invalid.
    """
    # Clean up any accidental leading/trailing spaces
    input = str(department_input).strip()
    
    department_mapping = {
        '0': 'Admin',
        '1': 'Management Department',
        '2': 'Technical Department',
        '3': 'Finance Department',
        '4': 'Store Department'
    }
    
    # Return the mapped value, or None if the key doesn't exist
    return department_mapping.get(input, None)

def generate_sequence_id(db, table_name, column_name, prefix):
    """
    Generates a cryptographically sound, contextual enterprise ID string.
    
    Format Matrices:
    - Purchase Order (PO): POYYYYMMDDNNNN (Total Length: 14 chars)
    - Shop Transfer  (ST): STYYYYMMDDNNNN (Total Length: 14 chars)
    - Inventory Transaction  (IT): RPYYYYMMDDNNNN (Total Length: 14 chars)
    - Repair Ticket  (RP): RPYYYYMMDDNNNNNN (Total Length: 16 chars)
    
    :param db: Active SQLite database execute wrapper connection instance.
    :param table_name: Target database table to scan (e.g., 'repair_tickets').
    :param column_name: Target column tracking this sequence ID string (e.g., 'ticket_id').
    :param prefix: The module operation code token string ('PO', 'ST', or 'RP').
    :return: A customized sequential string.
    """
    # Force uppercase to prevent casing typo bugs inside your SQL comparisons
    prefix = str(prefix).strip().upper()
    
    # 1. Grab today's calendar date string stamp: YYYYMMDD
    today_date_str = datetime.now().strftime("%Y%m%d") # e.g., '20260801'
    
    # Combine prefix and date to create our daily lookup base marker
    search_base_marker = f"{prefix}{today_date_str}" # e.g., 'PO20260801' or 'RP20260801'

    # 2. RESOLVE PADDING RESOLUTIONS AUTOMATICALLY BY MODULE CATEGORY
    # Set digit lengths and expected total character string bounds dynamically
    if prefix in ['PO', 'ST']:
        digit_padding = 4
        expected_total_length = 2 + 8 + 4  # prefix(2) + date(8) + counter(4) = 14 chars
    elif prefix == 'RP':
        digit_padding = 6
        expected_total_length = 2 + 8 + 6  # prefix(2) + date(8) + counter(6) = 16 chars
    else:
        # Fallback safeguard layout defaults to prevent compilation crashes on unknown codes
        digit_padding = 4
        expected_total_length = len(prefix) + 8 + 4

    # 3. Query SQLite to find the highest matching sequential string generated TODAY
    query = f"SELECT MAX({column_name}) as max_id FROM {table_name} WHERE {column_name} LIKE :search_pattern"
    try:
        result = db.execute(query, search_pattern=f"{search_base_marker}%")

    except Exception as e:
        return str(e)  # Return the error string for debugging purposes"

    # Handle data result wrapper list arrays safely
    if isinstance(result, list) and len(result) > 0:
        max_id_row = result[0]
    else:
        max_id_row = result

    # 4. DETERMINE THE NEXT IN-LINE SEQUENCE ID
    next_sequence_number = 1 # Fallback baseline default if this is the very first entry of the day

    if max_id_row and max_id_row.get("max_id"):
        current_max_id_str = str(max_id_row["max_id"])
        
        # Verify the length matches our specific structural criteria precisely
        if len(current_max_id_str) == expected_total_length and current_max_id_str.startswith(search_base_marker):
            # Isolate and slice out exactly the final counter digits
            last_digits_counter = current_max_id_str[-digit_padding:]
            next_sequence_number = int(last_digits_counter) + 1

    # 5. ASSEMBLE AND RETURN THE COMPLETED ENTERPRISE IDENTIFIER
    # Uses dynamic width formatting padding string interpolation (e.g., :04d or :06d dynamically)
    final_id_string = f"{search_base_marker}{next_sequence_number:0{digit_padding}d}"
    
    return final_id_string

def not_found(url, page):
    """
    Renders a custom 404 error page.
    """
    return render_template("404.html", url=url, page=page), 404


