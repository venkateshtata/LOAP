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

def get_meeting_link(property_id: str):
    """Fetches the meeting link for the agent assigned to the property."""
    print(f"[DEBUG] Looking up meeting link for property {property_id}")
    
    result = execute_query(
        """
        SELECT fly_person_name, meeting_link FROM Flyp_contact
        WHERE property_id = ?
        """, (property_id,), fetch=True
    )
    
    if result:
        agent_name, meeting_link = result[0]
        return f"Your assigned agent is {agent_name}. You can schedule a meeting here: {meeting_link}"
    else:
        return "No agent found for this property. Please contact support."

def update_property(property_id: str, field: str, new_value: str):
    """Updates a specific field of a property."""
    print(f"[DEBUG] Updating property {property_id} field '{field}' to '{new_value}'")
    
    query = f"UPDATE Property SET {field} = ? WHERE property_id = ?"
    result = execute_query(query, (new_value, property_id))
    
    if result == "Success":
        return f"✅ Property {property_id} updated successfully."
    else:
        return result

def detect_request(user_input: str, default_property_id: Optional[str]) -> Optional[tuple]:
    """Parses user input to detect update or meeting requests."""
    
    pattern = re.search(r"update (\w+) of property (\d+) to (.+)", user_input, re.IGNORECASE)
    if pattern:
        field, property_id, new_value = pattern.groups()
        return ("update", property_id, field, new_value)
    
    if "update" in user_input.lower() and default_property_id:
        pattern = re.search(r"update the (\w+) to (.+)", user_input, re.IGNORECASE)
        if pattern:
            field, new_value = pattern.groups()
            return ("update", default_property_id, field, new_value)
    
    if "meeting" in user_input.lower() or "schedule" in user_input.lower():
        return ("meeting", default_property_id)
    
    return None

def chatbot_logic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Processes user input and updates the conversation state."""
    user_input = state.get("user_input", "")
    
    if state.get("awaiting_phone_number", True):
        state["phone_number"] = user_input
        properties = get_properties(user_input)
        if properties:
            state["linked_properties"] = properties
            state["default_property_id"] = properties[0][0]
            greeting_message = "\nHello! Here are your linked properties:\n"
            for prop in properties:
                greeting_message += f"- {prop[1]} at {prop[2]}\n"
            state["response"] = greeting_message
        else:
            state["response"] = "No properties found for this phone number."
        state["awaiting_phone_number"] = False
    else:
        request_info = detect_request(user_input, state.get("default_property_id"))
        if request_info:
            request_type = request_info[0]
            if request_type == "update":
                _, property_id, field, new_value = request_info
                update_result = update_property(property_id, field, new_value)
                state["response"] = update_result
            elif request_type == "meeting":
                _, property_id = request_info
                meeting_response = get_meeting_link(property_id)
                state["response"] = meeting_response
        else:
            state["response"] = "I didn't understand that. You can update a property by saying 'Update the status to Sold' or request a meeting."
    return state

# Create and compile LangGraph state machine
workflow = StateGraph(state_schema=Dict[str, Any])
workflow.add_node("chatbot_logic", chatbot_logic)
workflow.set_entry_point("chatbot_logic")
compiled_workflow = workflow.compile()

# Start chatbot
def chatbot():
    print("\n🤖 Welcome Flype! Type 'exit' to quit.\n")
    state = {"awaiting_phone_number": True, "user_input": ""}
    
    print("FlypBOT: Please enter your phone number to retrieve linked properties:")
    
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
