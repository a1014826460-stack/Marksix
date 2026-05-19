"""Clean corrupted UTF-8 characters from route.ts"""
import re

path = r"d:\pythonProject\outsource\Liuhecai\frontend\app\api\kaijiang\[[...path]]\route.ts"

with open(path, 'rb') as f:
    data = f.read()

# Decode with replacement
text = data.decode('utf-8', errors='replace')

lines = text.split('\n')
fixed = []

for line in lines:
    if '�' in line:  # replacement character
        # Remove all non-ASCII from corrupted lines, keep code structure
        # Check line type
        stripped = line.lstrip()
        if stripped.startswith('case ') or stripped.startswith('default:'):
            # Keep the code, strip broken comments
            code_part = re.split(r'\s*//', line, maxsplit=1)[0]
            fixed.append(code_part)
        elif stripped.startswith('//'):
            # Comment-only line with corruption - make it a clean separator
            indent = line[:len(line) - len(stripped)]
            # Count the repeated corruption pattern (it was a long separator)
            if len(stripped) > 40:
                fixed.append(indent + '// ---')
            else:
                fixed.append(indent + '//')
        else:
            # Code line with trailing corrupted comment
            code_part = re.split(r'\s*//', line, maxsplit=1)[0]
            fixed.append(code_part)
    else:
        fixed.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(fixed))

print(f"Cleaned {sum(1 for l in text.split(chr(10)) if chr(0xfffd) in l)} lines")
print("Done")
