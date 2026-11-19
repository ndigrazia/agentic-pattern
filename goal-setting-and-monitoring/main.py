import os
import random
import re
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Initialize the Language Model using Gemini
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

try:
    print("📡 Initializing language model...")
    llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, temperature=0.3)
    print(f"Language model initialized: {llm.model}")
except Exception as e:
    print(f"Error initializing language model: {e}")
    llm = None

def extract_text(response) -> str:
    """Extracts text content from an LLM response or string."""
    if hasattr(response, "text") and isinstance(response.text, str):
        return response.text
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(part.text)
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)

def generate_prompt(use_case: str, goals: list[str], previous_code: str = "",
    feedback: str = "") -> str:
    print("📝 Constructing prompt for code generation...")
    
    base_prompt = f"""
        You are an AI coding agent. Your job is to write Python code based on the following use case:
        
        Use Case: {use_case}
        
        Your goals are: {chr(10).join(f"- {g.strip()}" for g in goals)}
    """
    
    if previous_code:
        print("🔄 Adding previous code to the prompt for refinement.")
        base_prompt += f"\nPreviously generated code:\n {previous_code}"
    if feedback:
        print("📋 Including feedback for revision.")
        base_prompt += f"\nFeedback on previous version:\n{feedback}\n"

    base_prompt += "\nPlease return only the revised Python code. Do not include comments or explanations outside the code."
    
    return base_prompt

def get_code_feedback(code: str, goals: list[str]) -> str:
    print("🔍 Evaluating code against the goals...")
    
    feedback_prompt = f"""
        You are a Python code reviewer. A code snippet is shown below.
        Based on the following goals: {chr(10).join(f"- {g.strip()}" for g in goals)}

        Please critique this code and identify if the goals are met.
        Mention if improvements are needed for clarity, simplicity, correctness, 
        edge case handling, or test coverage.
        
        Code:
        {code}
    """
    return llm.invoke(feedback_prompt)

def goals_met(feedback_text: str, goals: list[str]) -> bool:
    """
    Uses the LLM to evaluate whether the goals have been met based
    on the feedback text.
    Returns True or False (parsed from LLM output).
    """
    
    review_prompt = f""" 
    You are an AI reviewer. 
    Here are the goals: {chr(10).join(f"- {g.strip()}" for g in goals)}
    
    Here is the feedback on the code: \"\"\"
    {feedback_text}
    \"\"\"

    Based on the feedback above, have the goals been met?
    
    Respond with only one word: True or False.
    """
    
    response = extract_text(llm.invoke(review_prompt)).strip().lower()
    
    return response == "true" or response.rstrip(".").startswith("true")

def clean_code_block(code: str) -> str:
    lines = code.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)

def add_comment_header(code: str, use_case: str) -> str:
    comment = f"# This Python program implements the following use case:\n# {use_case.strip()}\n"
    return comment + "\n" + code

def to_snake_case(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9 ]", "", text)
    return re.sub(r"\s+", "_", text.strip().lower())

def save_code_to_file(code: str, use_case: str) -> str:
    print("💾 Saving final code to file...")
    
    summary_prompt = (
        f"Summarize the following use case into a single lowercase word or phrase, "
        f"no more than 10 characters, suitable for a Python filename:\n\n{use_case}"
    )
    
    raw_summary = extract_text(llm.invoke(summary_prompt)).strip()
       
    short_name = to_snake_case(raw_summary)[:10] or "code"
    
    random_suffix = str(random.randint(1000, 9999))
    filename = f"{short_name}_{random_suffix}.py"
    filepath = Path.cwd() / filename
    
    with open(filepath, "w") as f:
        f.write(code)
        
    print(f"✅ Code saved to: {filepath}")
    
    return str(filepath)

def run_code_agent(use_case: str, goals_input: str, max_iterations:int = 5) -> str:
    goals = [g.strip() for g in goals_input.split(",")]
    
    print(f"\n🎯 Use Case: {use_case}")
    print("🎯 Goals:")
    for g in goals:
        print(f" - {g}")
    
    previous_code = ""
    feedback = ""

    for i in range(max_iterations):
        print(f"\n=== 🔁 Iteration {i + 1} of {max_iterations} ===")
        prompt = generate_prompt(use_case, goals, previous_code, 
                extract_text(feedback) if feedback else "")
        
        print("🚧 Generating code...")
        code_response = llm.invoke(prompt)
        raw_code = extract_text(code_response).strip()
        
        code = clean_code_block(raw_code)
        print("\n🧾 Generated Code:\n" + "-" * 50 + f"\n{code}\n" + "-" * 50)

        print("\n📤 Submitting code for feedback review...")
        feedback = get_code_feedback(code, goals)
        feedback_text = extract_text(feedback).strip()
        
        print("\n📥 Feedback Received:\n" + "-" * 50 + f"\n{feedback_text}\n" + "-" * 50)
        
        if goals_met(feedback_text, goals):
            print("✅ LLM confirms goals are met. Stopping iteration.")
            break

        print("🛠️ Goals not fully met. Preparing for next iteration...")
        
        previous_code = code
    
    final_code = add_comment_header(code, use_case)
    
    return save_code_to_file(final_code, use_case)
        
def main():
    print("🚀 Welcome to the Goal-Setting and Monitoring Code Agent!")
    
    # Example 1
    use_case_input = "Write code to find BinaryGap of a given positive integer"
    goals_input = """Code simple to understand, Functionally correct, Handles comprehensive edge cases, 
    Takes positive integer input only, prints the results with few examples"""

    run_code_agent(use_case_input, goals_input)

if __name__ == "__main__":
    main()
