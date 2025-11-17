# ===================================================================================
# Project: ChatSkLearn
# File: src/services/rag/sklearn_graph.py
# Description: Implementation of main SkLearnAssistant Graph
# Author: LALAN KUMAR
# Created: [07-11-2025]
# Updated: [07-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import asyncio
import os
import sys
from typing import Any
from typing_extensions import TypedDict, cast, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, RemoveMessage, AIMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import MemorySaver

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)
    
from src.services.rag.states import AgentState, InputState, Router
from src.services.rag.prompts import (
    ROUTER_SYSTEM_PROMPT,
    GENERAL_SYSTEM_PROMPT,
    MORE_INFO_SYSTEM_PROMPT,
    RESEARCH_PLAN_SYSTEM_PROMPT,
    RESPONSE_SYSTEM_PROMPT
)
from src.config import LLM_MODEL
from src.services.rag.researcher_subgraph import create_researcher_graph

# QueryAnalyzer
async def analyze_and_route_query(
    state: AgentState
) -> dict[str, Any]:
    """Analyze the user's query and determine the appropriate routing"""
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT}
    ] + state["messages"]
    #response = cast(Router, await LLM_MODEL.with_structured_output({"logic": str, "type": str}).ainvoke(messages))
    model= LLM_MODEL.with_structured_output(Router) # Important for Gemini or Antropic models
    response= await model.ainvoke(messages)
    return {"router": response}

# QueryRouter
def route_query(
    state: AgentState,
) -> Literal["create_research_plan", "ask_for_more_info", "respond_to_general_query"]:
    """Determine the next steps based on query classification"""
    _type = state["router"]["type"]
    if _type == "scikit-learn":
        return "create_research_plan"
    elif _type == "more-info":
        return "ask_for_more_info"
    elif _type == "general":
        return "respond_to_general_query"
    else:
        raise ValueError(f"Unknown router type: {_type}")

# ask_for_more_info
async def ask_for_more_info(
    state: AgentState
) -> dict[str, list[BaseMessage]]:
    """Generate a response asking the user for more information"""
    system_prompt = MORE_INFO_SYSTEM_PROMPT.format(logic=state["router"]["logic"])
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = await LLM_MODEL.ainvoke(messages)
    return {"messages": [response]}

# Respond to general query
async def respond_to_general_query(
    state: AgentState
) -> dict[str, list[BaseMessage]]:
    """Generate a response to a general query not related to scikit-learn."""
    system_prompt = GENERAL_SYSTEM_PROMPT.format(
        logic=state["router"]["logic"]
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = await LLM_MODEL.ainvoke(messages)
    return {"messages": [response]}

# Create research plan
async def create_research_plan(
    state: AgentState
) -> dict[str, list[str] | str]:
    """Create a step-by-step research plan for answering a Scikit-learn related query."""

    class Plan(TypedDict):
        """Generate research plan."""
        steps: list[str]

    model = LLM_MODEL.with_structured_output(Plan)
    messages = [
        {"role": "system", "content": RESEARCH_PLAN_SYSTEM_PROMPT}
    ] + state["messages"]
    response = cast(Plan, await model.ainvoke(messages))
    return {"steps": response["steps"], "documents": "delete"}

# Conduct Research
async def conduct_research(state: AgentState) -> dict[str, Any]:
    """Execute the first step of the research plan."""
    researcher_graph = create_researcher_graph()
    result = await researcher_graph.ainvoke({"question": state["steps"][0]})
    
    return {"documents": result["documents"], "steps": state["steps"][1:]}

def check_finished(state: AgentState) -> Literal["respond", "conduct_research"]:
    """Determine if the research process is complete or if more research is needed."""
    if len(state["steps"] or []) > 0:
        return "conduct_research"
    else:
        return "respond"
    

# Conversation summarization node
async def summarize_conversation(
    state: AgentState
) -> dict[str, Any]:
    """Incrementally summarize conversation history and trim old messages."""
    
    # Use .get() with defaults for optional fields
    last_index = state.get("last_summarized_index") or -1
    summary = state.get("summary")
    
    new_messages = state["messages"][last_index + 1 :]
    
    if not new_messages:
        return {}
    
    # Check if we need to summarize
    token_count = count_tokens_approximately(state["messages"])
    if token_count < 1000:
        return {}
    
    if summary:  # Now safely check if summary exists
        prompt = (
            f"This is the existing summary of the conversation:\n{summary}\n\n"
            "Extend the summary by incorporating the following new messages:\n"
        )
    else:
        prompt = "Create a summary of the following conversation messages:\n"
        
    def get_role(message):
        if isinstance(message, HumanMessage):
            return "Human"
        elif isinstance(message, AIMessage):
            return "Assistant"
        elif isinstance(message, SystemMessage):
            return "System"
        else:
            return "Unknown"
    
    # Format new messages as text for summarization
    new_lines = "\n".join(f"{get_role(m)}: {m.content}" for m in new_messages)
    prompt += new_lines + "\n\nNew summary:"
    
    messages = [
        SystemMessage(content="You are an assistant that summarizes the conversation so far. Create a concise summary capturing the key points."),
        HumanMessage(content=prompt)
    ]
    
    summary_response = await LLM_MODEL.ainvoke(messages)
    updated_summary = summary_response.content.strip()
    
    # only the last 3 messages
    num_recent = 3
    messages_to_keep = state["messages"][-num_recent:] if len(state["messages"]) > num_recent else state["messages"]
    
    if len(state["messages"]) > num_recent:
        messages_to_remove = state["messages"][:-num_recent]
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_remove]
    else:
        delete_messages = []
    
    return {
        "summary": updated_summary,
        "last_summarized_index": len(state["messages"]) - num_recent,
        "messages": delete_messages + messages_to_keep,
    }

# Conditional function to decide whether to summarize or continue
def check_summarize(state: AgentState) -> Literal["summarize_conversation", "continue"]:
    """Check if we should summarize conversation"""
    token_count = count_tokens_approximately(state["messages"][:-1])  # Exclude Assistant's new reply
    last_index = state.get("last_summarized_index") or -1
    if token_count >= 1000 and len(state["messages"]) > last_index + 1:
        return "summarize_conversation"
    return "continue"

async def respond(
    state: AgentState
) -> dict[str, list[BaseMessage]]:
    """Generate a final response to the user's query based on the conducted research."""
    
    prompt = RESPONSE_SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": prompt + "\n\nIMPORTANT: Always preserve code blocks with ```python and ``` markers. Never modify code content."}
    ] + state['messages']
    response = await LLM_MODEL.ainvoke(messages)
    return {"messages": [response]}

def create_assistant_graph():
    """Create and return the main agent graph."""
    builder = StateGraph(AgentState, input_schema=InputState)

    builder.add_node("analyze_and_route_query", analyze_and_route_query)
    builder.add_node("ask_for_more_info", ask_for_more_info)
    builder.add_node("respond_to_general_query", respond_to_general_query)
    builder.add_node("conduct_research", conduct_research)
    builder.add_node("create_research_plan", create_research_plan)
    builder.add_node("respond", respond)
    builder.add_node("summarize_conversation", summarize_conversation)
    
    builder.add_edge(START, "analyze_and_route_query")
    
    builder.add_conditional_edges("analyze_and_route_query", route_query)
    
    builder.add_edge("create_research_plan", "conduct_research")
    builder.add_conditional_edges("conduct_research", check_finished)
    
    # After respond, decide whether to summarize or finish
    builder.add_conditional_edges("respond", check_summarize, {
        "summarize_conversation": "summarize_conversation",
        "continue": END
    })
    builder.add_edge("summarize_conversation", END)
    
    builder.add_edge("ask_for_more_info", "create_research_plan")
    builder.add_edge("respond_to_general_query", END)
    
    memory = MemorySaver()

    # Compile into a graph object
    graph = builder.compile(checkpointer=memory)
    graph.name = "SkLearnAssistantGraph"
    
    return graph


# Example usage:
#if __name__ == "__main__":
    #graph=create_assistant_graph()
    #print("Graph compiled successfully.")
    #print(graph.nodes)

    #input_state = AgentState(
        #messages=[HumanMessage(content="How to use RandomForestClassifier?")]
    #)
    # Optionally, define a config with thread_id and user_id for persistence
    #config = {"configurable": {"thread_id": "1", "user_id": "user123"}}

    #result = asyncio.run(graph.ainvoke(input_state,config))
    #print(result)

    #print("------------------------------------------------------------------------------------------",sep="\n")

    #final_response = result["messages"][-1].content
    #print(final_response)