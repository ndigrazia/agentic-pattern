import os
import warnings

# Suppress LangChain deprecation warnings
warnings.simplefilter("ignore")

from dotenv import load_dotenv

load_dotenv()

# Replace OpenAI with Google Gemini in LangChain
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferMemory
except ImportError:
    from langchain_classic.chains import LLMChain
    from langchain_classic.memory import ConversationBufferMemory

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate

# 1. Define LLM and Prompt
gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
llm = ChatGoogleGenerativeAI(model=gemini_model, temperature=0)

template = """You are a helpful travel agent.
Previous conversation:
{history}
New question: {question}
Response:"""

prompt = PromptTemplate.from_template(template)

# 2. Configure Memory
# The memory_key "history" matches the variable in the prompt
memory = ConversationBufferMemory(memory_key="history")

# 3. Build the Chain
conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

# 4. Run the Conversation
print("--- Turn 1 ---")
response = conversation.predict(question="I want to book a flight.")
print(response)

print("\n--- Turn 2 ---")
response = conversation.predict(question="My name is Sam, by the way.")
print(response)

print("\n--- Turn 3 ---")
response = conversation.predict(question="What was my name again?")
print(response)

