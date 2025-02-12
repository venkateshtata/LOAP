import streamlit as st  # to render the user interface.
import sqlite3  # to connect to SQLite database
import logging  # to log model responses and tool usage
from langchain_community.llms import Ollama  # to use Ollama llms in langchain
from langchain_core.prompts import ChatPromptTemplate  # crafts prompts for our llm
from langchain_community.chat_message_histories import StreamlitChatMessageHistory  # stores message history
from langchain_core.tools import tool  # tools for our llm
from langchain.tools.render import render_text_description  # to describe tools as a string
from langchain_core.output_parsers import JsonOutputParser  # ensure JSON input for tools
from operator import itemgetter  # to retrieve specific items in our chain.
from langchain_ollama import ChatOllama

# Configure logging
logging.basicConfig(filename='chatbot_logs.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

model = ChatOllama(model="llama3.3:70b")

# Modal to get phone number
if 'phone_number' not in st.session_state:
    with st.form(key='phone_form'):
        phone_number = st.text_input("Enter your phone number:", max_chars=15)
        submit_button = st.form_submit_button(label='Submit')
        if submit_button and phone_number:
            st.session_state.phone_number = phone_number


@tool
def converse(input: str) -> str:
    "Provide a natural language response using the user input."
    return model.invoke(input)

@tool
def update_property_status(property_identifier: str, new_status: str, status_detail: str = "") -> str:
    """Update the status and status_detail of a property in the real estate database.
    This tool should be used when you need to change a property's status, such as marking it as 'Sold', 
    'Available', 'Under Contract', 'Pending', etc. The status change helps track the current state of properties
    in the real estate inventory. You can identify the property using its ID, address, shortcode, or name.

    Args:
        property_identifier (str): The property identifier - can be property_id, address, shortcode or name
        new_status (str): The new status to set for the property (e.g. 'Sold', 'Available', 'Under Contract')
        status_detail (str, optional): Additional details about the status change. Defaults to empty string.

    Returns:
        str: A message confirming the status update was successful, or an error message if it failed
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        
        # First try to find the property using the provided identifier
        cursor.execute("""
            SELECT property_id FROM Property 
            WHERE property_id = ? OR address = ? OR shortcode = ? OR name = ?
        """, (property_identifier, property_identifier, property_identifier, property_identifier))
        
        result = cursor.fetchone()
        if not result:
            return f"Error: No property found matching identifier '{property_identifier}'"
            
        property_id = result[0]
        
        # Update both status and status_detail
        cursor.execute("""
            UPDATE Property 
            SET status = ?, status_detail = ?
            WHERE property_id = ?
        """, (new_status, status_detail, property_id))
        
        conn.commit()
        conn.close()
        
        update_msg = f"Property {property_identifier} status successfully updated to '{new_status}'"
        if status_detail:
            update_msg += f" with details: '{status_detail}'"
        return update_msg
        
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_property_status(property_identifier: str) -> str:
    """Retrieve status and status details for a specific property.
    Args:
        property_identifier: The property's address, shortcode, or name to look up
    Returns:
        str: The property's status information as a string
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        
        # Try to find the property using the provided identifier
        cursor.execute("""
            SELECT status, status_detail 
            FROM Property 
            WHERE address = ? OR shortcode = ? OR name = ?
        """, (property_identifier, property_identifier, property_identifier))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No property found matching identifier '{property_identifier}'"
            
        status, status_detail = result
        response = f"Property '{property_identifier}' status: {status}"
        if status_detail:
            response += f"\nDetails: {status_detail}"
        return response
        
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_meeting_link(fly_person_name: str) -> str:
    """Retrieve a meeting link for scheduling a meeting with a specific fly person.
    This tool helps coordinate meetings by providing the appropriate video conferencing link
    for the specified fly team member.
    
    Args:
        fly_person_name: The name of the fly team member you want to meet with
        
    Returns:
        str: The meeting link for the specified person, or an error message if the person is not found
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT meeting_link
            FROM Flyp_contact 
            WHERE fly_person_name = ?
        """, (fly_person_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No meeting link found for fly team member '{fly_person_name}'"
            
        meeting_link = result[0]
        return f"Meeting link for {fly_person_name}: {meeting_link}"
        
    except Exception as e:
        return f"Error retrieving meeting link: {str(e)}"


# List of tools
tools = [converse, update_property_status, get_property_status, get_meeting_link]
rendered_tools = render_text_description(tools)

parser = JsonOutputParser()


system_prompt = f"""You are an assistant that has access to the following set of tools.
Here are the names and descriptions for each tool:

{rendered_tools}

Given the user input, return the name and input of the tool to use.
Return your response as a JSON blob with 'name' and 'arguments' keys.
The value associated with the 'arguments' key should be a dictionary of parameters.

{parser.get_format_instructions()}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "{input}")
])


def tool_chain(model_output):
    tool_map = {tool.name: tool for tool in tools}
    chosen_tool = tool_map[model_output["name"]]

    # Log the tool selection and arguments
    logging.info(f"Model selected tool: {model_output['name']} with arguments: {model_output['arguments']}")

    return itemgetter("arguments") | chosen_tool

chain = prompt | model | JsonOutputParser() | tool_chain 

# Set up message history.
msgs = StreamlitChatMessageHistory(key="langchain_messages")
if len(msgs.messages) == 0:
    msgs.add_ai_message("I can retreive and update your property statuses")

# Set the page title.
st.title("Flyp AI")

# Render the chat history.
for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

# React to user input
if input := st.chat_input("What is up?"):
    # Append phone number to the message
    phone_number = st.session_state.get('phone_number', 'Unknown')
    input_with_phone = f"[Phone: {phone_number}] {input}"

    # Display user input and save to message history.
    st.chat_message("user").write(input_with_phone)
    msgs.add_user_message(input_with_phone)

    # Invoke chain to get response.
    response = chain.invoke({'input': input_with_phone})

    # Extract the content from AIMessage object
    content = response.content if hasattr(response, 'content') else str(response)

    # Log the model response
    logging.info(f"Model response: {content}")

    # Display AI assistant response and save to message history.
    st.chat_message("assistant").write(content)
    msgs.add_ai_message(content)
