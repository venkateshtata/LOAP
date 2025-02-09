import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import create_react_agent, AgentExecutor, AgentOutputParser

# Initialize database
db = SQLDatabase.from_uri("sqlite:///real_estate.db")
llm = ChatOllama(model="llama3:70b")

# Function to update property status
def update_property_status(input_str: str):
    try:
        parts = input_str.split(",")
        if len(parts) != 2:
            return "Error: Expected input format 'property_id,status'. Example: '1,Sold'"

        property_id, status = parts
        property_id = int(property_id.strip())
        status = status.strip()

        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Property SET status = ? WHERE id = ?", (status, property_id))
            conn.commit()
            return f"✅ Successfully updated property {property_id} to status '{status}'."
    except ValueError:
        return "Error: Property ID must be an integer."
    except Exception as e:
        return f"Error updating property: {e}"

# Function to execute SQL query
def query_database(query: str):
    try:
        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            return str(results)
    except Exception as e:
        return f"Error querying database: {e}"

# Define tools
tools = [
    Tool(
        name="UpdatePropertyStatus",
        func=update_property_status,
        description="Updates the status of a property. Input should be 'property_id,status'. Example: '1,Sold'",
    ),
    Tool(
        name="QueryDatabase",
        func=query_database,
        description="Executes an SQL query against the database. Input should be a valid SQL query.",
    )
]

# Define prompt template
template = """
You are an AI assistant interacting with a SQL database.

### 🚨 STRICT RESPONSE FORMAT:
1. **Tool Call:** 
   Thought: <your reasoning>
   Action: <tool_name>
   Action Input: <input to tool>

2. **Final Answer:** 
   Thought: <your reasoning>
   Final Answer: <your final answer>

---

### ❌ NEVER SAY:
- "I'm ready to assist." 
- "How can I help you?"
- Polite filler phrases.

ONLY respond with Thought, Action, and Action Input, or Final Answer.

### 📋 AVAILABLE TABLES:
{db_tables}

### 🛠️ AVAILABLE TOOLS:
{tool_names}

### USER QUERY:
{input}

{agent_scratchpad}
"""


prompt = PromptTemplate(
    template=template,
    input_variables=["input", "db_tables", "agent_scratchpad", "tool_names", "tools"]
)

# Output Parser
class CustomOutputParser(AgentOutputParser):
    def parse(self, llm_output: str):
        llm_output = llm_output.strip()
        print("\n🔍 RAW LLM OUTPUT:\n", llm_output, "\n")

        # Handle forbidden phrases
        forbidden_phrases = ["I'm here to help.", "How can I assist", "Sure, I can do that."]
        if any(phrase in llm_output for phrase in forbidden_phrases):
            return AgentFinish({"output": "Invalid response: Unnecessary filler text."}, log=llm_output)

        # Handle Final Answer
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            return AgentFinish({"output": final_answer}, log=llm_output)

        # Handle Tool Actions
        if "Action:" in llm_output and "Action Input:" in llm_output:
            try:
                action = llm_output.split("Action:")[1].split("\n")[0].strip()
                action_input = llm_output.split("Action Input:")[1].split("\n")[0].strip()
                return AgentAction(tool=action, tool_input=action_input, log=llm_output)
            except Exception:
                return AgentFinish({"output": "Invalid response format detected."}, log=llm_output)

        return AgentFinish({"output": f"Unstructured response detected: '{llm_output}'"}, log=llm_output)


output_parser = CustomOutputParser()

# Agent Setup
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt.partial(
        tool_names=", ".join([t.name for t in tools]),
        tools=", ".join([t.description for t in tools])  # Added this line
    ),
    output_parser=output_parser
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# Interactive Chat Loop
def interactive_chat():
    conversation_history = ""

    print("💬 Real Estate Agent Bot (type 'exit' to quit)\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break

        # Invoke the agent with conversation context
        response = agent_executor.invoke({
            "input": user_input,  # Make sure this is passed
            "db_tables": db.get_usable_table_names(),
            "agent_scratchpad": conversation_history,
            "tool_names": ", ".join([t.name for t in tools])  # Added this to match prompt variables
        })



        # Display AI's response
        print("AI:", response.get('output'))

        # Append to conversation history
        conversation_history += f"\nUser: {user_input}\nAI: {response.get('output')}\n"

# Start chat
interactive_chat()
