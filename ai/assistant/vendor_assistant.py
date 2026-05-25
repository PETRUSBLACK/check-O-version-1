"""
Vendor AI Business Assistant.

Helps vendors manage their SmartMall store by:
- Summarising sales performance
- Flagging low stock and pending orders
- Providing demand forecasts
- Suggesting pricing and promotions
- Answering business questions in plain language
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

VENDOR_SYSTEM_PROMPT = """You are SmartMall Business Assistant — an AI assistant that helps
vendors manage their SmartMall store effectively.

Your role:
- Give vendors a clear picture of their sales performance
- Alert them to low stock before they run out
- Help them understand pending orders and what needs to be fulfilled
- Provide demand forecasts so they know what to restock
- Suggest pricing strategies and promotion ideas
- Answer business questions in plain, practical language

Guidelines:
- Always use the available tools to get REAL data before answering
- Speak like a knowledgeable business advisor — practical and direct
- Amounts are in Naira (₦)
- Flag urgent issues (very low stock, many pending orders) prominently
- Give actionable advice, not just information
- If something looks good, say so. If something needs attention, be direct about it.
- You understand the Nigerian market context — Sallah, Christmas, rainy season etc affect demand
- Keep responses concise and business-focused

You're a trusted business partner helping vendors grow their shop on SmartMall."""


VENDOR_TOOLS = [
    {
        "name": "get_vendor_sales_summary",
        "description": "Get a summary of vendor sales — revenue, orders, and top products for a time period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_id": {"type": "string"},
                "days": {"type": "integer", "description": "Number of past days (default 30)"},
            },
            "required": ["business_id"],
        },
    },
    {
        "name": "get_vendor_pending_orders",
        "description": "Get all orders the vendor needs to fulfill right now.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_id": {"type": "string"},
            },
            "required": ["business_id"],
        },
    },
    {
        "name": "get_vendor_low_stock",
        "description": "Get vendor products running low on stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_id": {"type": "string"},
                "threshold": {"type": "integer", "description": "Stock level considered low (default 5)"},
            },
            "required": ["business_id"],
        },
    },
    {
        "name": "get_demand_forecast",
        "description": "Get ML-based demand forecast — which products to restock and when.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_id": {"type": "string"},
            },
            "required": ["business_id"],
        },
    },
]


class VendorAssistant:
    """Vendor-facing AI business assistant."""

    def __init__(self, business_id: str):
        self.business_id = business_id
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    def _call_api(self, messages: list) -> dict:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "system": VENDOR_SYSTEM_PROMPT,
            "tools": VENDOR_TOOLS,
            "messages": messages,
        }
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def _process_tool_calls(self, response: dict, messages: list) -> tuple[list, str | None]:
        from ai.tools.smartmall_tools import dispatch_tool

        content = response.get("content", [])
        stop_reason = response.get("stop_reason")

        if stop_reason == "end_turn":
            for block in content:
                if block.get("type") == "text":
                    return messages, block["text"]
            return messages, None

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content})
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_input = block.get("input", {})
                    # Auto-inject business_id
                    tool_input.setdefault("business_id", self.business_id)
                    logger.info("vendor_ai_tool tool=%s", block["name"])
                    result = dispatch_tool(block["name"], tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

        return messages, None

    def chat(self, message: str, conversation_history: list = None) -> dict:
        """Send a message to the vendor AI assistant."""
        if not self.api_key:
            return {
                "response": "AI assistant not configured. Set ANTHROPIC_API_KEY.",
                "conversation_history": conversation_history or [],
                "error": "missing_api_key",
            }

        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": message})

        try:
            max_iterations = 5
            final_response = None

            for _ in range(max_iterations):
                response = self._call_api(messages)
                messages, final_response = self._process_tool_calls(response, messages)
                if final_response is not None:
                    break
                if response.get("stop_reason") == "end_turn":
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            final_response = block["text"]
                    break

            if not final_response:
                final_response = "I couldn't process that request. Please try again."

            messages.append({"role": "assistant", "content": final_response})
            return {"response": final_response, "conversation_history": messages, "error": None}

        except Exception as exc:
            logger.exception("vendor_assistant_error")
            return {
                "response": "Something went wrong. Please try again.",
                "conversation_history": conversation_history or [],
                "error": str(exc),
            }
