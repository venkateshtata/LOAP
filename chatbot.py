import sqlite3
from langchain.llms import Ollama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Database Connection
DB_PATH = "real_estate.db"  # Update with your actual database file

def get_context(phone_number):
    """Fetches chat history, role, property details for the given phone number."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch role and associated property
    cursor.execute("""
        SELECT role, property_id FROM Role_map WHERE phone_number = ?
    """, (phone_number,))
    role_data = cursor.fetchone()
    
    if not role_data:
        conn.close()
        return None  # No role or property found

    role, property_id = role_data

    # Fetch property details
    cursor.execute("""
        SELECT address, status, status_detail FROM Property WHERE property_id = ?
    """, (property_id,))
    property_data = cursor.fetchone()
    
    if not property_data:
        conn.close()
        return None  # No property found

    property_address, property_status, property_status_details = property_data

    # Fetch chat history
    cursor.execute("""
        SELECT chat FROM Conversation WHERE phone_number = ?
    """, (phone_number,))
    chat_history = "\n".join(row[0] for row in cursor.fetchall())

    conn.close()

    # Construct context
    context = f"""
    Role: {role}
    Property Address: {property_address}
    Property Status: {property_status}
    Property Status Details: {property_status_details}
    Previous Chat History:
    {chat_history if chat_history else "No prior conversation found."}
    """

    return context

# Initialize Ollama (Ensure Ollama is running)
llm = Ollama(model="llama3")

print("\n🤖 Welcome to the LLaMA 3 Chatbot! Type 'exit' to quit.\n")

while True:
    phone_number = input("Enter your phone number: ").strip()
    
    # Retrieve contextual information
    context = get_context(phone_number)
    
    if not context:
        print("❌ No data found for this phone number.")
        continue

    # Initialize memory with chat history and property details
    memory = ConversationBufferMemory()
    memory.save_context({"input": "System Context"}, {"output": context})

    print('context', context)

    # Initialize Conversation Chain with memory
    conversation = ConversationChain(llm=llm, memory=memory)

    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye! 👋")
            break

        # Get response from LLaMA 3
        response = conversation.predict(input=user_input)

        print("Bot:", response)
