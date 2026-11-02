import uuid
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.workflow import Workflow, START, JoinNode
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, google_search
from google.genai import types
from google.adk.events import Event
import nest_asyncio

load_dotenv()

GEMINI_MODEL="gemini-3.5-flash"

# --- 1. Define Researcher Sub-Agents (to run in parallel) ---
# Researcher 1: Renewable Energy
researcher_agent_1 = LlmAgent(
    name="RenewableEnergyResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in energy.
                Research the latest advancements in 'renewable energy sources'.
                Use the Google Search tool provided.
                Summarize your key findings concisely (1-2 sentences).
                Output *only* the summary.
    """,
    description="Researches renewable energy sources.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="renewable_energy_result"
)

# Researcher 2: Electric Vehicles
researcher_agent_2 = LlmAgent(
    name="EVResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in transportation.
            Research the latest developments in 'electric vehicle technology'.
            Use the Google Search tool provided.
            Summarize your key findings concisely (1-2 sentences).
            Output *only* the summary.
    """,
    description="Researches electric vehicle technology.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="ev_technology_result"
)

# Researcher 3: Carbon Capture
researcher_agent_3 = LlmAgent(
    name="CarbonCaptureResearcher",
    model=GEMINI_MODEL,
    instruction="""You are an AI Research Assistant specializing in climate solutions.
            Research the current state of 'carbon capture methods'.
            Use the Google Search tool provided.
            Summarize your key findings concisely (1-2 sentences).
            Output *only* the summary.
    """,
    description="Researches carbon capture methods.",
    tools=[google_search],
    # Store result in state for the merger agent
    output_key="carbon_capture_result"
)

# --- 2. Create the Parallel Workflow (Runs researchers concurrently) ---
# This workflow orchestrates the concurrent execution of the researchers.
# It finishes once all researchers have completed and stored their results in state.
parallel_research_agent = Workflow(
    name="ParallelWebResearchAgent",
    edges=[
        (START, (researcher_agent_1, researcher_agent_2, researcher_agent_3)),
        ((researcher_agent_1, researcher_agent_2, researcher_agent_3), JoinNode(name="join_researchers")),
    ],
    description="Runs multiple research agents in parallel to gather information."
)

# --- 3. Define the Merger Agent (Runs *after* the parallel agents) ---
# This agent takes the results stored in the session state by the parallel agents
# and synthesizes them into a single, structured response with attributions.
merger_agent = LlmAgent(
    name="SynthesisAgent",
    model=GEMINI_MODEL, # Or potentially a more powerful model if needed for synthesis
    instruction="""You are an AI Assistant responsible for combining research findings into a structured report.
        Your primary task is to synthesize the following research summaries, clearly attributing findings to their source areas. 
        Structure your  response using headings for each topic. Ensure the report is coherent and integrates the key points smoothly.
        **Crucially: Your entire response MUST be grounded *exclusively* on the information provided in the 'Input Summaries' below. 
        Do NOT add any external knowledge, facts, or details not present in these specific summaries.**
        **Input Summaries:**
        
        * **Renewable Energy:**
        {renewable_energy_result}

        * **Electric Vehicles:**
        {ev_technology_result}

        * **Carbon Capture:**
        {carbon_capture_result}
        
        **Output Format:**
        
        ## Summary of Recent Sustainable Technology Advancements
        
        ### Renewable Energy Findings
        (Based on RenewableEnergyResearcher's findings)
        [Synthesize and elaborate *only* on the renewable energy input summary provided above.]

        ### Electric Vehicle Findings
        (Based on EVResearcher's findings)
        [Synthesize and elaborate *only* on the EV input summary provided above.]
        
        ### Carbon Capture Findings
        (Based on CarbonCaptureResearcher's findings)
        [Synthesize and elaborate *only* on the carbon capture input summary provided above.]

        ### Overall Conclusion
        [Provide a brief (1-2 sentence) concluding statement that connects *only* the findings presented above.]
        Output *only* the structured report following this format. Do not include introductory or concluding phrases 
        outside this structure,  and strictly adhere to using only the provided input summary content.
    """,
    description="Combines research findings from parallel agents into a structured, cited report, strictly grounded on provided inputs.",
    # No tools needed for merging
    # No output_key needed here, as its direct response is the final
    # output of the sequence
)

# --- 4. Create the Sequential Workflow (Orchestrates the overall flow) ---
# This is the main workflow that will be run. It first executes the parallel research workflow
# to populate the state, and then executes the MergerAgent to produce the final output.
sequential_pipeline_agent = Workflow(
    name="ResearchAndSynthesisPipeline",
    # Run parallel research first, then merge
    edges=[
        (START, parallel_research_agent),
        (parallel_research_agent, merger_agent),
    ],
    description="Coordinates parallel research and synthesizes the results."
)
root_agent = sequential_pipeline_agent


# --- 5. Execution Logic ---

async def run_pipeline(runner: InMemoryRunner, prompt: str = "Research sustainable technologies"):
    """Runs the parallel research and synthesis pipeline."""
    print(f"\n--- Running Parallel Research & Synthesis Pipeline: '{prompt}' ---")
    final_result = ""
    try:
        user_id = "user_123"
        session_id = str(uuid.uuid4())

        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )

        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=msg,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"\n[{event.author}]:\n{part.text}")
            if event.is_final_response() and event.content:
                if hasattr(event.content, "text") and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    text_parts = [part.text for part in event.content.parts if part.text]
                    final_result = "".join(text_parts)

        print("\n--- Final Synthesized Report ---")
        print(final_result)
        return final_result
    except Exception as e:
        print(f"An error occurred while running the pipeline: {e}")
        return f"An error occurred while running the pipeline: {e}"


async def main():
    """Main function to run the ADK parallelization example."""
    print("--- Google ADK Parallelization Pattern Example ---")
    runner = InMemoryRunner(root_agent)
    await run_pipeline(runner, "Research the latest advancements in sustainable technology.")


if __name__ == "__main__":
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())

