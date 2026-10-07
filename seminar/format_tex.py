"""Format Beamer markup without regenerating or replacing slide content."""
from pathlib import Path
import argparse


def balanced(text, start):
    opener = text[start]
    closer = {'{': '}', '[': ']'}[opener]
    depth = 1
    pos = start + 1
    while pos < len(text) and depth:
        if text[pos] == '\\':
            pos += 2
            continue
        if text[pos] == opener:
            depth += 1
        elif text[pos] == closer:
            depth -= 1
        pos += 1
    return pos


def format_latex(source):
    lines = []
    buf = ''
    indent = 0
    i = 0
    def flush():
        nonlocal buf
        if buf.strip():
            lines.append('  ' * indent + buf.strip())
        buf = ''
    while i < len(source):
        if source[i] == '%' and (i == 0 or source[i-1] != '\\'):
            end = source.find('\n', i)
            if end < 0: end = len(source)
            if buf.strip():
                buf += source[i:end]
                flush()
            else:
                lines.append('  ' * indent + source[i:end])
            i = end
            continue
        if source[i] == '\n':
            flush()
            i += 1
            continue
        if source.startswith('\\\\', i):
            buf += '\\\\'
            i += 2
            continue
        command = next((name for name in ('\\begin{', '\\end{', '\\item', '\\[', '\\]', '\\toprule', '\\midrule', '\\bottomrule') if source.startswith(name, i)), None)
        if command is None:
            buf += source[i]
            i += 1
            continue
        flush()
        if command in ('\\begin{', '\\end{'):
            j = source.find('}', i + len(command)) + 1
            if j == 0: raise ValueError('Unclosed environment name')
            if command == '\\begin{':
                # Keep the optional argument and mandatory environment arguments on one line.
                while j < len(source) and source[j] in '[{':
                    j = balanced(source, j)
                token = source[i:j]
                lines.append('  ' * indent + token)
                indent += 1
            else:
                indent = max(0, indent - 1)
                lines.append('  ' * indent + source[i:j])
            i = j
            continue
        if command == '\\item':
            buf = '\\item'
            i += len(command)
            continue
        if command == '\\[':
            lines.append('  ' * indent + '\\[')
            indent += 1
            i += 2
            continue
        if command == '\\]':
            indent = max(0, indent - 1)
            lines.append('  ' * indent + '\\]')
            i += 2
            continue
        lines.append('  ' * indent + command)
        i += len(command)
    flush()
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    source = args.path.read_text()
    args.path.write_text(format_latex(source))
