import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from alien_lab.final_memory_frontier import *

class ScriptClient:
    def __init__(self, base_url, script=None): self.script=list(script or [])
    def generate(self, **kw):
        if self.script:
            x=self.script.pop(0)
            if isinstance(x,Exception): raise x
            return x
        n=len(re.findall(r"(?m)^TASK \d+$",kw['prompt']))
        response=" ".join(f"{i}:A" for i in range(1,n+1)) if n else "A"
        return SimpleNamespace(status="OK",response=response,hit_ceiling=False,prompt_tokens=10,eval_tokens=5,wall_ms=1,done_reason="stop")

def R(response,status="OK",ceiling=False): return SimpleNamespace(status=status,response=response,hit_ceiling=ceiling,prompt_tokens=10,eval_tokens=5,wall_ms=1,done_reason="stop")

class Tests(unittest.TestCase):
    def test_audit(self):
        r=deterministic_audit(); self.assertTrue(r['passed'],r); self.assertGreater(r['perfect_learning_macro_count'],250)
    def test_same_facts_all_arms_and_retrieved_subset(self):
        st=generate_bootstrap(1); tasks,sealed=build_level(1,1,0,st)
        promote_verified(st,tasks,[{"task_id":t.task_id,"verified_success":True} for t in tasks],1)
        texts={a:render_packet(tasks,st,a) for a in ARMS}
        for rid in st.rules:
            self.assertIn(rid,texts[ARM_NONE][0]); self.assertIn(rid,texts[ARM_FULL][0]); self.assertIn(rid,texts[ARM_RETRIEVED][0])
        self.assertEqual(texts[ARM_NONE][1],())
        self.assertLessEqual(len(texts[ARM_RETRIEVED][1]),len(texts[ARM_FULL][1]))
    def test_failure_then_pass_is_recorded_not_terminal(self):
        rows=[]
        for l,a in [(1,.5),(2,1),(3,.4),(4,1),(5,.3),(6,.2),(7,.1),(8,.2),(9,.2)]:
            rows.append({'level':l,'variants':[{'arms':{ARM_RETRIEVED:{'status':'OK','accuracy':a}}}]})
        c=characterize(rows,ARM_RETRIEVED)
        self.assertIn(2,c['recovery_levels_after_failure']); self.assertIn(4,c['recovery_levels_after_failure'])
        self.assertEqual(c['sustained_collapse_start'],5)
    def test_retries_do_not_abort_arm(self):
        cfg=SuiteConfig('x',(ModelSpec('m','m'),),max_level=1,retry_count=3)
        client=ScriptClient('',[RuntimeError('x'),R('1:A 2:A 3:A 4:A 5:A 6:A')])
        with tempfile.TemporaryDirectory() as td:
            run=Final007Runner(cfg,lambda _:client,Path(td)); st=generate_bootstrap(cfg.seed); t,s=build_level(cfg.seed,1,0,st)
            row=run._run_arm(client,cfg.models[0],Path(td),1,0,t,s,st,ARM_NONE)
            self.assertEqual(row['status'],'OK'); self.assertEqual(len(row['retry_failures']),1)
    def test_context_cap_is_data_not_exception(self):
        spec=ModelSpec('m','m',context_limit=10)
        cfg=SuiteConfig('x',(spec,),max_level=1)
        with tempfile.TemporaryDirectory() as td:
            run=Final007Runner(cfg,ScriptClient,Path(td)); st=generate_bootstrap(1); t,s=build_level(1,1,0,st)
            row=run._run_arm(ScriptClient(''),spec,Path(td),1,0,t,s,st,ARM_FULL)
            self.assertEqual(row['status'],'CONTEXT_CAP_REACHED')
    def test_suite_continues_after_model_catastrophe(self):
        class BadFactory:
            def __init__(self): self.n=0
            def __call__(self,url):
                self.n+=1
                if self.n==1: raise RuntimeError('model unavailable')
                return ScriptClient(url)
        cfg=SuiteConfig('x',(ModelSpec('a','a'),ModelSpec('b','b')),max_level=1)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td); res=Final007Runner(cfg,BadFactory(),out).run_suite()
            self.assertEqual(len(res['models']),2); self.assertFalse(res['models'][0]['completed']); self.assertTrue(res['models'][1]['completed'])
            self.assertTrue((out/'suite_summary.json').exists())
    def test_titan_three_budgets_always_present(self):
        cfg=SuiteConfig('x',(ModelSpec('m','m',context_limit=100000),),max_level=1)
        with tempfile.TemporaryDirectory() as td:
            run=Final007Runner(cfg,ScriptClient,Path(td)); st=generate_bootstrap(cfg.seed)
            t,_=build_level(cfg.seed,1,0,st); promote_verified(st,t,[{"task_id":x.task_id,"verified_success":True} for x in t],1)
            res=run._run_titan(ScriptClient(''),cfg.models[0],Path(td),st)
            self.assertEqual(set(res['attempts']),set(TITAN_ARMS))
            self.assertGreaterEqual(res['raw_rule_applications'],40)
            self.assertGreaterEqual(res['macro_slots'],1)
            none=res['attempts'][TITAN_NONE]; limited=res['attempts'][TITAN_LIMITED]; maximum=res['attempts'][TITAN_MAX]
            self.assertEqual(none['memory_count'],0)
            self.assertGreater(limited['memory_count'],0)
            self.assertGreater(maximum['memory_count'],limited['memory_count'])
            self.assertLessEqual(limited['rendered_program_steps'], none['rendered_program_steps'])
            self.assertLessEqual(maximum['rendered_program_steps'], limited['rendered_program_steps'])
    def test_checkpoint_atomic_and_written_each_variant(self):
        cfg=SuiteConfig('x',(ModelSpec('m','m'),),max_level=1)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td); s=Final007Runner(cfg,ScriptClient,out).run_suite(); md=out/'m'
            self.assertTrue((md/'checkpoint.json').exists()); cp=json.loads((md/'checkpoint.json').read_text()); self.assertTrue(cp['completed'])
            self.assertTrue(s['models'][0]['completed'])
    def test_resume_skips_completed_variant_and_finishes(self):
        cfg=SuiteConfig('x',(ModelSpec('m','m'),),max_level=2)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td); runner=Final007Runner(cfg,ScriptClient,out); md=out/'m'; md.mkdir(parents=True)
            st=generate_bootstrap(cfg.seed); tasks,sealed=build_level(cfg.seed,1,0,st)
            fake_results=[{"task_id":t.task_id,"verified_success":True} for t in tasks]
            promote_verified(st,tasks,fake_results,1)
            row={"level":1,"variants":[{"variant":0,"arms":{a:{"status":"OK","accuracy":1.0} for a in ARMS},"promoted":1}]}
            runner._checkpoint(md,{"phase":"ladder","completed_level":1,"completed_variant":0,"memory_count":len(st.macros),
                "memory_fingerprint":st.fingerprint(),"store":st.to_dict(),"rows":[row],"infra_failures":0})
            summary=runner.run_model(cfg.models[0])
            self.assertTrue(summary['completed']); self.assertEqual(summary['levels_completed'],2)
            cp=json.loads((md/'checkpoint.json').read_text()); self.assertEqual(cp['phase'],'complete')

if __name__=='__main__': unittest.main()
