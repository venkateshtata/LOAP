import sqlite3
from langchain.llms import Ollama
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool
from langchain.tools import tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

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

def get_context(phone_number):
    """Fetches chat history, role, and property details for a given phone number."""
    print(f"[DEBUG] Fetching context for phone number: {phone_number}")
    
    role_data = execute_query(
        """
        SELECT role, property_id FROM Role_map WHERE phone_number = ?
        """, 
        (phone_number,), fetch=True
    )
    
    if not role_data:
        print("[DEBUG] No role data found.")
        return None
    
    role, property_id = role_data[0]
    
    property_data = execute_query(
        """
        SELECT address, status, status_detail FROM Property WHERE property_id = ?
        """, 
        (property_id,), fetch=True
    )
    
    if not property_data:
        print("[DEBUG] No property data found.")
        return None
    
    property_address, property_status, property_status_details = property_data[0]
    
    chat_history = execute_query(
        """
        SELECT chat FROM Conversation WHERE phone_number = ?
        """, 
        (phone_number,), fetch=True
    )
    
    chat_history_text = "\n".join(row[0] for row in chat_history) if chat_history else "No prior conversation."
    
    context = f"""
    Role: {role}
    Property Address: {property_address}
    Property Status: {property_status}
    Property Status Details: {property_status_details}
    Previous Chat History:
    {chat_history_text}
    """
    
    return context

@tool("update_property_status", return_direct=True)
def update_property_status(property_id: str, new_status: str, new_status_detail: str):
    """Updates the status and status details of a property."""
    print(f"[DEBUG] Updating property {property_id} to status '{new_status}', details '{new_status_detail}'")
    
    result = execute_query(
        """
        UPDATE Property SET status = ?, status_detail = ? WHERE property_id = ?
        """, 
        (new_status, new_status_detail, property_id)
    )
    
    if result == "Success":
        return f"Property {property_id} updated successfully."
    else:
        return result

@tool("update_role", return_direct=True)
def update_role(phone_number: str, new_role: str):
    """Updates the role of a user based on phone number."""
    print(f"[DEBUG] Updating role for {phone_number} to '{new_role}'")
    
    result = execute_query(
        """
        UPDATE Role_map SET role = ? WHERE phone_number = ?
        """, 
        (new_role, phone_number)
    )
    
    if result == "Success":
        return f"Role for {phone_number} updated successfully."
    else:
        return result

# Initialize LLM and agent
llm = Ollama(model="llama3")

# Define tools
tools = [update_property_status, update_role]

agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

print("\n🤖 Welcome to the Agent-based LLaMA 3 Chatbot! Type 'exit' to quit.\n")

while True:
    phone_number = input("Enter your phone number: ").strip()
    
    context = get_context(phone_number)
    
    if not context:
        print("❌ No data found for this phone number.")
        continue
    
    print("[DEBUG] Context retrieved:\n", context)
    
    memory = ConversationBufferMemory()
    memory.save_context({"input": "System Context"}, {"output": context})
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye! 👋")
            break
        
        try:
            response = agent_executor.run(user_input)
            print("Bot:", response)
        except Exception as e:
            print("[ERROR] Agent execution failed:", e)
