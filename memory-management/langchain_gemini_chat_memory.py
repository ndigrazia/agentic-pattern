import os
import warnings

# Suppress LangChain deprecation warnings
warnings.simplefilter("ignore")

from dotenv import load_dotenv

load_dotenv()

# Replace ChatOpenAI with ChatGoogleGenerativeAI (Gemini)
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferMemory
except ImportError:
    from langchain_classic.chains import LLMChain
    from langchain_classic.memory import ConversationBufferMemory

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)

# 1. Define Chat Model and Prompt
# Using Google Gemini chat model
gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
llm = ChatGoogleGenerativeAI(model=gemini_model, temperature=0)

prompt = ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template("You are a friendly assistant."),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)

# 2. Configure Memory
# return_messages=True is essential for chat models so messages stay structured
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
)

# 3. Build the Chain
conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

# 4. Run the Conversation
print("--- Turn 1 ---")
response = conversation.predict(question="Hi, I'm Jane.")
print(response)

print("\n--- Turn 2 ---")
response = conversation.predict(question="Do you remember my name?")
print(response)
