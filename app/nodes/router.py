"""Router node — classifies customer intent."""

from typing import Literal


ROUTER_PROMPT = """You are an intent classifier for a restaurant reservation system.
Classify the customer's message into exactly ONE of these categories:

- "reserve": Customer wants to make a new reservation or is in the process of providing booking details (name, date, time, party size)
- "faq": Customer is asking about the menu, hours, location, policies, or general restaurant questions
- "cancel": Customer wants to cancel or modify an existing reservation, or look up a reservation
- "off_topic": Message is not related to the restaurant at all

Respond with ONLY the category name, nothing else.

Customer message: {message}"""


def classify_intent(message: str) -> str:
    """Return the router prompt for intent classification.

    The actual LLM call happens in the agent graph — this just provides the prompt.
    """
    return ROUTER_PROMPT.format(message=message)


def parse_intent(llm_response: str) -> Literal["reserve", "faq", "cancel", "off_topic"]:
    """Parse the LLM's intent classification response."""
    response = llm_response.strip().lower().strip('"').strip("'")

    if "reserve" in response or "reservation" in response or "book" in response:
        return "reserve"
    elif "faq" in response or "question" in response or "menu" in response or "hour" in response:
        return "faq"
    elif "cancel" in response or "modify" in response or "change" in response or "lookup" in response:
        return "cancel"
    else:
        return "off_topic"
