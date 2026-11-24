"""Fill @@CODE path start end title@@ lines with the named lines of the robot code, copied verbatim and dedented."""
import re, sys, textwrap, pathlib
REPO = pathlib.Path(sys.argv[1]) / 'src'  # a clone of kl26436/ClaudeBot
OUT = pathlib.Path(__file__).resolve().parents[2] / 'src/content/docs/code'
def code(m):
    path, a, b, title = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip()
    lines = (REPO / path).read_text().split('\n')[a - 1:b]
    body = textwrap.dedent('\n'.join(lines)).rstrip()
    return f'```java title="{title}"\n{body}\n```'
for f in sys.argv[2:]:
    s = pathlib.Path(f).read_text()
    s, n = re.subn(r'^@@CODE (\S+) (\d+) (\d+) (.*?)@@$', code, s, flags=re.M)
    assert '@@' not in s, f
    (OUT / pathlib.Path(f).name).write_text(s); print(f, n, 'excerpts')
