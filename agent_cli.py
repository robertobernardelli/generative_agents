from datetime import datetime, timedelta
import json
import threading
import time
from openai import OpenAI

client = OpenAI()


def get_delivery_date(order_id: str) -> datetime:
    # In a real-world scenario, you would query a database or API to get the delivery date
    return datetime.now() + timedelta(days=7)


class AgentCore:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_delivery_date",
                    "description": "Get the delivery date for a customer's order. Call this whenever you need to know the delivery date, for example when a customer asks 'Where is my package'. Ask the user for their order ID and pass it as the 'order_id' parameter (unless you already have it).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "The customer's order ID.",
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
                "content": "You are a helpful customer support assistant. Use the supplied tools to assist the user.",
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
            model="gpt-3.5-turbo", messages=self.messages, tools=self.tools
        )
        message = response.choices[0].message
        self.messages.append(message.to_dict())

        if message.tool_calls is not None:
            while message.tool_calls is not None:
                tool_call = message.tool_calls[0]
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
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.messages,
                    tools=self.tools,
                )
                message = response.choices[0].message
                self.messages.append(message)

            return message.content

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
    print("Autonomous Generative Agent CLI")
    print("Type 'exit' to quit.\n")

    while True:
        user_prompt = input("You: ")
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
        print()


if __name__ == "__main__":
    main()
