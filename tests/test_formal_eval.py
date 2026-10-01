import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from returnguard import formal_eval as f
from returnguard.eval_metrics import apply_threshold, join_gold, metrics, support_diagnostic, threshold_table, wilson
from returnguard.keyword_baseline import extract, load_patterns, run_baseline, validate_evidence
from returnguard.schemas import Extraction


def candidate(score=.9, route="eligible", gold="eligible", status="completed", reason=None):
    raw = {k: {"value": v, "evidence": ["吊牌还在"], "support_score": score}
           for k,v in zip(Extraction.model_fields, ("ordinary_return", "attached", "absent", "no"))}
    return {"case_id": "dev_001", "evaluation_status": status,
            "validated_extraction": raw if status == "completed" else None, "raw_structured_extraction": raw,
            "candidate_route": route if status == "completed" else None,
            "candidate_rule_id": "EL01_7DAY", "case_support_score": score,
            "final_route": route if status == "completed" else "manual_review", "review_reason": reason,
            "gold": {"decision": {"route": gold, "rule_id": "EL01_7DAY"}, "extraction": raw}}


def fake_client(create):
    return SimpleNamespace(responses=SimpleNamespace(create=create))


def response(raw, model=f.MODEL):
    text = json.dumps(raw, ensure_ascii=False)
    return SimpleNamespace(output_text=text, model=model,
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
        model_dump=lambda **kw: {"model": model, "usage": {"input_tokens": 10, "output_tokens": 20, "cost": .001}, "id": "fixture"})


def projection(smoke_cases):
    case = smoke_cases[0]
    return {"case_id": "dev_001", "split": "dev", "input": case.input.model_dump(mode="json")}


def test_freeze_verifies_and_mismatch_stops(tmp_path):
    f.verify_freeze()
    # Check hash mismatch before any client could be constructed.
    base = tmp_path / "data/returnguard_synth_v1"
    base.mkdir(parents=True)
    (base / "freeze_manifest.json").write_text(json.dumps({"git_commit": f.DATA_COMMIT, "dev_sha256": "wrong", "test_sha256": f.TEST_HASH}))
    with pytest.raises(f.HardStop, match="identity"):
        f.verify_freeze(tmp_path)


def test_request_is_existing_contract_only_and_durable(tmp_path, smoke_cases):
    row = projection(smoke_cases)
    raw = {k: {**v, "support_score": .95} for k,v in smoke_cases[0].gold["extraction"].items()}
    calls = []
    def create(**kw):
        calls.append(kw)
        return response(raw)
    caller = f.FormalCaller(fake_client(create), f.ROOT / "prompts/extraction_v1.md", tmp_path)
    result, attempts = caller.collect(row)
    assert result.raw == raw and len(attempts) == 1
    call = calls[0]
    assert set(call) == {"model", "input", "text", "tools"}
    assert call["model"] == f.MODEL and call["tools"] == []
    assert call["input"][1] == {"role": "user", "content": row["input"]["customer_message"]}
    assert call["text"]["format"]["schema"] == Extraction.model_json_schema()
    assert call["text"]["format"]["strict"] is True
    assert "gold" not in call and "case_id" not in call
    assert smoke_cases[0].review_metadata["english_annotation"] not in repr(call)
    assert (tmp_path / "dev_attempts/dev_001_1.outcome.json").exists()
    # Replaying stored content does not issue another model call.
    caller.collect(row)
    assert len(calls) == 1


@pytest.mark.parametrize("raw", ["refusal", {"invalid": True}])
def test_content_failure_is_not_retried(tmp_path, smoke_cases, raw):
    calls=[]
    caller=f.FormalCaller(fake_client(lambda **kw: (calls.append(kw),response(raw))[1]), f.ROOT/'prompts/extraction_v1.md',tmp_path)
    cfg={"dataset_version":"ReturnGuard-Synth-v1", "dev_sha256":f.DEV_HASH,"eval_config_version":"formal_eval_v1.0","prompt_sha256":"fixture"}
    r=f.predict(projection(smoke_cases),caller,cfg,'fixture','fixture')
    assert r['evaluation_status']=='validation_failure' and r['request_attempts']==1
    assert len(calls)==1 and r['final_route']=='manual_review' and 'gold' not in r


def test_retry_exhaustion_is_exactly_three(tmp_path, smoke_cases):
    calls=[]
    def fail(**kw):
        calls.append(kw)
        raise TimeoutError()
    caller=f.FormalCaller(fake_client(fail), f.ROOT/'prompts/extraction_v1.md',tmp_path,sleep=lambda _:None)
    cfg={"dataset_version":"ReturnGuard-Synth-v1", "dev_sha256":f.DEV_HASH,"eval_config_version":"formal_eval_v1.0","prompt_sha256":"fixture"}
    r=f.predict(projection(smoke_cases),caller,cfg,'fixture','fixture')
    assert len(calls)==3 and calls[0]==calls[1]==calls[2]
    assert r['evaluation_status']=='execution_failure' and r['review_reason']=='execution_failure'
    caller.collect(projection(smoke_cases))
    assert len(calls)==3


def test_transient_then_content_retries_identical_request(tmp_path, smoke_cases):
    calls=[]
    def create(**kw):
        calls.append(kw)
        if len(calls)<3:
            raise ConnectionError()
        return response({})
    caller=f.FormalCaller(fake_client(create), f.ROOT/'prompts/extraction_v1.md',tmp_path,sleep=lambda _:None)
    _, attempts=caller.collect(projection(smoke_cases))
    assert len(attempts)==3 and calls[0]==calls[1]==calls[2]


def test_model_substitution_stops_and_keeps_response(tmp_path, smoke_cases):
    caller=f.FormalCaller(fake_client(lambda **kw:response({},'other-model')), f.ROOT/'prompts/extraction_v1.md',tmp_path)
    with pytest.raises(f.HardStop,match='model identity'):
        caller.collect(projection(smoke_cases))
    assert (tmp_path/'dev_attempts/dev_001_1.outcome.json').exists()


def test_ambiguous_attempt_never_resampled(tmp_path, smoke_cases):
    p=tmp_path/'dev_attempts/dev_001_1.started.json'
    f.write_once(p,b'{}')
    caller=f.FormalCaller(fake_client(lambda **kw:pytest.fail('resampled')),f.ROOT/'prompts/extraction_v1.md',tmp_path)
    with pytest.raises(f.HardStop,match='ambiguous'):
        caller.collect(projection(smoke_cases))


def test_prediction_cannot_be_overwritten(tmp_path):
    p=tmp_path/'prediction.json'
    f.write_once(p,b'original')
    f.write_once(p,b'original')
    with pytest.raises(f.HardStop,match='overwrite'):
        f.write_once(p,b'better answer')
    assert p.read_bytes()==b'original'


def test_projection_removes_all_annotations():
    rows=[{"case_id":f'dev_{i:03d}',"input":{"order_facts":{"receipt_date":"2026-09-01","request_date":"2026-09-02","is_custom_made":False},"customer_message":"尺码不合适"},"gold":{"route":"eligible"},"review_metadata":{"english_annotation":"SECRET"}} for i in range(1,91)]
    p=f.project_inputs(list(reversed(rows)),"dev")
    assert len(p)==90 and all(set(r)=={'case_id','split','input'} for r in p)
    assert 'SECRET' not in repr(p) and 'gold' not in repr(p)


def test_threshold_inclusive_and_no_epsilon():
    rows=[candidate(.7),candidate(math.nextafter(.7,0),gold='ineligible')]
    table,selected=threshold_table(rows)
    assert selected['threshold']==.7 and selected['accepted_n']==1
    assert apply_threshold(rows[0],.7)['final_route']=='eligible'
    assert apply_threshold(rows[1],.7)['review_reason']=='low_confidence'


def test_threshold_maximum_coverage_and_no_sixty_percent_constraint():
    rows=[candidate(.9)] + [candidate(.8,gold='ineligible') for _ in range(4)]
    table, selected=threshold_table(rows)
    assert selected['accepted_n']==1 and selected['coverage']==.2
    assert len(table)==2


def test_threshold_order_deterministic_and_no_feasible():
    rows=[candidate(.9),candidate(.8)]
    assert threshold_table(rows)==threshold_table(list(reversed(rows)))
    assert threshold_table(rows)[1]['threshold']==.8
    assert threshold_table([candidate(.9,gold='ineligible')])[1] is None


def test_policy_required_manual_bypasses_threshold():
    row=candidate(None,route='manual_review',gold='manual_review',reason='policy_required')
    out=apply_threshold(row,0)
    assert out['final_route']=='manual_review' and out['review_reason']=='policy_required'
    assert threshold_table([row])==( [], None)


def test_gold_manual_auto_route_is_selective_error_and_execution_denominator():
    rows=[candidate(.9,gold='manual_review'),candidate(.9),candidate(.9,status='execution_failure',reason='execution_failure')]
    m=metrics(rows)
    assert m['coverage']['numerator']==2 and m['coverage']['denominator']==3
    assert m['selective_accuracy']['numerator']==1 and m['selective_accuracy']['denominator']==2
    assert m['gold_manual_auto_routed_n']==1 and m['abstentions']['execution_failure']['n']==1


def test_error_capture_uses_only_valid_auto_candidate_errors():
    wrong=apply_threshold(candidate(.5,gold='manual_review'),.8)
    right=apply_threshold(candidate(.5),.8)
    policy=candidate(None,'manual_review', 'eligible',reason='policy_required')
    invalid=candidate(.5,status='validation_failure',reason='validation_failure')
    m=metrics([wrong,right,policy,invalid])
    assert m['error_capture']['captured_n']==1 and m['error_capture']['error_candidate_n']==1
    assert metrics([candidate()])['error_capture']['display']=='N/A'


def test_wilson_known_values():
    assert wilson(90,100)==pytest.approx([.8256343384950865,.9447708629393249])
    assert wilson(0,0) is None
    assert wilson(0,10)[0]==pytest.approx(0)
    assert wilson(10,10)[1]==pytest.approx(1)


def test_support_diagnostic_only_auto_candidates():
    rows=[candidate(.49),candidate(.5,gold='manual_review'),candidate(.7),candidate(.9),candidate(None,'manual_review','manual_review',reason='policy_required')]
    d=support_diagnostic(rows)
    assert [b['n'] for b in d['bins']]==[1,1,1,1]
    assert d['bins'][1]['candidate_route_errors']==1
    assert support_diagnostic([candidate()])['auroc_correctness'] is None


@pytest.mark.parametrize('message,damage,use',[
    ('没脏没破，没有穿出门','absent','no'),
    ('没有污渍','unknown','unknown'),
    ('没有破损','unknown','unknown'),
    ('没有弄脏也没有弄破，没穿出门','absent','no'),
    ('没有污渍和破损，只试穿','absent','no'),
    ('穿过','unknown','unknown'),
    ('有污渍，穿了一整天','present','yes'),
    ('没脏没破，后来蹭脏了；只试穿，但又穿出门','conflicting','conflicting'),
])
def test_baseline_negation_and_no_scores(message,damage,use):
    e=extract(message,load_patterns())
    assert e['damage_or_stain']['value']==damage
    assert e['use_beyond_inspection']['value']==use
    assert 'support_score' not in repr(e)
    assert all(span in message for v in e.values() for span in v['evidence'])


def test_baseline_uncertainty_priority_and_policy(policy):
    e=extract('尺码不合适，发错了；吊牌不知道是否剪掉；不确定有没有污渍；吊牌还在',load_patterns())
    assert e['return_reason']['value']=='quality_or_fulfillment_issue'
    assert e['damage_or_stain']['value']=='unknown'
    row={'case_id':'fixture','split':'dev','input':{'customer_message':'颜色不喜欢，吊牌还在，没脏没破，只试穿','order_facts':{'receipt_date':'2026-09-01','request_date':'2026-09-02','is_custom_made':False}}}
    r=run_baseline(row,policy,load_patterns())
    assert r['final_route']=='eligible' and r['candidate_rule_id']=='EL01_7DAY'
    assert 'support_score' not in repr(r)
    bad=copy.deepcopy(r['validated_extraction'])
    bad['tag_status']['evidence']=['not verbatim']
    with pytest.raises(ValueError,match='verbatim'):
        validate_evidence(bad,row['input']['customer_message'])


def test_baseline_locked_source_change_stops(tmp_path):
    p=tmp_path/'patterns.json'
    p.write_text('{}')
    hashes={'patterns.json':f.file_hash(p)}
    f.verify_file_map(tmp_path,hashes)
    p.write_text('{"tuned":true}')
    with pytest.raises(f.HardStop,match='locked hash'):
        f.verify_file_map(tmp_path,hashes)


def test_configuration_immutable_after_first_call():
    start={'eval_config_sha256':'original-config','baseline_lock_sha256':'original-baseline'}
    f.verify_started_bindings(start,'original-config','original-baseline')
    with pytest.raises(f.HardStop,match='after first formal call'):
        f.verify_started_bindings(start,'revised-config','original-baseline')
    with pytest.raises(f.HardStop,match='after first formal call'):
        f.verify_started_bindings(start,'original-config','tuned-baseline')


@pytest.mark.parametrize('code,expected',[(429,True),(500,True),(503,True),(401,False),(400,False)])
def test_only_infrastructure_http_errors_retry(code,expected):
    class HttpError(Exception):
        status_code=code
    assert f.retryable(HttpError()) is expected


def test_test_runner_requires_matching_authorization(tmp_path):
    with pytest.raises(f.HardStop,match='authorization missing'):
        f.verify_test_authorization(tmp_path,{})
    f.write_once(tmp_path/'threshold_lock_v1.json',f.encode({'status':'provisional_locked_from_dev','value':.8,'eval_config_sha256':'x'}))
    f.write_once(tmp_path/'baseline_lock_v1.json',b'{}')
    f.write_once(tmp_path/'eval_config_v1.json',b'{}')
    f.write_once(tmp_path/'test_authorization.json',f.encode({'decision':'approved_for_locked_test','test_dataset_sha256':'wrong'}))
    with pytest.raises(f.HardStop,match='binding mismatch'):
        f.verify_test_authorization(tmp_path,{})


def test_scoring_cannot_change_threshold_lock(tmp_path):
    p=tmp_path/'threshold_lock_v1.json'
    f.write_once(p,f.encode({'value':.8}))
    before=p.read_bytes()
    rows=[apply_threshold(candidate(.7),f.read_json(p)['value'])]
    metrics(rows)
    assert p.read_bytes()==before


def test_no_test_outputs_gate(tmp_path):
    f.assert_no_test_outputs(tmp_path)
    (tmp_path/'test_predictions_raw.jsonl').write_text('')
    with pytest.raises(f.HardStop,match='test formal'):
        f.assert_no_test_outputs(tmp_path)
