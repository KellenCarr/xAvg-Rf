"""Simple skill: count words/chars/lines in the 'input' field.

Called by the harness with JSON on stdin; prints result text to stdout.
"""
import json
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("error: expected JSON on stdin", file=sys.stderr)
        sys.exit(1)

    text = payload.get("input", "")
    words = len(text.split())
    chars = len(text)
    lines = text.count("\n") + (1 if text else 0)
    print(f"words: {words}\ncharacters: {chars}\nlines: {lines}")


if __name__ == "__main__":
    main()
