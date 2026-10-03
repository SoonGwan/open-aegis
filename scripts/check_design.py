"""Validate selected UI text/background pairs against WCAG AA contrast."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tokens = json.loads((ROOT / 'web/src/design/montage-semantic.json').read_text())['themes']['light']


def rgba(value):
    h = value.lstrip('#')
    return [int(h[i:i+2], 16)/255 for i in (0, 2, 4)] + [int(h[6:8] or 'FF', 16)/255]


def composite(value, background):
    r = rgba(value)
    return [r[i]*r[3] + background[i]*(1-r[3]) for i in range(3)]


def luminance(rgb):
    return sum(weight*(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4)
               for c, weight in zip(rgb, (.2126, .7152, .0722)))


pairs = [
    ('body', tokens['label']['normal'], tokens['background']['normal']['normal']),
    ('support text', tokens['label']['neutral'], tokens['background']['normal']['normal']),
    ('support text on alternate', tokens['label']['neutral'], tokens['background']['normal']['alternative']),
    ('primary action', tokens['static']['white'], tokens['primary']['normal']),
    ('primary hover', tokens['static']['white'], tokens['primary']['strong']),
    ('hero', tokens['label']['normal'], tokens['accent']['background']['lightBlue']),
    ('status positive', tokens['label']['normal'], tokens['background']['status']['positive']),
    ('status cautionary', tokens['label']['normal'], tokens['background']['status']['cautionary']),
    ('status negative', tokens['label']['normal'], tokens['background']['status']['negative']),
]
failed = []
for name, foreground, background in pairs:
    bg = composite(background, [1, 1, 1])
    fg = composite(foreground, bg)
    a, b = sorted((luminance(fg), luminance(bg)))
    ratio = (b+.05)/(a+.05)
    print(f'{name}: {ratio:.2f}:1')
    if ratio < 4.5:
        failed.append(name)
if failed:
    raise SystemExit('AA contrast failed: ' + ', '.join(failed))
css = (ROOT / 'web/src/style.css').read_text()
import re
if re.search(r'#[0-9a-fA-F]{3,8}\b', css):
    raise SystemExit('Literal color found outside design tokens')
print('Selected pairs pass AA; full rendered accessibility audit is separate.')
