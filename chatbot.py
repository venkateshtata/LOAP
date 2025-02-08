from langchain.llms import Ollama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Initialize Ollama (Ensure Ollama is running)
llm = Ollama(model="llama3")

# Initialize memory to remember conversation history
memory = ConversationBufferMemory()

# Initialize Conversation Chain
conversation = ConversationChain(llm=llm, memory=memory)

print("\n🤖 Welcome to the LLaMA 3 Chatbot! Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("Goodbye! 👋")
        break
    
    # Get response from LLaMA 3
    response = conversation.predict(input=user_input)
    
    print("Bot:", response)