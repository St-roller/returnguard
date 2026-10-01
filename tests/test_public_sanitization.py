import copy
import importlib.util
from pathlib import Path
import pytest

path=Path(__file__).parents[1]/'scripts/sanitize_phase3_public.py'
spec=importlib.util.spec_from_file_location('public_sanitizer',path);s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def test_envelope_is_allowlisted_and_all_reasoning_and_headers_are_discarded():
 x={'id':'original','model':'locked','usage':{'input_tokens':2,'output_tokens':3,'cost':.01,'output_tokens_details':{'reasoning_tokens':1,'opaque':'secret'}},'reasoning':{'hidden':'private'},'output':[{'encrypted_content':'private'}],'headers':{'authorization':'private'},'metadata':{'opaque':'secret'}}
 y=s.sanitize_response(x)
 assert set(y)=={'id','model','usage'} and y['id']==s.hash_id('original')
 assert y['usage']=={'input_tokens':2,'output_tokens':3,'cost':.01,'output_tokens_details':{'reasoning_tokens':1}}
 assert 'private' not in str(y) and 'secret' not in str(y)

def test_response_hash_is_deterministic_and_original_record_is_unchanged():
 x={'response_id':'provider-id','raw_structured_extraction':{'score':.86},'gold':{'route':'manual_review'},'latency_seconds':1.23,'reported_usage_cost_usd':.1}
 original=copy.deepcopy(x);a=s.sanitize_record(x);b=s.sanitize_record(x)
 assert a==b and x==original
 assert {k:v for k,v in a.items() if k!='response_id'}=={k:v for k,v in x.items() if k!='response_id'}

def test_non_response_artifacts_are_byte_identical():
 for path in ['results/phase3/test_metrics.json','results/phase3/error_analysis.json','results/phase3/threshold_lock_v1.json']:
  payload=b'{"unchanged": 0.86}\n';assert s.sanitize_bytes(path,payload)==(payload,'byte_identical')

def test_attempt_text_time_usage_and_cost_are_preserved():
 x={'case_id':'test_001','attempt':1,'timestamp':'t','request_binding_sha256':'h','status':'content_response','response':{'id':'id','model':'m','usage':{'input_tokens':1,'cost':.01},'output':[{'type':'reasoning','encrypted_content':'private'}]},'output_text':'{"field":"value"}','latency_seconds':1,'completed_at':'end'}
 b,kind=s.sanitize_bytes('results/phase3/test_attempts/test_001_1.outcome.json',s.encode(x));y=s.json.loads(b)
 assert kind=='provider_envelope_allowlist'
 assert {k:v for k,v in x.items() if k!='response'}=={k:v for k,v in y.items() if k!='response'}
 assert y['response']['usage']==x['response']['usage']

def test_unexpected_attempt_fields_hard_stop():
 with pytest.raises(ValueError,match='unexpected'):
  s.sanitize_bytes('results/phase3/test_attempts/test_001_1.outcome.json',s.encode({'headers':{'secret':'x'}}))

def test_forbidden_payloads_are_rejected_at_any_depth():
 for key in ['encrypted_content','reasoning','reasoning_content','headers','Authorization','api_key']:
  with pytest.raises(ValueError):s.scan_json({'nested':[{'deeper':{key:'x'}}]})

def test_hidden_usage_detail_is_not_retained():
 assert s.sanitize_response({'usage':{'cost_details':{'upstream_inference_cost':.01,'hidden_reasoning':'x'}}})=={'usage':{'cost_details':{'upstream_inference_cost':.01}}}
