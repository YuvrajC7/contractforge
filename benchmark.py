import time
from core import fixture,repair,validate_contract
from reporting import save_report
if __name__=='__main__':
    fixed=abstained=unsafe=contracts=0;records=[];t=time.perf_counter()
    for i in range(40):
        kind='rename' if i<24 else ('type_change' if i<32 else 'removed')
        f=fixture(1000+i,kind);r=repair(f['source'],f['old'],f['new'])
        if kind=='rename':
            v=validate_contract(r['source'],f['cases']);ok=v['passed']==v['total']
            fixed+=ok;contracts+=v['passed']
        else:
            ok=r['status']=='abstained';abstained+=ok;unsafe+=not ok
        records.append({'fixture':1000+i,'kind':kind,'status':r['status'],'expected_behavior':ok})
    save_report({'fixtures':40,'supported_rename_fixtures':24,'repaired_and_validated':fixed,
      'passing_consumer_examples':contracts,'unsupported_fixtures':16,'correct_abstentions':abstained,
      'unsafe_acceptances':unsafe,'elapsed_ms':round((time.perf_counter()-t)*1000,3),
      'records':records,'scope_note':'Generated fixture family with held-out field identifiers, not independently sourced real repositories. Deterministic codemod, no LLM execution.'})
