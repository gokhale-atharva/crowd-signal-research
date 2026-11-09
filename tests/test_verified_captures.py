from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest
from crowd_signal.captures import import_verified_probes, mentions_asset
from crowd_signal.config import load_config, Settings
from crowd_signal.storage import write_json
from crowd_signal.agents.sentiment import SentimentAgent
from crowd_signal.models import Post

NOW=datetime(2026,11,9,4,tzinfo=UTC)

def capture(root, source, rows, name=None):
    folder=Path('data/raw')/(name or source)
    cfg=load_config().exchange('HKEX')
    write_json(root/folder/'manifest.json', {'status':'SUCCEEDED','actor_id':cfg.actor_ids[source],
        'checked_at':NOW.isoformat(),'run_id':name or source,'input':{'searchQuery':'Tencent'}})
    write_json(root/folder/'items.json', rows)
    return {'source':source,'directory':str(folder)}

def row(text, **kw):
    return dict(text=text, own_text=text, title='Tencent 股票 discussion',thread_id='42',
        date=(NOW-timedelta(hours=1)).isoformat(),url='https://example.invalid/post',**kw)

def test_capture_requires_two_actual_sources_per_exchange(tmp_path):
    cfg=load_config().exchange('HKEX')
    selection=[capture(tmp_path,'lihkg',[row('Tencent bullish')])]
    with pytest.raises(ValueError,match='Two-source'):
        import_verified_probes(cfg,tmp_path,selection,NOW)
    partial,coverage=import_verified_probes(cfg,tmp_path,selection,NOW,True)
    assert len(partial)==1 and any(c['source']=='telegram' and c['usable_posts']==0 for c in coverage)
    selection.append(capture(tmp_path,'telegram',[row('Tencent growth')]))
    posts,coverage=import_verified_probes(cfg,tmp_path,selection,NOW)
    assert len(posts)==2
    assert all(c['usable_posts']==0 for c in coverage if c['ticker']=='9988.HK')

def test_capture_rejects_titles_quotes_device_reviews_and_unrelated_replies(tmp_path):
    cfg=load_config().exchange('HKEX')
    rows=[row('Tencent bullish'), row('This refers to a different stock'),row(''),
        {**row(''), 'own_text':None,'content':'Tencent I am long'},
        {**row('小米 tablet review'), 'title':'Tablet discussion','thread_id':'99'}]
    selected=[capture(tmp_path,'lihkg',rows)]
    posts,_=import_verified_probes(cfg,tmp_path,selected,NOW,True)
    assert [p.text for p in posts]==['Tencent bullish']

def test_capture_validates_origin_and_observation_time(tmp_path):
    cfg=load_config().exchange('HKEX')
    selected=[capture(tmp_path,'telegram',[row('Tencent bullish')])]
    with pytest.raises(ValueError,match='observation time'):
        import_verified_probes(cfg,tmp_path,selected,NOW-timedelta(minutes=1),True)
    with pytest.raises(ValueError,match='inside data/raw'):
        import_verified_probes(cfg,tmp_path,[{'source':'telegram','directory':'../outside'}],NOW,True)
    write_json(tmp_path/selected[0]['directory']/'manifest.json',{'status':'SUCCEEDED','actor_id':'wrong'})
    with pytest.raises(ValueError,match='actor'):
        import_verified_probes(cfg,tmp_path,selected,NOW,True)

def test_target_scoring_and_cache_remain_company_specific(tmp_path):
    text='Tencent bullish growth. Alibaba bearish loss.'
    posts=[Post(ticker=t,text=text,source='telegram',url='https://example.invalid/a',timestamp=NOW,observed_at=NOW)
           for t in ['0700.HK','9988.HK']]
    agent=SentimentAgent(Settings(_env_file=None),tmp_path,offline=True,
                         aliases={'0700.HK':['Tencent'],'9988.HK':['Alibaba']})
    scores=agent.score(posts)
    assert scores[0].sentiment>0 and scores[1].sentiment<0
    assert agent.score(posts)==scores and len(list(tmp_path.glob('*.json')))==2
    assert mentions_asset('00700 rallies',['0700'])
    assert not mentions_asset('17000',['0700'])
