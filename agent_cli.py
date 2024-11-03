from datetime import datetime, timedelta
import json
import threading
import time
from openai import OpenAI
import logging
import os
from tools import get_delivery_date, get_order_status, get_order_shipping_address

# Set up logging
filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(filename="logs/" + filename, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("[%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)
# Disable OpenAI and httpx logging
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

# Initialize the OpenAI client
client = OpenAI()
CHATGPT_MODEL = "gpt-4-turbo"


class AgentCore:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_delivery_date",
                    "description": "Get the delivery date for a customer's order. Call this whenever you need to know the delivery date, for example when a customer asks 'When is my order coming?'. Ask the user for their order ID and pass it as the 'order_id' parameter (unless you already have it).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "The customer's order ID, provided by the user.",
                            },
                        },
                        "required": ["order_id"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_status",
                    "description": "Get the status of a customer's order. Call this whenever you need to know the status of an order, for example when a customer asks 'What is the status of my order?'. Ask the user for their order ID and pass it as the 'order_id' parameter (unless you already have it).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "The customer's order ID, provided by the user.",
                            },
                        },
                        "required": ["order_id"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_shipping_address",
                    "description": "Get the shipping address for a customer's order. Call this whenever you need to know the shipping address of an order, for example when a customer asks 'Where is my order being shipped?'. Ask the user for their order ID and pass it as the 'order_id' parameter (unless you already have it).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "The customer's order ID, provided by the user.",
                            },
                        },
                        "required": ["order_id"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

        self.functions = {
            tool["function"]["name"]: globals()[tool["function"]["name"]]
            for tool in self.tools
            if tool["type"] == "function"
        }

        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful customer support assistant. Use the supplied tools to assist the user. When a user asks for the status of the order, they want to know both the status and the expected delivery date, so you can call multiple tools. The latest order ID is # 306-3621584-1622342. Always specify the order ID when talking about an order.",
            }
        ]

    def call_function(self, function_name, arguments=None):
        if function_name in self.functions:
            return self.functions[function_name](**arguments)
        else:
            raise ValueError(f"Function '{function_name}' is not available.")

    def respond_to_prompt(self, prompt):
        self.messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=CHATGPT_MODEL, messages=self.messages, tools=self.tools
        )
        message = response.choices[0].message
        self.messages.append(message.to_dict())

        if message.tool_calls is not None:
            debug_str = "\n\n[DEBUG]\nTo answer this question, the bot used the following Tools:"
            while message.tool_calls is not None:

                for tool_call in message.tool_calls:

                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    function_response = self.call_function(function_name, arguments)
                    function_call_result_message = {
                        "role": "tool",
                        "content": json.dumps(
                            {
                                "arguments": arguments,
                                "function_output": str(function_response),
                            }
                        ),
                        "tool_call_id": tool_call.id,
                    }
                    self.messages.append(function_call_result_message)

                    debug_str += f"\n- {function_name}() with arguments: {arguments}; returned: {function_response}"

                response = client.chat.completions.create(
                    model=CHATGPT_MODEL,
                    messages=self.messages,
                    tools=self.tools,
                )

                message = response.choices[0].message
                self.messages.append(message)
                output = message.content
                output += debug_str
                
            return output

        else:
            return message.content


def spinner():
    while True:
        for cursor in "|/-\\":
            yield cursor


def animate_spinner(spinner_generator):
    while not stop_spinner.is_set():
        print(f"\rThinking... {next(spinner_generator)}", end="", flush=True)
        time.sleep(0.1)
    print("\r                 ")  # Clear the spinner line


# CLI functionality
def main():
    agent = AgentCore()
    print("Generative Agent CLI")
    print("Type 'exit' to quit.\n")
    print("--------------------------------------------------\n")

    while True:
        
        user_prompt = input("You: ")
        print("\n--------------------------------------------------")
        if user_prompt.lower() == "exit":
            print("Exiting.")
            break

        # Call the agent to respond to the user's prompt and animate a spinner while waiting
        global stop_spinner
        stop_spinner = threading.Event()
        spinner_gen = spinner()
        spinner_thread = threading.Thread(target=animate_spinner, args=(spinner_gen,))
        spinner_thread.start()
        response = agent.respond_to_prompt(user_prompt)
        stop_spinner.set()
        spinner_thread.join()  # Wait for the spinner thread to finish

        print("Agent:", response)
        print("\n--------------------------------------------------\n")


if __name__ == "__main__":
    main()
