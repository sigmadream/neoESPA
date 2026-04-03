# eng의 (.+)와 kor의 %[srd]의 개수가 같은지 확인하는 코드
import json
import re

with open("pylint_message.json", "r") as f:
    data = json.load(f)

for key, value in data.items():
    eng_count = len(re.findall(r"\(.\+\)", value["eng"]))
    kor_count = len(re.findall(r"%[srd]", value["kor"]))
    if eng_count != kor_count:
        print(f'Mismatch in "{key}" message')
