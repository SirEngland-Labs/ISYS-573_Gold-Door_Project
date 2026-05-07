"""LangGraph agent — restaurant reservation state machine."""

import os
from typing import TypedDict, Literal, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from app.nodes.router import classify_intent, parse_intent
from app.nodes.reserve import get_reserve_prompt
from app.nodes.faq import get_faq_prompt
from app.nodes.cancel import get_cancel_prompt
from app.tools.booking import make_reservation, cancel_booking
from app.tools.availability import check_table_availability
from app.database import init_db


# --- Agent State ---

class AgentState(TypedDict):
    """State carried through the graph."""
    message: str                          # Current customer message
    phone: str                            # Customer phone number (from Twilio)
    intent: Optional[str]                 # Classified intent
    response: Optional[str]               # Agent response to send back
    history: list[str]                    # Conversation history
    reservation_state: dict               # Partial reservation info being collected


# --- LLM Setup ---

def get_llm():
    """Initialize MiniMax LLM via OpenAI-compatible endpoint."""
    return ChatOpenAI(
        model="MiniMax-M2.7",
        api_key=os.environ.get("MINIMAX_API_KEY"),
        base_url="https://api.minimax.io/v1",
    )


# --- Node Functions ---

def route_node(state: AgentState) -> AgentState:
    """Classify the customer's intent."""
    llm = get_llm()
    prompt = classify_intent(state["message"])
    result = llm.invoke(prompt)
    intent = parse_intent(result.content)
    return {**state, "intent": intent}


def reserve_node(state: AgentState) -> AgentState:
    """Handle reservation flow."""
    llm = get_llm()

    history_str = "\n".join(state.get("history", [])[-10:])
    prompt = get_reserve_prompt(state.get("reservation_state", {}), history_str, state["message"])

    result = llm.invoke(prompt)
    response = result.content

    # Check if the LLM response contains a booking confirmation pattern
    # In a real implementation, you'd use tool calling here
    # For now, the response is the agent's message to the customer

    return {**state, "response": response}


def faq_node(state: AgentState) -> AgentState:
    """Answer FAQ using RAG."""
    llm = get_llm()
    prompt = get_faq_prompt(state["message"])
    result = llm.invoke(prompt)
    return {**state, "response": result.content}


def cancel_node(state: AgentState) -> AgentState:
    """Handle cancellation flow."""
    llm = get_llm()
    prompt = get_cancel_prompt(state.get("phone", "unknown"), state["message"])
    result = llm.invoke(prompt)
    return {**state, "response": result.content}


def off_topic_node(state: AgentState) -> AgentState:
    """Handle off-topic messages."""
    return {
        **state,
        "response": "I'm sorry, I can only help with restaurant reservations, menu questions, and booking management. Is there anything else I can help you with regarding our restaurant?"
    }


# --- Router Edge ---

def route_by_intent(state: AgentState) -> Literal["reserve", "faq", "cancel", "off_topic"]:
    """Route to the appropriate node based on classified intent."""
    return state.get("intent", "off_topic")


# --- Build Graph ---

def create_agent_graph() -> StateGraph:
    """Create and compile the LangGraph agent."""

    # Initialize database
    init_db()

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_node)
    graph.add_node("reserve", reserve_node)
    graph.add_node("faq", faq_node)
    graph.add_node("cancel", cancel_node)
    graph.add_node("off_topic", off_topic_node)

    # Set entry point
    graph.set_entry_point("router")

    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "reserve": "reserve",
            "faq": "faq",
            "cancel": "cancel",
            "off_topic": "off_topic",
        }
    )

    # All handler nodes go to END
    graph.add_edge("reserve", END)
    graph.add_edge("faq", END)
    graph.add_edge("cancel", END)
    graph.add_edge("off_topic", END)

    return graph.compile()


# Module-level compiled graph
agent = create_agent_graph()


def process_message(message: str, phone: str, history: list[str] = None,
                     reservation_state: dict = None) -> str:
    """Process a customer message and return the agent's response.

    Args:
        message: Customer's text message
        phone: Customer's phone number
        history: Previous conversation messages
        reservation_state: Partial reservation info from ongoing booking

    Returns:
        Agent's response text
    """
    state = AgentState(
        message=message,
        phone=phone,
        intent=None,
        response=None,
        history=history or [],
        reservation_state=reservation_state or {},
    )

    result = agent.invoke(state)
    return result.get("response", "I'm sorry, something went wrong. Please try again.")
