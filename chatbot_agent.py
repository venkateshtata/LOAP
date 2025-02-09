import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import create_react_agent, AgentExecutor, AgentOutputParser

# Initialize database
db = SQLDatabase.from_uri("sqlite:///real_estate.db")
llm = ChatOllama(model="llama3")

# Function to update property status
# Function to update property status
def update_property_status(input_str: str):
    try:
        parts = input_str.split(",")
        if len(parts) != 2:
            return "Error: Expected input format 'property_id,status'. Example: '1,Sold'"
        
        property_id, status = parts
        property_id = int(property_id.strip())  # Ensure ID is an integer
        status = status.strip()  # Ensure status is properly formatted
        
        with sqlite3.connect("real_estate.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Property SET status = ? WHERE id = ?", (status, property_id))
            conn.commit()
            return f"Successfully updated property {property_id} to status '{status}'."
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
        description="Updates the status of a property. Input should be a string in the format 'property_id,status'. Example: '1,Sold'",
    ),
    Tool(
        name="QueryDatabase",
        func=query_database,
        description="Executes a SQL query against the database. Input should be a valid SQL query.",
    )
]


# Define structured prompt
template = """You are an AI agent that interacts with a SQL database.

You must strictly follow this response format:

- If calling a tool, respond exactly as follows:
    Thought: <your_reasoning> Action: <tool_name> Action Input: <input_to_tool>

- If providing a final answer, respond exactly as follows:
    Thought: <your_reasoning> Final Answer: <your_final_answer>

### **Strict Rules:**
- Do **not** ask for clarification.
- Do **not** add any extra text.
- Do **not** say "I'm ready to assist!" or similar phrases.
- Always return a valid response in the required format.

Available database tables: {db_tables}

Available tools: {tool_names}

Example tool usage:
- Update property status:
    Thought: The user wants to update the status of property 1 to 'Sold'. Action: UpdatePropertyStatus Action Input: "1,Sold"
- Run a database query:
    Thought: The user wants to retrieve the first 10 properties. Action: QueryDatabase Action Input: "SELECT * FROM Property LIMIT 10;"

{agent_scratchpad}"""

print("template: ", template)

prompt = PromptTemplate(
    template=template, 
    input_variables=["input", "db_tables", "agent_scratchpad", "tool_names", "tools"]
)


# LLMChain (using RunnableSequence)
llm_chain = prompt | llm

# Output Parser with improved error handling
class CustomOutputParser(AgentOutputParser):
    def parse(self, llm_output: str):
        llm_output = llm_output.strip()

        # Debug print
        print("\n🔍 RAW LLM OUTPUT:\n", llm_output, "\n")

        if "Final Answer:" in llm_output and "Action:" in llm_output:
            raise ValueError(f"Invalid response! Cannot contain both 'Final Answer:' and 'Action:'. LLM output: {llm_output}")

        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            return AgentFinish({"output": final_answer}, log=llm_output)

        if "Action:" in llm_output and "Action Input:" in llm_output:
            lines = llm_output.split("\n")
            action = next((line.split("Action:")[-1].strip() for line in lines if "Action:" in line), None)
            action_input = next((line.split("Action Input:")[-1].strip() for line in lines if "Action Input:" in line), None)

            if action and action_input:
                return AgentAction(tool=action, tool_input=action_input, log=llm_output)

        raise ValueError(f"Invalid format! Could not parse LLM output:\n{llm_output}")



output_parser = CustomOutputParser()

# Create the agent with correct variable substitution
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt.partial(tool_names=", ".join([t.name for t in tools]), tools=str(tools))
)

# Create the agent executor with error handling
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True  # Allows retries when parsing fails
)

# Execute the agent
agent_executor.invoke({
    "input": "Update the status of property_id 1 as 'Sold' in the property table",
    "db_tables": db.get_usable_table_names(),
    "agent_scratchpad": ""
})

# Run a database query to check the update
print(db.run("SELECT * FROM Property LIMIT 10;"))
