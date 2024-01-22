from openai import OpenAI
import json

client = OpenAI()

# Example dummy function hard coded to return the same weather
# In production, this could be your backend API or an external API
def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": unit})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "32", "unit": unit})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": unit})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})

def run_conversation():
    # Step 1: send the conversation and available functions to the model
    messages = [{"role": "user", "content": "Tell me a joke and then tell me what's the weather like in San Francisco, Tokyo, and Paris?"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    stream = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
        stream=True,
    ) 

    available_functions = {
        "get_current_weather": get_current_weather,
    }  # only one function in this example, but you can have multiple

    response_text = ""
    tool_calls = []

    for chunk in stream:
        delta = chunk.choices[0].delta
        # print(delta)

        if delta and delta.content:
            # content chunk -- send to browser and record for later saving
            print(delta.content)
            response_text += delta.content

        elif delta and delta.tool_calls:
            tcchunklist = delta.tool_calls
            for tcchunk in tcchunklist:
                if len(tool_calls) <= tcchunk.index:
                    tool_calls.append({"id": "", "type": "function", "function": { "name": "", "arguments": "" } })
                tc = tool_calls[tcchunk.index]

                if tcchunk.id:
                    tc["id"] += tcchunk.id
                if tcchunk.function.name:
                    tc["function"]["name"] += tcchunk.function.name
                if tcchunk.function.arguments:
                    tc["function"]["arguments"] += tcchunk.function.arguments    

    # print(tool_calls)

    messages.append(
        {
            "tool_calls": tool_calls,
            "role": 'assistant',
        }                    
    )    

    for tool_call in tool_calls:
        function_name = tool_call['function']['name']
        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_call['function']['arguments'])
        function_response = function_to_call(
            location=function_args.get("location"),
            unit=function_args.get("unit"),
        )
        messages.append(
            {
                "tool_call_id": tool_call['id'],
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
    
    # print(messages)
    
    stream = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        stream=True,
    ) 

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            delta = chunk.choices[0].delta
            print(delta.content, end="")        
            response_text += delta.content

run_conversation()
