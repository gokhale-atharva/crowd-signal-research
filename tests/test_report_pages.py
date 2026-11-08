from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from crowd_signal.agents.report import ReportAgent
from crowd_signal.config import load_config


def test_portable_site_has_working_page_links_and_companion_assets(tmp_path):
    ReportAgent().preview(load_config(), tmp_path)
    pages = list(tmp_path.glob('*.html'))
    assert len(pages) == 17  # Landing, four areas, ten companies, two legacy exports.
    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
        assert len(soup.find_all('h1')) == 1
        for element in soup.select('a[href],link[href],script[src]'):
            target = urlsplit(element.get('href') or element.get('src'))
            if target.scheme or target.netloc or not target.path:
                continue
            assert (page.parent / unquote(target.path)).is_file(), (page.name, target.path)
    landing = BeautifulSoup((tmp_path / 'index.html').read_text(encoding='utf-8'), 'html.parser')
    assert not landing.select('script[src]')
    assert landing.select_one('.primary-cta')['target'] == '_blank'
    for name in ('hkex', 'krx'):
        legacy = BeautifulSoup((tmp_path / f'{name}.html').read_text(encoding='utf-8'), 'html.parser')
        assert not legacy.select('script[src]')
    methodology = BeautifulSoup((tmp_path / 'methodology.html').read_text(encoding='utf-8'), 'html.parser')
    assert not methodology.select('script[src="assets/data.js"],script[src="assets/plotly.js"],script[src="assets/three.js"]')
