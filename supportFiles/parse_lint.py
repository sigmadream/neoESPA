import sys
import os
import json
import re
import tokenize
from io import BytesIO
from datetime import datetime

parser_mapping = {"p": "pylint", "j": "pmd", "c": "cppcheck"}
cppcheck_severity_mapper = {
    "error": "issue",
    "warning": "issue",
    "portability": "issue",
    "style": "style",
    "performance": "performance",
    "information": "information",
}
pylint_severity_mapper = {
    "fatal": "fatal",
    "error": "issue",
    "warning": "issue",
    "convention": "style",
    "refactor": "performance",
    "information": "information",
}
pmd_severity_mapper = {
    "Best Practices": "issue",
    "Code Style": "style",
    "Design": "style",
    "Error Prone": "issue",
    "Multithreading": "issue",
    "Performance": "performance",
}

message_path = {
    "pylint": "pylint_message.json",
    "pmd": "pmd_message.json",
    "cppcheck": "cppcheck_message.json",
}


def load_rules(parser):
    # 파서 규칙을 로드
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), message_path[parser]
    )
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_token_py(parsed_data, file_path):
    with open(file_path, "rb") as file:
        token_list = []
        ncloc_count = 0
        code = file.read()
        file_content = code.decode("utf-8")
        try:
            for token in tokenize.tokenize(BytesIO(code).readline):
                if (
                    token.type != tokenize.COMMENT
                    and token.type != tokenize.ENDMARKER
                    and token.type != tokenize.ENCODING
                    and token.type != tokenize.NL
                ):
                    token_dict = {
                        "type_code": token.type,
                        "type_name": tokenize.tok_name[token.type],
                        "string": token.string,
                        "start": token.start,
                        "end": token.end,
                        "line": token.line.strip(),
                    }
                    if token.type == tokenize.NEWLINE:
                        ncloc_count += 1
                    token_list.append(token_dict)
        except IndentationError as e:
            print(f"IndentationError|{datetime.now()}|get_token_py()|77")
            print(e)
            print(f"{'-' * 30}")

        token_count = len(token_list)

        parsed_data["files"][file_path]["code"] = file_content
        parsed_data["files"][file_path]["token"] = {
            "ncloc": ncloc_count,
            "count": token_count,
            "list": token_list,
        }

    return parsed_data


def get_ncloc_cppcheck_pmd(parsed_data, file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        parsed_data["files"][file_path]["code"] = "".join(lines)

        ncloc_count = 0
        in_multiline_comment = False

        for line in lines:
            # 여러 줄 주석 시작 처리
            if "/*" in line or "//" in line:
                in_multiline_comment = True

            # 여러 줄 주석 종료 처리
            if "*/" in line:
                in_multiline_comment = False

            # 여러 줄 주석 내부에 있지 않고, 주석이나 빈 라인이 아닌 경우에만 라인 수를 증가시킴
            if not in_multiline_comment and line.strip():
                ncloc_count += 1

        parsed_data["files"][file_path]["token"] = {
            "ncloc": ncloc_count,
        }

    return parsed_data


def parse_results(results, parser):
    parsed_data = {
        "parserName": f"{parser}-parser",
        "parserVersion": "0.0.1",
        "runTime": datetime.now().isoformat(),
        "files": {},
    }

    files_and_folders = os.listdir(os.getcwd())

    if parser == "pylint":
        for py_file in [file for file in files_and_folders if file.endswith(".py")]:
            parsed_data["files"][py_file] = {"lint": [], "code": []}
            get_token_py(parsed_data, py_file)
        parse_pylint(parsed_data, results, parser)
    elif parser == "pmd":
        for java_file in [file for file in files_and_folders if file.endswith(".java")]:
            parsed_data["files"][java_file] = {"lint": [], "code": []}
            get_ncloc_cppcheck_pmd(parsed_data, java_file)
        parse_pmd(parsed_data, results, parser)
    elif parser == "cppcheck":
        for c_file in [
            file
            for file in files_and_folders
            if file.endswith(".cpp") or file.endswith(".c")
        ]:
            parsed_data["files"][c_file] = {"lint": [], "code": []}
            get_ncloc_cppcheck_pmd(parsed_data, c_file)
        parse_cppcheck(parsed_data, results, parser)
    else:
        print(f"Unknown parser option: {parser}")
        sys.exit()

    return parsed_data


def parse_pylint(parsed_data, results, parser):
    rules = load_rules(parser)

    for result in results.split("\n"):
        if not result or "************* " in result:
            continue

        parts = result.split("|")
        (
            severity,
            rule,
            message,
            file_path,
            line_start,
            line_end,
            column_start,
            column_end,
        ) = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
            parts[6],
            parts[7],
        )

        if file_path.endswith(".pylintrc") or file_path == "nofile":
            continue

        parsed_data["files"][file_path]["lint"].append(
            {
                "severity": severity,
                "neo_severity": pylint_severity_mapper[severity],
                "rule": rule,
                "message": (
                    find_sentence(rule, rules, message)
                    if rule in rules
                    else {"eng": message, "kor": ""}
                ),
                "externalURL": f"https://pylint.readthedocs.io/en/stable/user_guide/messages/{severity}/{rule}.html",
                "lineStart": line_start,
                "lineEnd": line_end if line_end else line_start,
                "columnStart": column_start,
                "columnEnd": column_end if column_end else column_start,
            }
        )

    return parsed_data


def find_sentence(rule, rules, message):
    matches = re.findall(rules[rule]["eng"], message)
    sentences = {}

    if matches and matches[0] != message:
        for match in matches:
            sentences["eng"] = message
            try:
                sentences["kor"] = rules[rule]["kor"] % match
            except TypeError as e:
                print(f"TypeError|{datetime.now()}|find_sentence|212")
                print(rules[rule]["eng"])
                print(matches)
                print(rules[rule]["kor"])
                print(e)
                print(f"{'-' * 30}")
                sentences["kor"] = rules[rule]["kor"]
    else:
        sentences["eng"] = rules[rule]["eng"]
        sentences["kor"] = rules[rule]["kor"]

    return sentences if sentences else {"eng": message, "kor": ""}


def parse_pmd(parsed_data, results, parser):
    rules = load_rules(parser)

    pmd_data = json.loads(results)

    for file_data in pmd_data.get("files", []):
        file_name = file_data.get("filename")

        for violation in file_data.get("violations", []):
            if violation.get("ruleset") == "Documentation":
                continue
            lint_entry = {
                "severity": violation.get("ruleset"),
                "neo_severity": pmd_severity_mapper[violation.get("ruleset")],
                "rule": violation.get("rule"),
                "message": (
                    find_sentence(
                        violation.get("rule"), rules, violation.get("description")
                    )
                    if violation.get("rule") in rules
                    else {"eng": violation.get("description"), "kor": ""}
                ),
                "externalURL": violation.get("externalInfoUrl"),
                "lineStart": violation.get("beginline"),
                "lineEnd": violation.get("endline"),
                "columnStart": int(violation.get("begincolumn")) - 1,
                "columnEnd": int(violation.get("endcolumn")) - 1,
            }

            parsed_data["files"][file_name]["lint"].append(lint_entry)

    return parsed_data


def parse_cppcheck(parsed_data, results, parser):
    rules = load_rules(parser)

    for result in results.split("\n"):
        if not result:
            continue

        parts = result.split("|")
        severity, rule, message, file_path, line_start, column_start = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
        )

        if file_path == "nofile":
            continue

        parsed_data["files"][file_path]["lint"].append(
            {
                "severity": severity,
                "neo_severity": cppcheck_severity_mapper[severity],
                "rule": rule,
                "message": (
                    find_sentence(rule, rules, message)
                    if rule in rules
                    else {"eng": message, "kor": ""}
                ),
                "externalURL": "",
                "lineStart": line_start,
                "lineEnd": line_start,
                "columnStart": column_start,
                "columnEnd": column_start,
            }
        )

    return parsed_data


def main():
    # 파이프로 연결되었는지 확인
    # 입력이 파이프로 연결된 경우
    # 모든 입력이 완료될 때까지 기다림
    if not sys.stdin.isatty():
        if len(sys.argv) != 2 or sys.argv[1][0] != "-" or len(sys.argv[1]) != 2:
            print("Usage: python script.py -p|-j|-c")
            sys.exit()

        parser_option = sys.argv[1][1:]

        if parser_option in parser_mapping:
            parser_name = parser_mapping[parser_option]
            read_data = sys.stdin.read()

            parsed_data = parse_results(read_data, parser_name)

            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)

            # JSON을 파일에 저장
            with open("lint_results.json", "w", encoding="utf-8") as json_file:
                json_file.write(formatted_json)
        else:
            print(
                "Unknown parser option. Use -p for pylint, -j for pmd, or -c for cppcheck."
            )
            sys.exit()
    else:
        print("No input received from pipe.")


if __name__ == "__main__":
    main()
