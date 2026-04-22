import json

with open('D:/it/cla-ai-ala/prepsensei/backend/data/question_bank.json', encoding='utf-8') as f:
    raw = f.read()


def fix_json_strings(s):
    """Walk char-by-char; escape any double-quote that appears inside a JSON
    string value but does not actually terminate it."""
    out = []
    i = 0
    n = len(s)
    in_string = False
    escape_next = False

    while i < n:
        ch = s[i]

        if escape_next:
            out.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == '\\':
            out.append(ch)
            escape_next = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                in_string = True
                out.append(ch)
                i += 1
                continue
            else:
                # Peek ahead past whitespace to decide if this closes the string
                j = i + 1
                while j < n and s[j] in ' \t':
                    j += 1
                nxt = s[j] if j < n else ''
                if nxt in (',', '}', ']', '\n', '\r', ':'):
                    # Legitimate closing quote
                    in_string = False
                    out.append(ch)
                    i += 1
                    continue
                else:
                    # Unescaped inner quote — escape it
                    out.append('\\')
                    out.append('"')
                    i += 1
                    continue

        out.append(ch)
        i += 1

    return ''.join(out)


fixed = fix_json_strings(raw)

try:
    data = json.loads(fixed)
    print(f'JSON valid: {len(data)} entries')
    with open('D:/it/cla-ai-ala/prepsensei/backend/data/question_bank.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('Written back OK')
except json.JSONDecodeError as e:
    print(f'Still invalid: {e}')
    pos = e.pos
    print('Context:', repr(fixed[max(0, pos - 60):pos + 60]))
