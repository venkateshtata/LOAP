import sqlite3
import re
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph
from typing import Dict, Any, Optional

# Database Connection
DB_PATH = "real_estate.db"  # Ensure this is the correct path

def execute_query(query, params=(), fetch=False):
    """Executes a SQL query safely with proper commit and error handling."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch:
            result = cursor.fetchall()
            conn.close()
            return result
        
        conn.commit()
        conn.close()
        return "Success"
    except Exception as e:
        print("[ERROR] Database operation failed:", e)
        return f"Database error: {e}"

def get_properties(phone_number: str):
    """Fetches all properties linked to the given phone number."""
    print(f"[DEBUG] Fetching properties for phone number: {phone_number}")
    
    properties = execute_query(
        """
        SELECT p.property_id, p.name, p.address FROM Property p
        JOIN Role_map r ON p.property_id = r.property_id
        WHERE r.phone_number = ?
        """, 
        (phone_number,), fetch=True
    )
    
    if not properties:
        print("[DEBUG] No properties found.")
        return None
    
    return properties

def update_property(property_id: str, field: str, new_value: str):
    """Updates a specific field of a property."""
    print(f"[DEBUG] Updating property {property_id} field '{field}' to '{new_value}'")
    
    query = f"UPDATE Property SET {field} = ? WHERE property_id = ?"
    result = execute_query(query, (new_value, property_id))
    
    if result == "Success":
        return f"✅ Property {property_id} updated successfully."
    else:
        return result

def detect_update_request(user_input: str, default_property_id: Optional[str]) -> Optional[tuple]:
    """Parses user input to detect if it contains a property update request."""
    pattern = re.search(r"update (\w+) of property (\d+) to (.+)", user_input, re.IGNORECASE)
    
    if pattern:
        field, property_id, new_value = pattern.groups()
        return property_id, field, new_value
    
    # If no property ID is explicitly mentioned, assume it's for the first linked property
    if "update" in user_input.lower() and default_property_id:
        pattern = re.search(r"update the (\w+) to (.+)", user_input, re.IGNORECASE)
        if pattern:
            field, new_value = pattern.groups()
            return default_property_id, field, new_value
    
    return None

def chatbot_logic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Processes user input and updates the conversation state."""
    user_input = state.get("user_input", "")
    
    if state.get("awaiting_phone_number", True):
        state["phone_number"] = user_input
        properties = get_properties(user_input)
        if properties:
            state["linked_properties"] = properties  # Store property list in state
            state["default_property_id"] = properties[0][0]  # Assume first property is default
            greeting_message = "\nHello! Here are your linked properties:\n"
            for prop in properties:
                greeting_message += f"- {prop[1]} at {prop[2]}\n"
            state["response"] = greeting_message
        else:
            state["response"] = "No properties found for this phone number."
        state["awaiting_phone_number"] = False
    else:
        update_info = detect_update_request(user_input, state.get("default_property_id"))
        if update_info:
            property_id, field, new_value = update_info
            update_result = update_property(property_id, field, new_value)
            state["response"] = update_result
        else:
            state["response"] = "I didn't understand that. You can update a property by saying 'Update the status to Sold'."
    return state

# Create and compile LangGraph state machine
workflow = StateGraph(state_schema=Dict[str, Any])
workflow.add_node("chatbot_logic", chatbot_logic)
workflow.set_entry_point("chatbot_logic")
compiled_workflow = workflow.compile()

# Start chatbot
def chatbot():
    print("\n🤖 Welcome to the Real Estate Chatbot! Type 'exit' to quit.\n")
    state = {"awaiting_phone_number": True, "user_input": ""}
    
    # Prompt user for phone number first
    print("Bot: Please enter your phone number to retrieve linked properties:")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye! 👋")
            break
        
        state["user_input"] = user_input  # Store user input in state
        state = compiled_workflow.invoke(state)  # Pass state, not user_input separately
        print("Bot:", state["response"])

# Run chatbot
if __name__ == "__main__":
    chatbot()
