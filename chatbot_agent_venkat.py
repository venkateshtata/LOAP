import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import create_react_agent, AgentExecutor, AgentOutputParser

# Initialize database and LLM
db = SQLDatabase.from_uri("sqlite:///real_estate.db")
llm = ChatOllama(model="llama3:70b")

# Utility functions
def update_property_status(input_str: str):
    try:
        input_str = input_str.strip().replace("'", "")  # Remove any quotes
        property_id, status = map(str.strip, input_str.split(","))
        property_id = int(property_id)

        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Property SET status = ? WHERE property_id = ?", (status, property_id))
            conn.commit()
        return f"✅ Successfully updated property {property_id} to status '{status}'."
    except ValueError as ve:
        return f"Error: Invalid format. Ensure input is 'property_id,status' (e.g., '1,Sold'). Details: {ve}"
    except Exception as e:
        return f"Error updating property: {e}"

def query_database(query: str):
    try:
        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return str(cursor.fetchall())
    except Exception as e:
        return f"Error querying database: {e}"

# Load property details based on phone number
def load_property_details(phone_number: str):
    try:
        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.property_id, p.address, p.shortcode, p.name, p.status, p.status_detail
                FROM Property p
                JOIN Role_map r ON p.property_id = r.property_id
                WHERE r.phone_number = ?
            """, (phone_number,))
            property_details = cursor.fetchone()

            if property_details:
                return {
                    "property_id": property_details[0],
                    "address": property_details[1],
                    "shortcode": property_details[2],
                    "name": property_details[3],
                    "status": property_details[4],
                    "status_detail": property_details[5]
                }
            return None
    except Exception as e:
        return f"Error loading property details: {e}"

# Tools
tools = [
    Tool(name="UpdatePropertyStatus", func=update_property_status, description="Updates the status of a property. Input: 'property_id,status' (e.g., '1,Sold')."),
    Tool(name="QueryDatabase", func=query_database, description="Executes an SQL query against the database. Input: valid SQL query.")
]

# Prompt Template
template = """
You are an AI assistant interacting with a SQL database.

### PROPERTY DETAILS:
{property_details}

### 🚨 STRICT RESPONSE FORMAT:
1. **Tool Call:** 
   Thought: <your reasoning>
   Action: <tool_name>
   Action Input: <input to tool> (NO extra quotes or unnecessary characters)

2. **Final Answer:** 
   Thought: <your reasoning>
   Final Answer: <your final answer>

ONLY respond with Thought, Action, and Action Input, or Final Answer.
Decide to use a tool ONLY if it's required based on the user's query. If no tool is needed, respond with a final answer directly.

⚠️ **IMPORTANT:** Do NOT claim a task is completed unless you have successfully executed the tool and received confirmation. If an error occurs, retry with corrections before providing a final answer.

### 📋 AVAILABLE TABLES:
{db_tables}

### 🛠️ AVAILABLE TOOLS:
{tool_names}

### TOOL DESCRIPTIONS:
{tools}

### USER QUERY:
{input}

{agent_scratchpad}
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["input", "db_tables", "agent_scratchpad", "tool_names", "tools", "property_details"]
)

# Custom Output Parser
class CustomOutputParser(AgentOutputParser):
    def parse(self, llm_output: str):
        llm_output = llm_output.strip()

        if "Final Answer:" in llm_output:
            if "Error" in llm_output:
                return AgentFinish({"output": "Task not completed due to an error. Please correct and retry."}, log=llm_output)
            return AgentFinish({"output": llm_output.split("Final Answer:")[-1].strip()}, log=llm_output)

        if "Action:" in llm_output and "Action Input:" in llm_output:
            action = llm_output.split("Action:")[1].split("\n")[0].strip()
            action_input = llm_output.split("Action Input:")[1].split("\n")[0].strip()
            action_input = action_input.replace("'", "")  # Remove extra quotes

            if action == "None":
                return AgentFinish({"output": "No action required."}, log=llm_output)
            return AgentAction(tool=action, tool_input=action_input, log=llm_output)

        return AgentFinish({"output": f"Unstructured response detected: '{llm_output}'"}, log=llm_output)

# Agent Setup
output_parser = CustomOutputParser()
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt.partial(
        tool_names=", ".join(t.name for t in tools),
        tools="\n".join(t.description for t in tools)
    ),
    output_parser=output_parser
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

# Interactive Chat Loop
def interactive_chat():
    phone_number = input("📞 Enter your phone number: ")
    property_details = load_property_details(phone_number)

    print('Got property details: ', property_details)

    if not property_details:
        print("❌ No property found associated with this phone number.")
        return

    conversation_history = ""
    print("💬 Real Estate Agent Bot (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break

        response = agent_executor.invoke({
            "input": user_input,
            "db_tables": db.get_usable_table_names(),
            "agent_scratchpad": conversation_history,
            "tool_names": ", ".join(t.name for t in tools),
            "tools": "\n".join(t.description for t in tools),
            "property_details": property_details
        })

        print("AI:", response.get('output'))
        conversation_history += f"\nUser: {user_input}\nAI: {response.get('output')}\n"

# Start chat
interactive_chat()
