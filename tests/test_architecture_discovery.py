import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from alien_lab.architecture_discovery import *

class ScriptClient:
    def __init__(self, model_map=None, caps=None, ceiling=False, missing=False, bad_format=False):
        self.model_map=model_map or {}; self.caps=caps or ["completion"]; self.ceiling=ceiling; self.missing=missing; self.bad_format=bad_format; self.calls=[]
    def model_metadata(self, model):
        if self.missing: raise RuntimeError("missing")
        return {"name":model,"capabilities":self.caps}
    def generate(self, **kw):
        self.calls.append(kw); prompt=kw["prompt"]
        if self.ceiling: return SimpleNamespace(status="OK",response="",hit_ceiling=True,prompt_tokens=1,eval_tokens=192,wall_ms=1,done_reason="length")
        if self.bad_format: response="not json"
        elif "INDEPENDENT AUDITOR" in prompt: response=json.dumps({"decision":"APPROVE"})
        else:
            tid=re.search(r"TASK_ID=([0-9a-f]+)",prompt); task=self.model_map.get(tid.group(1) if tid else "")
            if task:
                by={a.semantic_id:a for a in task.actions}; response=json.dumps({"plan":[by[s].locator for s in task.required_semantics]})
            else: response=json.dumps({"plan":["node-00","node-01"]})
        return SimpleNamespace(status="OK",response=response,hit_ceiling=False,prompt_tokens=5,eval_tokens=3,wall_ms=1,done_reason="stop")

class Tests(unittest.TestCase):
    def test_task_deterministic_and_oracle_not_public(self):
        a=build_task(1,"linear_dependency",8,"NOVEL","x"); b=build_task(1,"linear_dependency",8,"NOVEL","x")
        self.assertEqual(a,b); self.assertNotIn("oracle_final",a.public_dict()); self.assertNotIn(a.oracle_hash,json.dumps(a.public_dict()))
    def test_difficulty_grows_structure(self):
        a=build_task(1,"linear_dependency",2,"NOVEL","x"); b=build_task(1,"linear_dependency",20,"NOVEL","x")
        self.assertGreater(len(b.required_semantics),len(a.required_semantics)); self.assertGreater(len(b.actions),len(a.actions))
    def test_silent_fault_screen_success_but_authoritative_failure(self):
        t=build_task(2,"silent_effect_fault",4,"SILENT_EFFECT_FAULT","x"); by={a.semantic_id:a for a in t.actions}; p=[by[s].locator for s in t.required_semantics]
        o=execute_plan(t,p); self.assertTrue(o.screen_success); self.assertFalse(o.authoritative_success); self.assertEqual(o.score,0)
    def test_verified_only_memory_promotion(self):
        t=build_task(2,"linear_dependency",4,"NOVEL","x"); m=AlienMemory(); self.assertIsNone(m.promote(t,t.required_semantics,"e",False)); self.assertEqual(len(m.records),0)
        self.assertIsNotNone(m.promote(t,t.required_semantics,"e",True)); self.assertEqual(len(m.records),1)
    def test_skill_replay_zero_model_and_drift_label_fallback(self):
        base=build_task(3,"drift_resolution",4,"NOVEL","same"); drift=build_task(3,"drift_resolution",4,"DRIFT","same")
        s=SkillRegistry(); by={a.semantic_id:a for a in base.actions}; skill=s.compile_verified(base,base.required_semantics,tuple(by[x].locator for x in base.required_semantics),"e",True)
        plan,rungs,err=s.resolve(drift,skill); self.assertIsNotNone(plan); self.assertIn("LABEL",rungs); self.assertIsNone(err)
    def test_unresolved_drift_halts_not_guesses(self):
        base=build_task(4,"drift_resolution",24,"NOVEL","same"); drift=build_task(4,"drift_resolution",24,"DRIFT","same")
        s=SkillRegistry(); by={a.semantic_id:a for a in base.actions}; skill=s.compile_verified(base,base.required_semantics,tuple(by[x].locator for x in base.required_semantics),"e",True)
        # Destroy labels too, forcing unresolved at severity >1.
        bad=TaskSpec(drift.task_id,drift.family,drift.difficulty,drift.stage,drift.lineage,drift.seed,drift.initial,
                     tuple(SurfaceAction(a.semantic_id,a.locator,a.label+"x",a.slot,a.op,a.target,a.arg,a.forbidden) for a in drift.actions),drift.required_semantics,drift.public_flag,drift.silent_fault,drift.drift_severity,drift.oracle_final,drift.oracle_hash)
        plan,_,err=s.resolve(bad,skill); self.assertIsNone(plan); self.assertTrue(err.startswith("UNRESOLVED"))
    def test_non_scored_status_cannot_have_zero(self):
        ev=TrialEvidence("x",0,"s",CellStatus.MODEL_UNAVAILABLE.value,0,"p","m",{}, {},"o",{}, {},"a","a",0,0,0,0,[],None,[],None,None,[],None,None,None,False,[],"x")
        with self.assertRaises(ValueError): ev.validate()
    def test_valid_failure_zero_is_legal(self):
        ev=TrialEvidence("x",0,"s",CellStatus.VALID_FAILURE.value,0,"p","m",{}, {},"o",{}, {},"a","a",0,0,0,0,[],None,[],None,None,[],False,False,False,False,[],"x"); ev.validate()
    def test_ledger_contains_all_8_factorial_and_locations(self):
        profile={"seeds":[1],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]}
        L=build_ledger("m",profile); names={c.architecture.name for c in L if c.phase=="FACTORIAL"}; self.assertEqual(names,{a.name for a in FACTORIAL_ARMS})
        self.assertEqual(len([c for c in L if c.phase=="PLACEMENT_ALIEN"]),2*len(ALIEN_LOCATIONS)); self.assertEqual(len([c for c in L if c.phase=="PLACEMENT_OPENADAPT"]),2*len(OPENADAPT_LOCATIONS)); self.assertEqual(len([c for c in L if c.phase=="PLACEMENT_VELMA"]),2*len(VELMA_LOCATIONS))
    def test_state_isolation_keys_change_by_architecture(self):
        self.assertNotEqual(architecture_state_key(FACTORIAL_ARMS[1],"x","l",1),architecture_state_key(FACTORIAL_ARMS[4],"x","l",1))
    def test_model_gateway_negotiates_thinking_and_ceiling(self):
        c=ScriptClient(caps=["completion","thinking"],ceiling=True); g=ModelGateway(c,ModelSpec("m","m",100000,10),retry_count=1); r=g.generate("x",1)
        self.assertEqual(r.status,CellStatus.OUTPUT_CAP_REACHED.value); self.assertIs(c.calls[0]["think"],False)
    def test_plain_model_omits_thinking(self):
        c=ScriptClient(caps=["completion"]); g=ModelGateway(c,ModelSpec("m","m",100000,10),retry_count=1); g.generate("x",1); self.assertIsNone(c.calls[0]["think"])
    def test_missing_model_cell_is_null_scored(self):
        t=build_task(1,"linear_dependency",2,"NOVEL","x"); cell=LedgerCell("c",0,"F","m",FACTORIAL_ARMS[0],t.family,t.difficulty,t.stage,t.lineage,t.seed,"s")
        with tempfile.TemporaryDirectory() as td:
            r=ArchitectureRunner(ModelSpec("m","m"),lambda _:ScriptClient(missing=True),"",Path(td)); ev=r.run_cell(cell); self.assertEqual(ev.status,CellStatus.MODEL_UNAVAILABLE.value); self.assertIsNone(ev.score)
    def test_bad_format_is_unscorable_not_zero(self):
        t=build_task(1,"linear_dependency",2,"NOVEL","x"); cell=LedgerCell("c",0,"F","m",FACTORIAL_ARMS[0],t.family,t.difficulty,t.stage,t.lineage,t.seed,"s")
        with tempfile.TemporaryDirectory() as td:
            r=ArchitectureRunner(ModelSpec("m","m",100000),lambda _:ScriptClient(bad_format=True),"",Path(td),retry_count=1); ev=r.run_cell(cell); self.assertEqual(ev.status,CellStatus.FORMAT_UNSCORABLE.value); self.assertIsNone(ev.score)
    def test_corrupt_evidence_is_quarantined_and_recomputed(self):
        t=build_task(1,"linear_dependency",2,"NOVEL","x"); cell=LedgerCell("c",0,"F","m",FACTORIAL_ARMS[0],t.family,t.difficulty,t.stage,t.lineage,t.seed,"s")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); es=EvidenceStore(p); es.path("c").write_text("{")
            client=ScriptClient({t.task_id:t}); r=ArchitectureRunner(ModelSpec("m","m",100000),lambda _:client,"",p,retry_count=1); ev=r.run_cell(cell); self.assertIn(CellStatus(ev.status),VALID_SCORED); self.assertTrue(list((p/"quarantine").glob("*")))
    def test_one_cell_exception_does_not_stop_suite(self):
        profile={"seeds":[1],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]}; L=build_ledger("m",profile)[:3]
        task_map={build_task(c.seed,c.family,c.difficulty,c.stage,c.lineage).task_id:build_task(c.seed,c.family,c.difficulty,c.stage,c.lineage) for c in L}; client=ScriptClient(task_map)
        with tempfile.TemporaryDirectory() as td:
            r=ArchitectureRunner(ModelSpec("m","m",100000),lambda _:client,"",Path(td),retry_count=1,progress_every=999); s=r.run(L); self.assertEqual(s["terminal_cells"],3); self.assertFalse(s["missing_cells"])
    def test_synthetic_audit(self):
        with tempfile.TemporaryDirectory() as td:
            r=synthetic_audit(Path(td)); self.assertTrue(r["passed"],r)
    def test_select_model_rejects_zero_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.json"; p.write_text(json.dumps({"models":[{"completed":True,"paired_packet_count":0,"paired_retrieved_minus_none_mean":None,"model":{"model":"x","label":"x"}}]}))
            with self.assertRaises(RuntimeError): select_model_from_007(p)
    def test_select_model_prefers_gain_then_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.json"; p.write_text(json.dumps({"models":[
                {"experiment_valid":True,"paired_packet_count":2,"paired_retrieved_minus_none_mean":.1,"analysis":{"RETRIEVED":{"last_passing_level":10}},"model":{"model":"a","label":"a"}},
                {"experiment_valid":True,"paired_packet_count":2,"paired_retrieved_minus_none_mean":.2,"analysis":{"RETRIEVED":{"last_passing_level":8}},"model":{"model":"b","label":"b"}}]}))
            self.assertEqual(select_model_from_007(p).model,"b")

    def test_repeat_is_same_underlying_task_but_drift_changes_locators(self):
        n=build_task(7,"linear_dependency",8,"NOVEL","same")
        r=build_task(7,"linear_dependency",8,"REPEAT","same")
        d=build_task(7,"linear_dependency",8,"DRIFT","same")
        self.assertEqual(n.initial,r.initial); self.assertEqual(n.required_semantics,r.required_semantics)
        self.assertEqual([(a.semantic_id,a.label,a.arg) for a in n.actions],[(a.semantic_id,a.label,a.arg) for a in r.actions])
        self.assertEqual(n.required_semantics,d.required_semantics)
        self.assertNotEqual({a.locator for a in n.actions},{a.locator for a in d.actions})

    def test_factorial_has_matched_novel_repeat_for_every_arm(self):
        profile={"seeds":[1],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]}
        rows=[c for c in build_ledger("m",profile) if c.phase=="FACTORIAL"]
        self.assertEqual(len(rows),16)
        for arch in FACTORIAL_ARMS:
            stages={c.stage for c in rows if c.architecture.name==arch.name}
            self.assertEqual(stages,{"NOVEL","REPEAT"})

    def test_resume_uses_highest_predecessor_order_not_filename_order(self):
        t=build_task(1,"linear_dependency",2,"REPEAT","line")
        arch=FACTORIAL_ARMS[1]; sk=architecture_state_key(arch,t.family,t.lineage,t.seed)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); es=EvidenceStore(p)
            st1=ArchitectureState(); st1.memory.promote(t,t.required_semantics,"e1",True)
            st2=ArchitectureState.from_dict(st1.to_dict()); st2.memory.promote(t,t.required_semantics,"e2",True)
            def ev(cid,order,state):
                return TrialEvidence(cid,order,sk,CellStatus.VALID_SUCCESS.value,1,"F","m",asdict(arch),t.public_dict(),t.oracle_hash,{},state.to_dict(),stable_hash({}),state.fingerprint(),0,0,0,0,[],None,[],[],[],list(t.required_semantics),True,True,True,False,[],None)
            es.write(ev("zz",1,st1)); es.write(ev("aa",2,st2))
            cell=LedgerCell("next",3,"F","m",arch,t.family,t.difficulty,t.stage,t.lineage,t.seed,sk)
            runner=ArchitectureRunner(ModelSpec("m","m"),lambda _:ScriptClient(),"",p)
            restored=runner._state_for(cell)
            self.assertEqual(restored.fingerprint(),st2.fingerprint())

    def test_live_preflight_rejects_format_valid_wrong_plan(self):
        with tempfile.TemporaryDirectory() as td:
            report=live_preflight([ModelSpec("m","m",100000,192)],lambda _:ScriptClient(),"",Path(td))
            self.assertFalse(report["passed"])
            self.assertEqual(report["models"]["m"]["status"],"LIVE_CAPABILITY_PREFLIGHT_FAILED")

    def test_negative_controls_actually_reuse_unsafe_state(self):
        class WrongClient(ScriptClient):
            def generate(self, **kw):
                self.calls.append(kw); prompt=kw["prompt"]
                if "INDEPENDENT AUDITOR" in prompt:
                    response=json.dumps({"decision":"APPROVE"})
                else:
                    tid=re.search(r"TASK_ID=([0-9a-f]+)",prompt); task=self.model_map.get(tid.group(1) if tid else "")
                    by={a.semantic_id:a for a in task.actions}; response=json.dumps({"plan":[by[s].locator for s in reversed(task.required_semantics)]})
                return SimpleNamespace(status="OK",response=response,hit_ceiling=False,prompt_tokens=5,eval_tokens=3,wall_ms=1,done_reason="stop")
        for arch in (ArchitectureConfig("NEG_A",True,False,False,"PREVERIFY_LEARN_NEGATIVE_CONTROL"),
                     ArchitectureConfig("NEG_O",False,False,True,openadapt_location="PREVERIFY_COMPILE_NEGATIVE_CONTROL")):
            lineage="neg"; n=build_task(31,"linear_dependency",4,"NOVEL",lineage); r=build_task(31,"linear_dependency",4,"REPEAT",lineage)
            sk=architecture_state_key(arch,n.family,lineage,n.seed)
            cells=[LedgerCell("n"+arch.name,0,"P","m",arch,n.family,n.difficulty,n.stage,lineage,n.seed,sk),
                   LedgerCell("r"+arch.name,1,"P","m",arch,r.family,r.difficulty,r.stage,lineage,r.seed,sk)]
            mp={n.task_id:n,r.task_id:r}; client=WrongClient(mp)
            with tempfile.TemporaryDirectory() as td:
                runner=ArchitectureRunner(ModelSpec("m","m",100000),lambda _:client,"",Path(td),retry_count=1)
                first=runner.run_cell(cells[0]); second=runner.run_cell(cells[1])
                self.assertEqual(first.score,0)
                if arch.alien:
                    self.assertTrue(second.retrieved_memory_ids)
                else:
                    self.assertIsNotNone(second.skill_id); self.assertEqual(second.model_calls,0)

    def test_openadapt_product_gate_success_and_failure(self):
        class CP:
            def __init__(self,stdout,stderr="",returncode=0): self.stdout=stdout; self.stderr=stderr; self.returncode=returncode
        def good_run(cmd,**kw):
            if "--break-it" in cmd: return CP("transaction: RECONCILIATION_REQUIRED; 1/2 REFUTED")
            return CP("VERIFIED in 4.1s; 0 model calls")
        with tempfile.TemporaryDirectory() as td:
            r=openadapt_product_gate(Path(td),which=lambda _:"/x/openadapt-flow",run=good_run)
            self.assertTrue(r["passed"]); self.assertTrue(r["healthy_zero_model_calls"]); self.assertTrue(r["broken_false_success_caught"])
        with tempfile.TemporaryDirectory() as td:
            r=openadapt_product_gate(Path(td),which=lambda _:None,run=good_run)
            self.assertFalse(r["passed"]); self.assertEqual(r["status"],"OPENADAPT_PRODUCT_UNAVAILABLE")

    def test_execution_complete_is_not_experiment_valid_when_invalid_cells_exist(self):
        profile={"seeds":[1],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]}
        L=build_ledger("m",profile)[:2]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); client=ScriptClient(missing=True)
            r=ArchitectureRunner(ModelSpec("m","m"),lambda _:client,"",p,retry_count=1,progress_every=999)
            summary=r.run(L)
            self.assertTrue(summary["execution_complete"]); self.assertFalse(summary["experiment_complete_valid"]); self.assertEqual(summary["conclusion_status"],"INSUFFICIENT_VALID_EVIDENCE")

    def test_evidence_hash_mismatch_is_quarantined(self):
        t=build_task(1,"linear_dependency",2,"NOVEL","x"); arch=FACTORIAL_ARMS[0]
        ev=TrialEvidence("c",0,"s",CellStatus.VALID_SUCCESS.value,1,"F","m",asdict(arch),t.public_dict(),t.oracle_hash,{}, {},stable_hash({}),stable_hash({}),0,0,0,0,[],None,[],[],[],list(t.required_semantics),True,True,True,False,[],None)
        with tempfile.TemporaryDirectory() as td:
            es=EvidenceStore(Path(td)); es.write(ev); p=es.path("c"); doc=json.loads(p.read_text()); doc["evidence"]["score"]=0; p.write_text(json.dumps(doc))
            self.assertIsNone(es.read("c")); self.assertTrue(list((Path(td)/"quarantine").glob("*")))

    def test_changed_ledger_refuses_same_output_directory(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); model=ModelSpec("m","m",100000); client=ScriptClient()
            r=ArchitectureRunner(model,lambda _:client,"",p,retry_count=1,progress_every=999)
            a=build_ledger("m",{"seeds":[1],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]})[:1]
            # Use missing model to avoid depending on a correct plan; manifest is still sealed.
            r=ArchitectureRunner(model,lambda _:ScriptClient(missing=True),"",p,retry_count=1,progress_every=999); r.run(a)
            b=build_ledger("m",{"seeds":[2],"families":["linear_dependency"],"factorial_difficulties":[2],"frontier_topologies":0,"lifecycle":[]})[:1]
            with self.assertRaises(RuntimeError): ArchitectureRunner(model,lambda _:ScriptClient(missing=True),"",p,retry_count=1).run(b)

    def test_openadapt_factor_catches_false_backend_success(self):
        t=build_task(9,"silent_effect_fault",2,"NOVEL","x")
        cell=LedgerCell("oa",0,"FACTORIAL","m",FACTORIAL_ARMS[3],t.family,t.difficulty,t.stage,t.lineage,t.seed,architecture_state_key(FACTORIAL_ARMS[3],t.family,t.lineage,t.seed))
        with tempfile.TemporaryDirectory() as td:
            client=ScriptClient({t.task_id:t}); ev=ArchitectureRunner(ModelSpec("m","m",100000),lambda _:client,"",Path(td),retry_count=1).run_cell(cell)
            self.assertEqual(ev.status,CellStatus.SAFE_HALT.value); self.assertTrue(ev.screen_success); self.assertFalse(ev.authoritative_success); self.assertEqual(ev.score,0)

if __name__=="__main__": unittest.main()
