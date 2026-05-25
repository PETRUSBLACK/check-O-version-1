"""
Customer AI Shopping Assistant.

Uses Claude API with tool calling to help customers:
- Discover products near them
- Compare prices across shops
- Get personalised recommendations
- Track their orders
- Find deals and flash sales

The assistant has access to real SmartMall data via tools.
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

CUSTOMER_SYSTEM_PROMPT = """You are SmartMall Assistant — a friendly, helpful AI shopping assistant
for SmartMall, a Nigerian local commerce platform where customers find products in physical shops near them.

Your role:
- Help customers find products they're looking for
- Suggest nearby shops with the best prices and ratings
- Recommend products based on their preferences and history
- Help them compare products before buying
- Track their orders
- Alert them to deals and flash sales

Guidelines:
- Always be friendly, conversational and helpful
- Understand Nigerian market context — prices are in Naira (₦)
- If the customer mentions a location or area, factor that into searches
- When you find products, always mention the shop name, price, and rating
- If stock is low, mention it so the customer can decide quickly
- For comparisons, highlight the key differences clearly
- You understand Nigerian English, Pidgin, and formal English equally
- Never make up products or prices — only use data from your tools
- If you can't find something, suggest alternatives or ask clarifying questions
- Always use the search and recommendation tools before answering product questions
- When recommending, explain WHY you're recommending it

Remember: You're helping real Nigerians find real products in real shops near them.
Be accurate, be helpful, and make shopping easier for them."""


CUSTOMER_TOOLS = [
    {
        "name": "search_products",
        "description": "Search for products by name or description. Filter by max price and location to find nearby shops.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Product name or keyword to search for"},
                "max_price": {"type": "number", "description": "Maximum price in Naira"},
                "lat": {"type": "number", "description": "Customer latitude for nearby search"},
                "lng": {"type": "number", "description": "Customer longitude for nearby search"},
                "radius_km": {"type": "number", "description": "Search radius in kilometres (default 10)"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_product_details",
        "description": "Get full details of a specific product including price, stock, shop info and active discounts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The product UUID"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "compare_products",
        "description": "Compare multiple products side by side — price, stock, shop, description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product UUIDs to compare",
                },
            },
            "required": ["product_ids"],
        },
    },
    {
        "name": "find_nearby_shops",
        "description": "Find approved shops near a location, optionally filtered by a product they carry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lng": {"type": "number", "description": "Longitude"},
                "product_query": {"type": "string", "description": "Product to look for in nearby shops"},
                "radius_km": {"type": "number", "description": "Search radius in kilometres"},
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "get_recommendations",
        "description": "Get personalised product recommendations for the customer based on history and location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer UUID"},
                "lat": {"type": "number", "description": "Customer latitude"},
                "lng": {"type": "number", "description": "Customer longitude"},
                "limit": {"type": "integer", "description": "Number of recommendations"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_order_status",
        "description": "Check the status and tracking info of a customer's specific order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order UUID"},
                "customer_id": {"type": "string", "description": "Customer UUID for verification"},
            },
            "required": ["order_id", "customer_id"],
        },
    },
    {
        "name": "get_featured_deals",
        "description": "Get current featured products, flash sales and active discounts on SmartMall.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Customer latitude"},
                "lng": {"type": "number", "description": "Customer longitude"},
                "limit": {"type": "integer", "description": "Number of deals"},
            },
        },
    },
]


class CustomerAssistant:
    """
    Customer-facing AI shopping assistant.
    Maintains conversation history for multi-turn dialogue.
    """

    def __init__(self, customer_id: str = None, customer_lat: float = None, customer_lng: float = None):
        self.customer_id = customer_id
        self.customer_lat = customer_lat
        self.customer_lng = customer_lng
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    def _call_api(self, messages: list) -> dict:
        """Call Claude API with tool use enabled."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "system": CUSTOMER_SYSTEM_PROMPT,
            "tools": CUSTOMER_TOOLS,
            "messages": messages,
        }

        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def _process_tool_calls(self, response: dict, messages: list) -> tuple[list, str | None]:
        """
        Process tool calls from Claude's response.
        Executes each tool and appends results to messages.
        Returns updated messages and final text response if available.
        """
        from ai.tools.smartmall_tools import dispatch_tool

        content = response.get("content", [])
        stop_reason = response.get("stop_reason")

        # Check for text response (no tool calls)
        if stop_reason == "end_turn":
            for block in content:
                if block.get("type") == "text":
                    return messages, block.get("text", "")
            return messages, None

        # Process tool calls
        if stop_reason == "tool_use":
            # Add assistant's response to message history
            messages.append({"role": "assistant", "content": content})

            # Execute each tool call
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block.get("input", {})

                    # Inject customer context automatically
                    if "customer_id" in CUSTOMER_TOOLS[0]["input_schema"]["properties"] and self.customer_id:
                        if tool_name in ("get_recommendations", "get_order_status"):
                            tool_input.setdefault("customer_id", self.customer_id)
                    if self.customer_lat and self.customer_lng:
                        if tool_name in ("search_products", "find_nearby_shops", "get_recommendations", "get_featured_deals"):
                            tool_input.setdefault("lat", self.customer_lat)
                            tool_input.setdefault("lng", self.customer_lng)

                    logger.info("ai_tool_call tool=%s input=%s", tool_name, tool_input)
                    result = dispatch_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result,
                    })

            # Append tool results
            messages.append({"role": "user", "content": tool_results})

        return messages, None

    def chat(self, message: str, conversation_history: list = None) -> dict:
        """
        Send a message to the customer AI assistant.

        Args:
            message: The customer's message
            conversation_history: Previous messages in this conversation

        Returns:
            dict with 'response' (text), 'conversation_history' (updated), 'error' (if any)
        """
        if not self.api_key:
            return {
                "response": "AI assistant is not configured. Please set ANTHROPIC_API_KEY.",
                "conversation_history": conversation_history or [],
                "error": "missing_api_key",
            }

        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": message})

        try:
            # Agentic loop — keep calling API until we get a final text response
            max_iterations = 5
            final_response = None

            for i in range(max_iterations):
                response = self._call_api(messages)
                messages, final_response = self._process_tool_calls(response, messages)

                if final_response is not None:
                    break

                # If no final response yet, continue loop
                if response.get("stop_reason") == "end_turn" and not final_response:
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            final_response = block["text"]
                    break

            if not final_response:
                final_response = "I'm sorry, I couldn't process your request. Please try again."

            # Add final assistant response to history
            messages.append({"role": "assistant", "content": final_response})

            return {
                "response": final_response,
                "conversation_history": messages,
                "error": None,
            }

        except requests.RequestException as exc:
            logger.exception("customer_assistant_api_error")
            return {
                "response": "I'm having trouble connecting right now. Please try again in a moment.",
                "conversation_history": conversation_history or [],
                "error": str(exc),
            }
        except Exception as exc:
            logger.exception("customer_assistant_error")
            return {
                "response": "Something went wrong. Please try again.",
                "conversation_history": conversation_history or [],
                "error": str(exc),
            }
