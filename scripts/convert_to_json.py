import sys, json, ast
import pathlib

if len(sys.argv) < 2:
    print('Usage: convert_to_json.py <file>', file=sys.stderr)
    sys.exit(2)

p = pathlib.Path(sys.argv[1])
if not p.exists():
    print(f'File not found: {p}', file=sys.stderr)
    sys.exit(2)

s = p.read_text(encoding='utf-8')
try:
    # Try strict JSON first
    obj = json.loads(s)
    print(json.dumps(obj))
except Exception:
    try:
        # Fallback: parse Python literal (dict) and dump JSON
        obj = ast.literal_eval(s)
        print(json.dumps(obj))
    except Exception as e:
        print(f'Conversion failed: {e}', file=sys.stderr)
        sys.exit(1)
