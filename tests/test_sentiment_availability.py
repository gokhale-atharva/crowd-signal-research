from datetime import UTC, datetime, timedelta
from pathlib import Path
import json

import pandas as pd
import pytest
from typer.testing import CliRunner

from crowd_signal.agents.sentiment import lexicon_extract
from crowd_signal.analytics import build_features, discussion_timeline, ticker_signals
from crowd_signal.cli import app
from crowd_signal.config import Settings, load_config
from crowd_signal.history import retain_first_observations
from crowd_signal.models import NewsItem, Post
from crowd_signal.readiness import require_live_setup

ROOT = Path(__file__).resolve().parents[1]


def post(timestamp, observed, **kwargs):
    return Post(ticker='0700.HK', text='I am long Tencent, bullish growth', source='telegram',
                url='https://example.invalid/post', timestamp=timestamp, observed_at=observed, **kwargs)


def test_no_observations_is_unavailable_but_observed_neutral_is_zero():
    config = load_config().exchange('HKEX')
    bars = pd.read_csv(ROOT / 'data/sample/bars.csv', dtype={'ticker': str, 'session': str})
    bars = bars[bars.ticker.isin([a.ticker for a in config.tickers])]
    now = datetime.fromisoformat(bars.session.max()).replace(tzinfo=UTC) + timedelta(hours=12)
    empty = ticker_signals(config, bars, [], [], [], [], now, 3)
    assert all(s.sentiment is None and s.direction is None for s in empty)
    neutral = post(now - timedelta(hours=1), now).model_copy(update={'text':'Tencent held its annual meeting'})
    actual = ticker_signals(config, bars, [neutral], [], [lexicon_extract(neutral.text)], [], now, 3)
    assert actual[0].sentiment == 0 and actual[0].direction == 'neutral' and actual[0].mentions == 1


def test_retrospective_chart_does_not_backdate_model_features():
    bars = pd.read_csv(ROOT / 'data/sample/bars.csv', dtype={'ticker': str, 'session': str})
    bars = bars[bars.ticker == '0700.HK'].tail(100)
    schedule = json.loads((ROOT / 'data/sample/sessions.json').read_text())['HKEX']
    session = str(bars.session.iloc[-4])
    close = datetime.fromisoformat(next(s['close'] for s in schedule if s['session'] == session))
    now = close + timedelta(hours=1)
    captured = post(close - timedelta(days=2), now)
    score = lexicon_extract(captured.text)
    rows = discussion_timeline([captured], [score], now, 'Asia/Hong_Kong')['0700.HK']
    assert sum(r['posts'] for r in rows) == 1
    assert sum(r['sentiment'] is not None for r in rows) == 1
    assert any(r['sentiment'] is None for r in rows)
    frame = build_features(bars, schedule, [captured], [], [score], [])
    assert frame.loc[frame.session <= session, 'social_available'].sum() == 0
    assert frame.social_available.sum() == 1


def test_repeat_captures_preserve_earliest_text_and_engagement():
    now = datetime(2026, 11, 8, tzinfo=UTC)
    first = post(now - timedelta(days=3), now - timedelta(days=2), likes=2)
    updated = first.model_copy(update={'observed_at':now, 'likes':9000, 'text':'Edited later: bearish'})
    next_post = post(now, now).model_copy(update={'url':'https://example.invalid/another'})
    retained = retain_first_observations([first], [updated, next_post], now)
    assert len(retained) == 2 and retained[0] == first
    assert retained[0].likes == 2 and retained[0].text != updated.text
    # Reversed inputs must still choose earliest observation.
    assert retain_first_observations([updated], [first], now) == [first]
    article = NewsItem(ticker='0700.HK', title='Original', text='Original',
                       url='https://example.invalid/news', timestamp=first.timestamp,
                       retrieved_at=first.observed_at)
    revised = article.model_copy(update={'retrieved_at':now,'text':'Updated later'})
    assert retain_first_observations([article], [revised], now) == [article]
    with pytest.raises(ValueError, match='observation time'):
        retain_first_observations([], [post(now, now + timedelta(seconds=1))], now)


def test_preflight_reports_all_blockers_without_launching_collection(monkeypatch):
    runner = CliRunner()
    def reject_collection(*args, **kwargs):
        raise AssertionError('Incomplete setup must not launch paid source jobs')
    monkeypatch.setattr('crowd_signal.pipeline.Pipeline.collect', reject_collection)
    result = runner.invoke(app, ['run-all', '--exchange', 'ALL', '--mode', 'live'])
    assert result.exit_code == 2
    for name in ('APIFY_TOKEN', 'EXA_API_KEY', 'HKEX/telegram channels', 'KRX/telegram channels', 'KRX/naver_board actor'):
        assert name in result.stdout
    result = runner.invoke(app, ['doctor', '--json', '--strict'])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload['ready_for_live_collection'] is False
    settings = Settings(_env_file=None, apify_token='test-secret', exa_api_key='test-exa')
    with pytest.raises(ValueError) as failure:
        require_live_setup(load_config(), settings, ['HKEX','KRX'])
    assert 'test-secret' not in str(failure.value)


def test_incomplete_stages_cannot_reuse_stale_forecasts(tmp_path, settings, monkeypatch):
    from crowd_signal.pipeline import Pipeline
    from crowd_signal.storage import read_json, write_json
    import crowd_signal.pipeline as module
    pipeline = Pipeline(load_config(), settings, root=tmp_path)
    directory = pipeline.directory('HKEX', 'price_only')
    write_json(directory / 'run.json', {'stages':{'collection':True,'analysis':True,'training':True}})
    write_json(directory / 'forecasts.json', [])
    bars = pd.read_csv(ROOT / 'data/sample/bars.csv', dtype={'ticker':str,'session':str})
    bars = bars[bars.ticker.isin([a.ticker for a in load_config().exchange('HKEX').tickers])].copy()
    bars['provenance'] = 'live'
    def fail_write(*args, **kwargs):
        raise OSError('Interrupted dataset write')
    monkeypatch.setattr(module, 'write_frame', fail_write)
    with pytest.raises(OSError):
        pipeline.save_dataset('HKEX','price_only',bars,[],[],[],datetime.now(UTC),[],capture=False)
    assert not any(read_json(directory / 'run.json')['stages'].values())
    with pytest.raises(ValueError, match='incomplete stages'):
        pipeline.report_packet('HKEX','price_only')
    with pytest.raises(ValueError, match='analyse before train'):
        pipeline.train('HKEX','price_only')
    with pytest.raises(ValueError, match='Complete collection'):
        pipeline.predict('HKEX','price_only',commit=False)
    report = pipeline.report(tmp_path / 'reports')
    assert 'No live posts, prices, sentiment scores or forecasts' in report.read_text(encoding='utf-8')


def test_collection_accumulates_first_seen_observations(tmp_path, monkeypatch):
    from crowd_signal.pipeline import Pipeline
    from crowd_signal.storage import records
    import crowd_signal.pipeline as module
    now = datetime.now(UTC)
    first = post(now - timedelta(days=3), now - timedelta(days=2), likes=2)
    updated = first.model_copy(update={'observed_at':now - timedelta(hours=1),'likes':700})
    added = post(now - timedelta(hours=2), now - timedelta(hours=1)).model_copy(update={'url':'https://example.invalid/new'})
    responses = iter([([first],[]),([updated,added],[])])
    monkeypatch.setattr(module.ApifyCollector, 'validate_sources', lambda *a:None)
    monkeypatch.setattr(module.ApifyCollector, 'collect', lambda *a:next(responses))
    monkeypatch.setattr(module.ExaNewsAgent, 'collect', lambda *a:[])
    bars = pd.read_csv(ROOT / 'data/sample/bars.csv', dtype={'ticker':str,'session':str})
    bars = bars[bars.ticker.isin([a.ticker for a in load_config().exchange('HKEX').tickers])].copy()
    bars['provenance'] = 'live'
    monkeypatch.setattr(module.MarketData, 'collect', lambda *a:bars)
    calendar = pd.DataFrame({'market_open':[pd.Timestamp(now - timedelta(days=1))],
                             'market_close':[pd.Timestamp(now - timedelta(hours=10))]},
                            index=pd.DatetimeIndex([now.date()]))
    monkeypatch.setattr(module, 'exchange_schedule', lambda *a:calendar)
    monkeypatch.setattr(module, 'export_bundle', lambda *a:tmp_path / 'bundle.json')
    settings = Settings(_env_file=None,apify_token='unit-test',exa_api_key='unit-test')
    pipeline = Pipeline(load_config(),settings,root=tmp_path)
    pipeline.collect('HKEX')
    destination = pipeline.collect('HKEX')
    saved = [Post.model_validate(row) for row in records(pd.read_parquet(destination / 'posts.parquet'))]
    assert len(saved) == 2
    original = next(p for p in saved if str(p.url) == str(first.url))
    assert original.likes == 2 and original.observed_at == first.observed_at
