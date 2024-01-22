from openai import OpenAI
import json
import requests
import os

client = OpenAI()

def get_current_weather(location, unit='Celsius'):
    # Retrieve the API key from the environment variable
    api_key = os.getenv('OPENWEATHER_API_KEY')

    # Base URL for the OpenWeather API
    base_url = "https://api.openweathermap.org/data/2.5/weather?"

    formatted_location = location.replace(" ", "+")

    # Convert the unit parameter to the format required by the API
    api_units = {'Celsius': 'metric', 'Fahrenheit': 'imperial', 'Kelvin': 'standard'}.get(unit, 'metric')

    # Construct the full URL with parameters
    full_url = f"{base_url}q={formatted_location}&units={api_units}&appid={api_key}"

    try:
        # Make the API call
        response = requests.get(full_url)

        # Check if the response is successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Extract and format the weather data
            weather = {
                'location': data['name'],
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed']
            }
            return json.dumps(weather)
        else:
            # Handle HTTP errors
            print(f"Weather Error: {response.status_code} - {response.reason}")
            return f"Weather Error: {response.status_code} - {response.reason}"
    except requests.exceptions.RequestException as e:
        # Handle exceptions in making the API request
        print(f"Weather error occurred: {e}")
        return f"Weather error occurred: {e}"

def run_conversation():
    # Step 1: send the conversation and available functions to the model
    messages = [{"role": "user", "content": "Tell me a joke and then tell me what's the weather like in New York City, Tokyo, and Paris?"}]
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
                            "description": "The city and state, e.g. San Francisco",
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
