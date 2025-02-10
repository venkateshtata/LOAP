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

model = ChatOllama(model="llama3:70b")


@tool
def add(first: int, second: int) -> int:
    "Add two integers."
    return first + second

@tool
def multiply(first: int, second: int) -> int:
    """Multiply two integers together."""
    return first * second

@tool
def converse(input: str) -> str:
    "Provide a natural language response using the user input."
    return model.invoke(input)

@tool
def update_property_status(property_id: int, new_status: str, status_detail: str) -> str:
    """Update the status of a property in the Property table.
    Args:
        property_id (int): The ID of the property to update.
        new_status (str): The new status to set.
        status_detail (str): Additional details about the status.
    Returns:
        str: Confirmation message of the update.
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Property 
            SET status = ?, status_detail = ? 
            WHERE property_id = ?
        """, (new_status, status_detail, property_id))
        conn.commit()
        conn.close()
        return "Property status updated successfully."
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_contractor_data() -> str:
    """Retrieve data about contractors from the Contractor table.
    Args: None
    Returns:
        str: The contractor data as a string.
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Contractor")
        results = cursor.fetchall()
        conn.close()
        return "\n".join([str(row) for row in results]) if results else "No contractor data found."
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_property_data() -> str:
    """Retrieve data about properties from the Property table.
    Args: None
    Returns:
        str: The property data as a string.
    """
    try:
        conn = sqlite3.connect('real_estate.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Property")
        results = cursor.fetchall()
        conn.close()
        return "\n".join([str(row) for row in results]) if results else "No property data found."
    except Exception as e:
        return f"Error: {str(e)}"

# List of tools
tools = [add, multiply, converse, update_property_status, get_contractor_data, get_property_data]
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
    msgs.add_ai_message("I can add, multiply, chat, execute SQL queries, update property status, or retrieve contractor and property data! How can I help you?")

# Set the page title.
st.title("Chatbot with Tools")

# Render the chat history.
for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

# React to user input
if input := st.chat_input("What is up?"):
    # Display user input and save to message history.
    st.chat_message("user").write(input)
    msgs.add_user_message(input)

    # Invoke chain to get response.
    response = chain.invoke({'input': input})

    # Extract the content from AIMessage object
    content = response.content if hasattr(response, 'content') else str(response)

    # Log the model response
    logging.info(f"Model response: {content}")

    # Display AI assistant response and save to message history.
    st.chat_message("assistant").write(content)
    msgs.add_ai_message(content)
