# ch17/cases.py
"""The fixed request set: 20 tool-call requests (four tools, all
four offered every time, one call wanted per request) and 20
JSON-schema requests (four schemas). Same requests, same order,
every run."""


def obj(props, **extra):
    return {"type": "object", "properties": props,
            "required": list(props), "additionalProperties": False,
            **extra}


CODE = {"type": "string", "pattern": "^[A-Z]{3}$"}
TOOLS = {
    "get_weather": obj({
        "city": {"type": "string", "minLength": 1},
        "unit": {"enum": ["celsius", "fahrenheit"]}}),
    "convert_currency": obj({
        "amount": {"type": "number", "minimum": 0},
        "from": CODE, "to": CODE}),
    "book_table": obj({
        "restaurant": {"type": "string", "minLength": 1},
        "people": {"type": "integer", "minimum": 1, "maximum": 20},
        "time": {"type": "string",
                 "pattern": "^[0-2][0-9]:[0-5][0-9]$"}}),
    "set_reminder": obj({
        "text": {"type": "string", "minLength": 1},
        "minutes": {"type": "integer", "minimum": 1,
                    "maximum": 1440}}),
}
ASK = {
    "get_weather": [
        "What is the weather in Lisbon, in celsius?",
        "Is it hot in Austin today? Answer in fahrenheit.",
        "Weather for Oslo please, celsius.",
        "How warm is it in Nairobi right now, in celsius?",
        "Tell me the temperature in Denver in fahrenheit."],
    "convert_currency": [
        "Convert 120 EUR to USD.",
        "How many JPY is 50 GBP?",
        "Change 9.99 USD into CAD.",
        "What is 1000 CHF in EUR?",
        "Convert 75 AUD to NZD."],
    "book_table": [
        "Book a table at Nopa for 4 people at 19:30.",
        "Reserve Sushi Ko for 2 at 20:00.",
        "Get me a table at La Tasca for 6 people at 13:15.",
        "Book Blue Door for 3 at 18:45.",
        "I need a table for 8 at Casa Mia at 21:00."],
    "set_reminder": [
        "Remind me to call Ana in 30 minutes.",
        "Set a reminder to stretch in 45 minutes.",
        "In 10 minutes remind me to check the oven.",
        "Remind me in 120 minutes to leave for the airport.",
        "Set a reminder to water the plants in 5 minutes."],
}
SCHEMAS = {
    "person": obj({
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
        "city": {"type": "string", "minLength": 1}}),
    "order": obj({
        "item": {"type": "string", "minLength": 1},
        "quantity": {"type": "integer", "minimum": 1},
        "express": {"type": "boolean"}}),
    "event": obj({
        "title": {"type": "string", "minLength": 1},
        "date": {"type": "string",
                 "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
        "attendees": {"type": "array", "minItems": 1,
                      "items": {"type": "string"}}}),
    "review": obj({
        "label": {"enum": ["positive", "negative", "neutral"]},
        "stars": {"type": "integer", "minimum": 1, "maximum": 5}}),
}
TEXT = {
    "person": ["Maria is 34 and lives in Porto.",
               "Kenji, 51, moved to Osaka last year.",
               "The tenant, Aisha Bello, is 27 and lives in Lagos.",
               "Tom Weber (62) lives in Hamburg.",
               "Lucia lives in Rosario and turned 19 in May."],
    "order": ["Two lamps, express shipping please.",
              "One desk, standard delivery.",
              "I want 12 mugs sent express.",
              "Order 3 chairs, no rush.",
              "Five notebooks, as fast as possible."],
    "event": ["Team offsite on 2026-10-14 with Ana and Raj.",
              "Launch review, 2026-11-02, attendees: Kim, Lee.",
              "Dentist appointment 2026-09-30, just me (Sam).",
              "Book club on 2026-12-05 with Olga, Ben and Zoe.",
              "Quarterly planning 2027-01-08 with the CFO, Dana."],
    "review": ["Great battery, fast shipping. Five stars.",
               "Broke after two days. One star.",
               "It works. Nothing special, three stars.",
               "Lovely fabric, slightly small. Four stars.",
               "Awful support, never again. One star."],
}


def cases():
    tools = [{"type": "function", "function": {
        "name": n, "description": n.replace("_", " "),
        "parameters": s}} for n, s in TOOLS.items()]
    for name, asks in ASK.items():
        for i, q in enumerate(asks):
            yield {"id": f"tool-{name}-{i}", "kind": "tool call",
                   "expect": name, "body": {
                       "messages": [{"role": "user", "content": q}],
                       "tools": tools, "tool_choice": "auto",
                       "parallel_tool_calls": False}}
    for name, texts in TEXT.items():
        for i, t in enumerate(texts):
            ask = f"Extract the {name} as JSON: {t}"
            yield {"id": f"json-{name}-{i}", "kind": "json schema",
                   "expect": name, "body": {
                       "messages": [{"role": "user", "content": ask}],
                       "response_format": {
                           "type": "json_schema", "json_schema": {
                               "name": name, "strict": True,
                               "schema": SCHEMAS[name]}}}}
