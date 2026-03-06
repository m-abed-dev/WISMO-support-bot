import streamlit as st
import json
import os
from openai import OpenAI


client = OpenAI(
  base_url="https://api.groq.com/openai/v1",
  api_key=st.secrets["GROQ_API_KEY"],
)

def check_order_status(order_id: str):
    """Checks the status of an order."""
    mock_db = {
        "ORD-123": "Shipped",
        "ORD-456": "Processing",
        "ORD-789": "Delivered"
    }
    status = mock_db.get(order_id.upper(), "Order not found.")
    return json.dumps({"order_id": order_id, "status": status})

def process_return(order_id,reason:str):
    """Processes a return for a given order."""

    tracking_number = f"RET-{hash(order_id) % 10000}"
    return json.dumps(
        {"status": "success", "return_tracking_number": tracking_number, "message": f"Return processed for {reason}"})



available_functions = {
    "check_order_status": check_order_status,
    "process_return": process_return
}

SYSTEM_PROMPT ="""
You are a friendly, concise, and helpful customer support agent for a e-commerce store.
Your primary job is to help users with 'Where is my Order' (WISMO) requests and process returns.

RULES:
1. NEVER guess an order status. Always ask the user their Order ID and use the 'check_order_status' tool.
2. If the user wants to return an item, ask for the Order ID and the reason, then use the `process_return` tool.
3. If the user asks about anything outside of orders and returns (e.g., technical support, company history), politely redirect them to the correct department and explain your limitations.



"""
tools = [
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Get the current status of a customer's order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g., ORD-123"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_return",
            "description": "Process a return for a customer's order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g., ORD-123"},
                    "reason": {"type": "string", "description": "The reason for the return"},
                },
                "required": ["order_id", "reason"],
            },
        },
    }
]

st.set_page_config(page_title="WISMO Support Bot", page_icon="📦")
st.title("📦 WISMO Customer Support")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]


for message in st.session_state.messages:
    if message["role"] != "system" and message["role"] != "tool":

        if not message.get("tool_calls"):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


if prompt := st.chat_input("Hi! How can I help you with your order today?"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)


    with st.chat_message("assistant"):
        message_placeholder = st.empty()


        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=st.session_state.messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = response.choices[0].message


        tool_calls = response_message.tool_calls

        if tool_calls:

            st.session_state.messages.append(response_message)


            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)


                function_response = function_to_call(**function_args)


                st.session_state.messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )


            second_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=st.session_state.messages
            )
            final_reply = second_response.choices[0].message.content
            message_placeholder.markdown(final_reply)
            st.session_state.messages.append({"role": "assistant", "content": final_reply})

        else:

            final_reply = response_message.content
            message_placeholder.markdown(final_reply)
            st.session_state.messages.append({"role": "assistant", "content": final_reply})