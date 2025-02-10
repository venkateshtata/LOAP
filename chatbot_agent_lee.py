import sqlite3
import re
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph
from typing import Dict, Any, Optional

# Initialize LLM
llm = OllamaLLM(model="llama3:70b")  # Use an AI model for better language understanding

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

def detect_request(user_input: str, default_property_id: Optional[str]) -> Optional[tuple]:
    """Uses an LLM to understand user input and extract intent dynamically."""
    
    prompt = f"""
    You are a real estate chatbot. Analyze the user's input and classify the intent.
    
    User Input: "{user_input}"
    
    Possible intents:
    - update: User wants to update a property field (e.g., status).
    - meeting: User wants to schedule a meeting with an agent.
    
    Extracted Format:
    - If updating a property: ("update", property_id, status, new_value)
    - If scheduling a meeting: ("meeting", property_id)
    - If unknown: None
    """
    
    llm_response = llm.generate([prompt])
    
    try:
        intent_data = eval(llm_response[0]) if isinstance(llm_response, list) and llm_response else None
        return intent_data
    except Exception as e:
        print("[ERROR] Failed to process intent detection:", e)
        return None

def chatbot_logic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Processes user input and updates the conversation state."""
    user_input = state.get("user_input", "")
    
    if state.get("awaiting_phone_number", True):
        state["phone_number"] = user_input
        properties = execute_query(
            """
            SELECT p.property_id, p.name, p.address FROM Property p
            JOIN Role_map r ON p.property_id = r.property_id
            WHERE r.phone_number = ?
            """, 
            (user_input,), fetch=True
        )
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
                update_result = execute_query(
                    f"UPDATE Property SET {field} = ? WHERE property_id = ?",
                    (new_value, property_id)
                )
                state["response"] = update_result
            elif request_type == "meeting":
                _, property_id = request_info
                meeting_result = execute_query(
                    "SELECT fly_person_name, meeting_link FROM Flyp_contact WHERE property_id = ?",
                    (property_id,), fetch=True
                )
                if meeting_result:
                    agent_name, meeting_link = meeting_result[0]
                    state["response"] = f"Your assigned agent is {agent_name}. Schedule a meeting here: {meeting_link}"
                else:
                    state["response"] = "No agent found for this property. Please contact support."
        else:
            state["response"] = "I didn't understand that. You can update a property, request a meeting, or ask for property details."
    return state

def chatbot():
    """Runs the chatbot in a loop to handle user input."""
    print("\n🤖 Welcome to Flyp! Type 'exit' to quit.\n")
    state = {"awaiting_phone_number": True, "user_input": ""}
    
    print("FlypBOT: Please enter your phone number to retrieve linked properties:")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye! 👋")
            break
        
        state["user_input"] = user_input  # Store user input in state
        state = chatbot_logic(state)  # Process state with chatbot logic
        print("FlypBOT:", state["response"])

# Run chatbot
if __name__ == "__main__":
    chatbot()
