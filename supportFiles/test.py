import json

with open("pylint_message.json", "r") as f:
    data = json.load(f)

for key, value in data.items():
    if "%s" in value["eng"] or "%d" in value["eng"] or "%r" in value["eng"]:
        print(f'Found in "{key}" message')
