#!/usr/bin/env python3
"""Build the static Cloudflare landing from the shared GitHub Pages sources."""
import argparse
import html
from pathlib import Path
import shutil
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
DEFAULT_URL = 'https://aegis.no-money-do-you-have-money.com/'


def build(output: Path, site_url: str) -> None:
    origin = urlsplit(site_url)
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.port not in (None, 443) or origin.path not in ('', '/') or origin.query or origin.fragment:
        raise ValueError('site-url must be an HTTPS origin without credentials or a path')
    site_url = 'https://' + origin.netloc + '/'
    source = REPO / 'site'
    output = output.resolve()
    if output == source.resolve() or source.resolve() in output.parents:
        raise ValueError('output must be outside the source site directory')
    output.mkdir(parents=True, exist_ok=False)
    for path in sorted(source.rglob('*')):
        if path.name == '.nojekyll':
            continue
        if path.is_symlink() or any(p.startswith('.') for p in path.relative_to(source).parts):
            raise ValueError('source must contain only public regular files and directories')
        if path.is_dir():
            continue
        if path.suffix not in ('.html', '.css', '.jpg', '.svg'):
            raise ValueError('unexpected public source file type')
        if path.suffix != '.html':
            destination = output / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    for language, filename in [('ko', 'ko.html'), ('en', 'index.html')]:
        content = (source / filename).read_text()
        content = content.replace(DEFAULT_URL, html.escape(site_url, quote=True))
        content = content.replace('href="style.css"', 'href="/style.css"').replace('href="assets/', 'href="/assets/').replace('src="assets/', 'src="/assets/')
        content = content.replace('href="./"', 'href="/"').replace('href="index.html"', 'href="/en/"').replace('href="ko.html"', 'href="/"')
        destination = output / language / 'index.html'
        destination.parent.mkdir()
        destination.write_text(content)
        (output / ('ko.html' if language == 'ko' else 'en.html')).write_text(content)
        if language == 'ko':
            (output / 'index.html').write_text(content)
    escaped = html.escape(site_url, quote=True)
    (output / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + site_url + 'sitemap.xml\n')
    (output / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + escaped + '</loc></url><url><loc>' + escaped + 'en/</loc></url></urlset>\n')
    print('Built static landing at ' + str(output))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-url', default=DEFAULT_URL)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.output, args.site_url)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
