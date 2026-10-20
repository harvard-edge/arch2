"""Constructed unit fixtures exercise provenance; they are not physical evidence."""
from dataclasses import asdict, replace
import json
from pathlib import Path

import pytest

from nanochip.laboratory import design_changes as changes
from nanochip.laboratory import design_feedback_data as feedback
from nanochip.laboratory.contracts import Action, Artifact, ContractError, file_sha256
from nanochip.laboratory.design_experiment import PhysicalDesignMaterializer, _physical_inputs
from nanochip.laboratory.design_learning import design_input
from nanochip.laboratory.physical import flow


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def artifacts(root):
    return [asdict(Artifact.from_file(root, str(p.relative_to(root))))
            for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'receipt.json']


def functional(root, source, *, differential=False):
    root.mkdir(parents=True)
    (root / 'candidate.v').write_text(source)
    if differential:
        original = changes.REFERENCE_SOURCE.read_text()
        files = {'reference.v':original, 'miter.v':changes._equivalence_miter(original,source),
                 'stress.cpp':changes._STRESS_BENCH, 'checker.py':Path(changes.__file__).read_text(),
                 'obj/equivalence_probe':'constructed differential binary'}
        checks = dict(ok=True, jobs_completed=409, resets=15, valid_writes=100, stream_stall_cycles=10, cycles_checked=300)
        fields = {'reference_sha256':'reference.v','miter_sha256':'miter.v','bench_sha256':'stress.cpp',
                  'checker_sha256':'checker.py','binary_sha256':'obj/equivalence_probe'}
        prefix = 'EQUIVALENCE_JSON '
    else:
        files = {'dequant_tb.cpp':changes.dequant_probe.BENCH.read_text(), 'vectors.json':'[]',
                 'vectors.txt':'constructed vectors', 'obj/dequant_probe':'constructed oracle binary'}
        checks = dict(ok=True, mismatches=0, protocol_error='',rows_completed=15, lanes_checked=1740,stream_stall_cycles=7)
        fields = {'bench_sha256':'dequant_tb.cpp','vectors_sha256':'vectors.json',
                  'vector_text_sha256':'vectors.txt','binary_sha256':'obj/dequant_probe'}
        prefix = 'PROBE_JSON '
    for name,text in files.items():
        p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
    (root/'simulation.log').write_text(prefix+json.dumps(checks)+'\n')
    receipt = dict(mode='fresh',ok=True,status='passed', candidate_sha256=file_sha256(root/'candidate.v'),
                   tool_version='constructed Verilator fixture',checks=checks,
                   version_probe=dict(returncode=0,timed_out=False),build=dict(returncode=0,timed_out=False),
                   simulation=dict(returncode=0,timed_out=False),
                   probe_sha256=file_sha256(Path(changes.dequant_probe.__file__)),
                   **{key:file_sha256(root/name) for key,name in fields.items()})
    receipt['output_artifacts']=artifacts(root)
    write(root/'receipt.json',receipt)
    return receipt


def physical(root, source, area):
    root.mkdir(parents=True)
    (root/'msh_deq.v').write_text(source)
    (root/'config.json').write_text(flow.CONFIG.read_text())
    (root/'runner.py').write_text(Path(flow.__file__).read_text())
    (root/'coverage.tcl').write_text(Path(flow.__file__).with_name('coverage.tcl').read_text())
    (root/'image.json').write_text('constructed image metadata')
    gds=root/'runs/physical/final/gds/msh_deq.gds'; gds.parent.mkdir(parents=True); gds.write_text('constructed gds')
    stages = {
        '39-openroad-detailedrouting':{'route__drc_errors':0},
        '41-openroad-checkantennas-1':{'route__antenna_violation__count':2},
        '50-openroad-stapostpnr':{'design__instance__area':area,'timing__setup__ws':1.5,'timing__hold__ws':.1,
                                 'timing__setup_vio__count':0,'timing__hold_vio__count':0,'timing__unconstrained__count':0,
                                 'design__max_slew_violation__count':2,'design__max_cap_violation__count':0,
                                 'design__max_fanout_violation__count':1},
        '58-magic-drc':{'magic__drc_error__count':0},'59-klayout-drc':{'klayout__drc_error__count':0},
        '64-netgen-lvs':{'design__lvs_error__count':0}}
    for name,metrics in stages.items():write(root/'runs/physical'/name/'state_out.json',{'metrics':metrics})
    timing = root/'runs/physical/50-openroad-stapostpnr'
    corner_names = ['fixture_slow', 'fixture_fast']
    write(timing/'config.json', {'STA_CORNERS':corner_names})
    corners = []
    for name in corner_names:
        log, environment = name+'.log', name+'.tcl'
        (root/log).write_text('constructed coverage check return')
        (root/environment).write_text('constructed coverage environment')
        corners.append(dict(corner=name,status='pass',log=log,
            log_sha256=file_sha256(root/log),environment=environment,
            environment_sha256=file_sha256(root/environment)))
    write(root/'coverage-receipt.json',dict(status='pass',image=flow.IMAGE,
        expected_corners=corner_names,corners=corners,
        postroute_state_sha256=file_sha256(timing/'state_out.json'),
        script_sha256=file_sha256(root/'coverage.tcl'),
        input_artifacts=[asdict(Artifact.from_file(root,'config.json'))]))
    checks,_=flow.collect_checks(root)
    receipt=dict(status='completed',returncode=0,ok=False,candidate_sha256=file_sha256(root/'msh_deq.v'),
                 config_sha256=file_sha256(root/'config.json'),runner_sha256=file_sha256(root/'runner.py'),
                 image=flow.IMAGE,pdk='sky130A',pdk_revision=flow.PDK_REVISION,cores=1,host_architecture='fixture',checks=checks,
                 commands=[['docker','run','--cpus','1',flow.IMAGE,flow.PDK_REVISION]])
    receipt['artifacts']=artifacts(root);write(root/'receipt.json',receipt)


@pytest.fixture
def bundles(tmp_path,monkeypatch):
    base=tmp_path/'baseline';base.mkdir()
    original=changes.REFERENCE_SOURCE.read_text();(base/'source.v').write_text(original)
    functional(base/'functional',original);physical(base/'physical',original,100)
    candidate=tmp_path/'candidate';candidate.mkdir()
    task=changes.design_change_task()
    task=replace(task,max_proposals=1,max_attempts=1,specification=dict(task.specification,
        physical_inputs={name:file_sha256(path) for name,path in _physical_inputs().items()},
        budgets=dict(cores=1),image=flow.IMAGE,pdk_revision=flow.PDK_REVISION))
    attempt=candidate/'attempts/attempt-0001'
    item=PhysicalDesignMaterializer().materialize(task,Action('stream_quantized_row'),attempt)
    changed=(Path(item.root)/'msh_deq.v').read_text()
    functional(attempt/'tool',changed);functional(attempt/'differential',changed,differential=True)
    physical(attempt/'physical-fixture',changed,110)
    write(candidate/'task.json',asdict(task))
    proposal=dict(input_text=design_input(task),action=asdict(item.action));write(candidate/'proposal.json',proposal)
    observation=dict(candidate_digest=item.digest,action=asdict(item.action),status='success')
    campaign=dict(task_id=task.task_id,observations=[observation])
    write(candidate/'design-experiment.json',dict(campaign=campaign,complete_design_eligible=False))
    events=[dict(event='campaign_started',task=asdict(task)),dict(event='proposal',action=asdict(item.action)),
            dict(event='candidate',candidate=asdict(item),candidate_digest=item.digest),
            dict(event='observation',observation=observation),dict(event='campaign_finished',campaign=campaign)]
    (candidate/'events.jsonl').write_text('\n'.join(json.dumps(v) for v in events)+'\n')
    write(attempt/'execution-link.json',dict(task_digest=task.digest,candidate_digest=item.digest,
        action=asdict(item.action),physical_run=True,**{key:file_sha256(Path(item.root)/'msh_deq.v')
        for key in ('source_sha256','functional_source_sha256','physical_source_sha256')}))
    for name,root in [('functional-receipt.json',attempt/'tool'),('physical-receipt.json',attempt/'physical-fixture')]:
        write(attempt/name,dict(task_id=task.task_id,candidate_digest=item.digest,mode='fresh',execution_status='success',
            output_root=str(root),output_artifacts=[asdict(Artifact.from_file(root,'receipt.json'))]))
    def run_check(source,output):return functional(output,Path(source).read_text(),differential=True)
    monkeypatch.setattr(changes,'run_design_checks',run_check)
    return base,candidate,tmp_path/'feedback'


def test_collect_roundtrip_derives_losing_candidate_without_optimal_claim(bundles):
    base,candidate,output=bundles
    before={str(p):file_sha256(p) for root in (base,candidate) for p in root.rglob('*') if p.is_file()}
    result=feedback.collect_feedback(base,candidate,output)
    assert result['selected_action']=='retain_indexed_read'
    assert result['records'][0]['label_origin']==feedback.LABEL_ORIGIN
    assert result['records'][0]['original_split']=='development'
    assert result['accepted'] is False
    assert feedback.load_feedback(output/'manifest.json')==result
    assert all(file_sha256(path)==digest for path,digest in before.items())
    assert result['records'][0]['input_text']==design_input(result['target_features'])
    with pytest.raises(ContractError,match='new path'):feedback.collect_feedback(base,candidate,output)


@pytest.mark.parametrize('mutation', ['missing','tampered','hashwrong','label','serialization','snapshot'])
def test_loader_rejects_tampered_frozen_evidence(bundles,mutation):
    base,candidate,output=bundles;result=feedback.collect_feedback(base,candidate,output)
    manifest=output/'manifest.json'
    if mutation in ('missing','tampered'):
        p=output/result['copied_evidence'][0]['path']
        if mutation=='missing':p.unlink()
        else:p.write_text('tampered')
    elif mutation=='hashwrong':result['copied_evidence'][0]['sha256']='0'*64;write(manifest,result)
    elif mutation=='label':result['records'][0]['target_action']='stream_quantized_row';write(manifest,result)
    elif mutation=='serialization':result['records'][0]['input_text']='n=999';write(manifest,result)
    else:(output/'evidence.json').write_text('{}')
    with pytest.raises(ContractError):feedback.load_feedback(manifest)


@pytest.mark.parametrize('mutation', ['config','functional','source','receipt','task','nonfinite'])
def test_rejects_unmatched_or_invalid_source_evidence(bundles,mutation):
    base,candidate,output=bundles
    if mutation=='config':
        p=base/'physical/receipt.json';d=json.loads(p.read_text());d['cores']=2;write(p,d)
    elif mutation=='functional':
        p=base/'functional/receipt.json';d=json.loads(p.read_text());d['ok']=False;write(p,d)
    elif mutation=='source':(base/'source.v').write_text('changed source')
    elif mutation=='receipt':(base/'physical/receipt.json').unlink()
    elif mutation=='task':
        p=candidate/'task.json';d=json.loads(p.read_text());d['task_id']='changed';write(p,d)
    else:
        p=base/'physical/runs/physical/50-openroad-stapostpnr/state_out.json'
        d=json.loads(p.read_text());d['metrics']['design__instance__area']=float('nan');write(p,d)
    with pytest.raises(ContractError):feedback.collect_feedback(base,candidate,output)


def row(action,area):
    return dict(action=action,postroute_instance_area=area,postroute_setup_worst_slack=1,
                postroute_hold_worst_slack=.1,functional_passed=True,physical_completed=True,
                required_physical_passed=True,configuration={'matched':True},failed_check_families=['electrical','antenna'])


def test_preference_is_measured_and_independent_of_action_order():
    assert feedback.derive_preference([row('a',100),row('b',90)])=='b'
    assert feedback.derive_preference([row('b',90),row('a',100)])=='b'


@pytest.mark.parametrize('change', [dict(postroute_instance_area=100),dict(postroute_instance_area=float('inf')),
    dict(postroute_instance_area=-1),dict(failed_check_families=['different']),dict(failed_check_families=[]),
    dict(functional_passed=False),dict(physical_completed=False),dict(required_physical_passed=False),
    dict(postroute_hold_worst_slack=float('nan')),dict(configuration={'matched':False})])
def test_preference_abstains_for_unmatched_failed_or_nonfinite_designs(change):
    with pytest.raises(ContractError):feedback.derive_preference([row('a',100),row('b',110)|change])
