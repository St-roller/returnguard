"""Deterministic publication projection and offline equivalence audit; no model calls."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/phase3'
PRIVATE_SHA='375026564d47e37c7bf1683e52820bc20014494608fc5bddb948d2d60a661bc4'
VERSION='phase3_public_sanitization_v1'
POLICY={
 'version':VERSION,'response_id_transform':'sha256: + SHA256(UTF-8 original ID)',
 'provider_response_allowlist':['id','model','status','created_at','completed_at','usage'],
 'usage_allowlist':['input_tokens','output_tokens','total_tokens','cost','input_tokens_details','output_tokens_details','cost_details'],
 'usage_detail_allowlist':['cached_tokens','cache_write_tokens','reasoning_tokens','upstream_inference_cost','upstream_inference_input_cost','upstream_inference_output_cost'],
 'removed':'All other provider-envelope fields, including output/reasoning objects, encrypted content, headers, credentials and opaque provider identifiers. Exact output_text and structured extraction retained.',
 'unchanged':'All semantic prediction fields, scored gold, policy/threshold/baseline/config locks, metrics, error analysis, input projections, token/latency/cost metadata and historical source hashes.',
 'scope':'Both Phase 3A dev and Phase 3B test at the current branch tip; no history rewrite.',
 'model_calls_authorized':0,
}
FORBIDDEN={'encrypted_content','reasoning','reasoning_content','hidden_reasoning','thinking','chain_of_thought','headers','authorization','api_key','access_token','refresh_token'}

def digest(b):return hashlib.sha256(b).hexdigest()
def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def jsonl(rows):return ''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for x in rows).encode()
def read_rows(b):return [json.loads(x) for x in b.splitlines() if x.strip()]
def hash_id(value):
 if value is None:return None
 if not isinstance(value,str):raise ValueError('response ID must be text or null')
 return 'sha256:'+digest(value.encode())

def sanitize_record(record):
 result=copy.deepcopy(record)
 if 'response_id' in result:result['response_id']=hash_id(result['response_id'])
 return result

def sanitize_response(response):
 allowed={k:copy.deepcopy(response[k]) for k in POLICY['provider_response_allowlist'] if k in response and k!='usage'}
 if 'id' in allowed:allowed['id']=hash_id(allowed['id'])
 usage=response.get('usage') or {};safe={}
 for k in POLICY['usage_allowlist']:
  if k not in usage:continue
  value=usage[k]
  if isinstance(value,dict):value={d:v for d,v in value.items() if d in POLICY['usage_detail_allowlist']}
  safe[k]=copy.deepcopy(value)
 allowed['usage']=safe
 scan_json(allowed)
 return allowed

def sanitize_bytes(path,data):
 if re.fullmatch(r'results/phase3/(dev|test)_attempts/[^/]+\.outcome\.json',path):
  x=json.loads(data)
  expected={'case_id','attempt','timestamp','request_binding_sha256','status','response','output_text','latency_seconds','completed_at'}
  if set(x)-expected:raise ValueError('unexpected attempt fields: '+path)
  if x.get('status')!='content_response':raise ValueError('only observed content responses are supported by publication v1')
  # Avoid permissive recursive scrubbing: discard the provider envelope except allowlisted fields.
  x['response']=sanitize_response(x['response'])
  return encode(x),'provider_envelope_allowlist'
 if re.fullmatch(r'results/phase3/(dev|test)_cases/[^/]+\.json',path):return encode(sanitize_record(json.loads(data))),'response_id_hash'
 if re.fullmatch(r'results/phase3/(dev|test)_predictions_(raw|scored)\.jsonl',path):return jsonl([sanitize_record(x) for x in read_rows(data)]),'response_id_hash'
 return data,'byte_identical'

def scan_json(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower().replace('-','_') in FORBIDDEN:raise ValueError('forbidden public payload key: '+k)
   scan_json(v)
 elif isinstance(x,list):
  for v in x:scan_json(v)
 elif isinstance(x,str):
  if 'sk-or-v1-' in x or re.search(r'(?i)\bbearer\s+[a-z0-9._-]{12,}',x):raise ValueError('credential-like public string')

def private_files(package):
 if digest(package.read_bytes())!=PRIVATE_SHA:raise ValueError('private complete package digest mismatch')
 with zipfile.ZipFile(package) as z:
  hashes=json.loads(z.read('FILES_SHA256.json'))
  for name,sha in hashes.items():
   if digest(z.read(name))!=sha:raise ValueError('private entry hash mismatch: '+name)
  return {name[len('project/'):]:z.read(name) for name in z.namelist() if name.startswith('project/results/phase3/') or name in ['project/docs/Phase3_Formal_Evaluation_Handoff.md','project/docs/Phase3B_Verification_Notes.md']}

def prepare(package):
 files=private_files(package)
 # Verify every source currently present before replacing a single public byte.
 for name,data in files.items():
  p=ROOT/name
  sanitized,_=sanitize_bytes(name,data)
  if p.exists() and p.read_bytes() not in (data,sanitized):raise ValueError('source differs from preserved package: '+name)
 for name,data in files.items():
  payload,_=sanitize_bytes(name,data);p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
 (OUT/'sanitization_policy_v1.json').write_bytes(encode(POLICY))
 report=equivalence(package)
 (OUT/'sanitization_equivalence_v1.json').write_bytes(encode(report))
 print(json.dumps(report,ensure_ascii=False))

def equivalence(package):
 files=private_files(package);changed=[];identical=[];ids=set();case_n={};semantic_rows=0;envelopes=0
 for name,original in files.items():
  expected,kind=sanitize_bytes(name,original);public=(ROOT/name).read_bytes()
  if public!=expected:raise ValueError('deterministic projection mismatch: '+name)
  if kind=='byte_identical':identical.append(name)
  else:changed.append({'path':name,'transform':kind,'original_sha256':digest(original),'public_sha256':digest(public)})
  if name.endswith('.json'):scan_json(json.loads(public))
  elif name.endswith('.jsonl'):
   for row in read_rows(public):scan_json(row)
  if kind=='provider_envelope_allowlist':
   a=json.loads(original);b=json.loads(public);envelopes+=1;ids.add(a['response']['id'])
   assert a['output_text']==b['output_text']
   assert {k:v for k,v in a.items() if k!='response'}=={k:v for k,v in b.items() if k!='response'}
   assert b['response']['id']==hash_id(a['response']['id'])
  if re.fullmatch(r'results/phase3/(dev|test)_predictions_(raw|scored)\.jsonl',name):
   a=read_rows(original);b=read_rows(public);assert len(a)==len(b)==90
   for x,y in zip(a,b):
    assert {k:v for k,v in x.items() if k!='response_id'}=={k:v for k,v in y.items() if k!='response_id'}
    assert y['response_id']==hash_id(x['response_id']);semantic_rows+=1
   case_n[name]=len(b)
 for name in files:
  data=(ROOT/name).read_bytes()
  if any(response_id.encode() in data for response_id in ids):raise ValueError('unhashed provider response ID retained: '+name)
 assert envelopes==180 and semantic_rows==360
 # Recompute from public data with locked deterministic offline scoring only.
 sys.path.insert(0,str(ROOT/'src'))
 from returnguard import eval_metrics as m,heldout_scoring as h
 from returnguard.keyword_baseline import load_patterns,run_baseline
 from returnguard.policy import Policy
 for split in ('dev','test'):
  raw=read_rows((OUT/f'{split}_predictions_raw.jsonl').read_bytes())
  scored=read_rows((OUT/f'{split}_predictions_scored.jsonl').read_bytes())
  gold=read_rows((ROOT/f'data/returnguard_synth_v1/{split}.jsonl').read_bytes())
  joined=m.join_gold(raw,gold)
  if split=='dev':joined=[m.apply_threshold(x,.86) for x in joined]
  assert joined==scored
  calc=m.metrics(scored,dev_selected=True) if split=='dev' else h.heldout_metrics(scored)
  if split=='dev':calc.update(status='DEV_COMPLETE_PENDING_GATE_3A_APPROVAL',provisional_threshold=.86)
  assert calc==json.loads((OUT/f'{split}_metrics.json').read_bytes())
  inputs=read_rows((OUT/f'{split}_inputs.jsonl').read_bytes())
  baseline=[run_baseline(x,Policy(),load_patterns()) for x in inputs]
  assert jsonl(baseline)==(OUT/f'baseline_{split}_predictions.jsonl').read_bytes()
  baseline_scored=m.join_gold(baseline,gold)
  calc=m.metrics(baseline_scored) if split=='dev' else h.heldout_metrics(baseline_scored,baseline=True)
  if split=='dev':calc['error_capture']={'value':None,'display':'N/A: deterministic baseline has no confidence threshold'}
  assert calc==json.loads((OUT/f'baseline_{split}_metrics.json').read_bytes())
  if split=='test':assert h.error_analysis(scored,inputs,baseline_scored)==json.loads((OUT/'error_analysis.json').read_bytes())
 return {'version':VERSION,'status':'PASS','private_full_package_sha256':PRIVATE_SHA,'additional_model_calls':0,
  'private_source_files_verified':len(files),'byte_identical_file_n':len(identical),'metadata_transformed_file_n':len(changed),
  'provider_envelopes_projected_n':envelopes,'prediction_rows_semantically_identical_n':semantic_rows,
  'case_counts':case_n,'structured_outputs_scores_routes_gold_unchanged':True,'all_metrics_and_error_analysis_byte_identical':True,
  'threshold_config_baseline_authorization_and_source_hash_records_byte_identical':True,
  'baseline_predictions_byte_identical':True,'token_latency_cost_values_unchanged':True,
  'gold_join_metrics_baseline_error_analysis_offline_recomputed':True,'forbidden_payload_keys_and_plain_response_ids_absent':True,
  'changed_files':changed,'byte_identical_files':identical,
  'hash_interpretation':'Historical freeze/package/summary hash records describe the private original bytes. public_artifact_manifest.json hashes current sanitized public bytes. No historical hash or experimental result was rewritten.'}

def manifest():
 paths=list(OUT.rglob('*'))
 paths += [ROOT/'docs'/n for n in ('Phase3A_Dev_Evaluation_Handoff.md','Phase3A_Verification_Notes.md','Phase3_Formal_Evaluation_Handoff.md','Phase3B_Verification_Notes.md','Phase3_Publication_Sanitization.md')]
 cfg=json.loads((OUT/'eval_config_v1.json').read_bytes());paths += [ROOT/p for p in cfg['implementation_sha256']]
 paths += [ROOT/p for p in ('.github/workflows/phase2a-blueprint-validation.yml','scripts/sanitize_phase3_public.py','tests/test_public_sanitization.py','baselines/keyword_rules_v1.json','src/returnguard/keyword_baseline.py','data/returnguard_synth_v1/dev.jsonl','data/returnguard_synth_v1/test.jsonl','data/returnguard_synth_v1/freeze_manifest.json')]
 paths=sorted(set(p for p in paths if p.is_file() and p.name!='public_artifact_manifest.json'))
 obj={'version':'phase3_public_artifact_manifest_v1','sanitization_version':VERSION,'private_full_package_sha256':PRIVATE_SHA,'model_calls_for_publication':0,'formal_evaluation_status':'CLOSED_GATE_3B_APPROVED','sha256':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths},'historical_hash_scope':'Original experiment/private bytes; current public bytes are bound by this manifest.','manifest_self_excluded':True}
 (OUT/'public_artifact_manifest.json').write_bytes(encode(obj));verify_public()

def verify_public():
 manifest=json.loads((OUT/'public_artifact_manifest.json').read_bytes())
 assert manifest['private_full_package_sha256']==PRIVATE_SHA
 for name,sha in manifest['sha256'].items():
  data=(ROOT/name).read_bytes();assert digest(data)==sha,name
  if name.startswith('results/phase3/'):
   if name.endswith('.json'):scan_json(json.loads(data))
   elif name.endswith('.jsonl'):
    for x in read_rows(data):scan_json(x)
 cfg=json.loads((OUT/'eval_config_v1.json').read_bytes())
 for name,sha in cfg['implementation_sha256'].items():assert digest((ROOT/name).read_bytes())==sha
 assert digest((ROOT/'data/returnguard_synth_v1/test.jsonl').read_bytes())==cfg['test_sha256']
 assert digest((ROOT/'data/returnguard_synth_v1/dev.jsonl').read_bytes())==cfg['dev_sha256']
 assert json.loads((OUT/'threshold_lock_v1.json').read_bytes())['value']==.86
 for split in ('dev','test'):
  rows=read_rows((OUT/f'{split}_predictions_raw.jsonl').read_bytes());assert len(rows)==90
  assert [r['case_id'] for r in rows]==[f'{split}_{i:03d}' for i in range(1,91)]
  assert all(re.fullmatch(r'sha256:[a-f0-9]{64}',r['response_id']) for r in rows)
 print(json.dumps({'status':'PASS','public_manifest_files':len(manifest['sha256']),'model_calls':0,'private_full_package_sha256':PRIVATE_SHA}))

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','check','manifest','verify-public']);parser.add_argument('--private-package',type=Path);args=parser.parse_args()
 if args.command in ('prepare','check') and args.private_package is None:parser.error('--private-package required')
 if args.command=='prepare':prepare(args.private_package)
 elif args.command=='check':
  report=equivalence(args.private_package);assert encode(report)==(OUT/'sanitization_equivalence_v1.json').read_bytes();print(json.dumps({'status':'PASS','model_calls':0,'private_source_files_verified':report['private_source_files_verified']}))
 elif args.command=='manifest':manifest()
 else:verify_public()

if __name__=='__main__':main()
