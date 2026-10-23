"""Fixed API-level genuine hosted evaluation. Never invoke before WINDOWOPEN."""
import argparse
import datetime
import json
import time
from pathlib import Path
import httpx

OUT = Path(__file__).resolve().parent
ORIGIN = 'https://torob-plan-b-2026.liara.run'
BASE = {'query':'','category':None,'max_price_toman':None,'lat':35.69508821734553,'lon':51.41148102579503,'radius_km':1,'payment_provider':None,'visit_at':'2026-10-23T17:00:00+03:30','require_declared_open':True,'contactable_only':False,'origin_label':'محدوده جمهوری (نقطه پیش‌فرض)'}
CASES = [
 ('B1','برای کارهای روزمره و پیام‌رسان یک گوشی سامسونگ تا ۱۰۰ میلیون تومان می‌خواهم. کمک کن گزینه مناسب انتخاب کنم.'),
 ('B2','بین گوشی سامسونگ و شیائومی تا ۱۰۰ میلیون تومان برای استفاده روزمره مقایسه کن؛ برای هر برند یک نمونه از داده‌ها نشان بده.'),
 ('B3','برای خرید حضوری گوشی سامسونگ تا ۱۰۰ میلیون تومان نزدیک میدان ونک، امروز ساعت ۱۸ می‌خواهم.'),
 ('B4','این پاسخ شبیه‌سازی است: ۶۴ نداریم، ۱۲۸ موجوده.'),
]


def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--window-open',action='store_true',required=True)
    parser.parse_args()
    output=OUT/'results.json'
    if output.exists():
        raise SystemExit('Existing evaluation results must not be overwritten or inference replayed.')
    report={'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Actual public HTTPS normal owned API and genuine worker, no model/HTTP fixtures','criteria_file':'criteria.md','model_start_cap':8,'maximum_normal_stage_reservation':7,'actual_worker_starts':'root must supply independently measured before/after ledger','completed_trace_stages':0,'cases':[]}
    save(output,report)
    for case_id,message in CASES:
        value={'id':case_id,'message':message,'initial_constraints':BASE.copy(),'http':[],'polls':[],'source_products':{},'semantic_review':'pending','model_attempts':1}
        report['cases'].append(value)
        client=httpx.Client(base_url=ORIGIN,headers={'Origin':ORIGIN},timeout=20,follow_redirects=False)
        next_slot=[0.0]
        turn_deadline=[None]
        def request(method,path,body=None):
            delay=next_slot[0]-time.monotonic()
            if delay>0:time.sleep(delay)
            next_slot[0]=time.monotonic()+.4
            started=time.monotonic()
            timeout=20
            if method=='GET' and path.startswith('/api/turns/') and turn_deadline[0] is not None:
                timeout=min(20,max(.01,turn_deadline[0]-time.monotonic()))
            try:
                response=client.request(method,path,json=body,timeout=timeout) if body is not None else client.request(method,path,timeout=timeout)
            except httpx.TransportError as error:
                value['http'].append({'method':method,'path':path,'request_json':body,'elapsed_ms':round((time.monotonic()-started)*1000),'transport_error':repr(error)})
                save(output,report)
                raise
            try:payload=response.json()
            except ValueError:payload={'non_json_body':response.text[:2000]}
            value['http'].append({'method':method,'path':path,'request_json':body,'status':response.status_code,'elapsed_ms':round((time.monotonic()-started)*1000),'response':payload})
            save(output,report)
            response.raise_for_status()
            return payload
        try:
            request('POST','/api/sessions',{})
            capabilities=request('GET','/api/capabilities')
            value['capabilities']=capabilities
            if not capabilities.get('model_available'):
                raise RuntimeError('Genuine worker unavailable before case; no inference submitted.')
            body={'kind':'needs','message':message,'constraints':BASE.copy()}
            before=None
            if case_id=='B4':
                value['fixture_source']=request('GET','/api/products/product_adfdc73bc839d15cd7754318')
                demo={**BASE,'query':'A07','category':'گوشی موبایل','max_price_toman':'40000000','visit_at':'2026-10-22T20:15:00+03:30'}
                before=request('POST','/api/missions',{'product_id':'product_adfdc73bc839d15cd7754318','constraints':demo,'mode':'simulation'})
                value['mission_before']=before
                primary=before['plan']['primary']
                if not primary:raise RuntimeError('Source fixture has no primary; do not substitute a product.')
                followup=request('POST',f"/api/missions/{before['mission']['id']}/followups",{'offer_id':primary['offer']['offer_id']})
                body={'kind':'reply','message':message,'mission_id':before['mission']['id'],'base_revision':before['mission']['revision'],'followup_id':followup['id'],'constraints':demo}
            value['turn_request']=body
            started=time.monotonic();deadline=started+120;turn_deadline[0]=deadline
            state=request('POST','/api/turns',body) # Exactly once, even if response is uncertain.
            value['turn_id']=state['id']
            retries=0
            while state['state'] in ('running','advancing'):
                if time.monotonic()>=deadline:raise TimeoutError('Original120-second case deadline reached.')
                time.sleep(min(1.5,max(0,deadline-time.monotonic())))
                if time.monotonic()>=deadline:raise TimeoutError('Original120-second case deadline reached.')
                try:
                    state=request('GET',f"/api/turns/{value['turn_id']}")
                    value['polls'].append({'elapsed_ms':round((time.monotonic()-started)*1000),'turn':state})
                except (httpx.TransportError,httpx.HTTPStatusError) as error:
                    transient=isinstance(error,httpx.TransportError) or error.response.status_code in (502,503,504)
                    value.setdefault('read_errors',[]).append(repr(error))
                    if not transient or retries>=3:raise
                    retries+=1
                    continue
            value['elapsed_ms']=round((time.monotonic()-started)*1000)
            value['turn']=state
            value['read_retries']=retries
            value['completed_trace_stages']=sum(1 for entry in state.get('trace',[]) if entry.get('provenance'))
            report['completed_trace_stages']+=value['completed_trace_stages']
            if report['completed_trace_stages']>8:raise RuntimeError('Trace lower bound unexpectedly exceeds actual-start cap; stop.')
            result=state.get('result') or {}
            for product in result.get('products',[]):
                value['source_products'][product['product_id']]=request('GET',f"/api/products/{product['product_id']}")
            checks={}
            checks['turn_completed']=state['state']=='completed'
            if case_id in ('B1','B2'):
                checks['exact_budget']=result.get('proposed_constraints',{}).get('max_price_toman')=='100000000'
                products=result.get('products',[])
                checks['prices_within_ceiling']=all(p.get('min_recorded_price') is not None and int(p['min_recorded_price'])<=100000000 for p in products)
                if case_id=='B2':checks['both_named_brands']=all(any(brand in (p.get('brand') or '') for p in products) for brand in ('سامسونگ','شیائومی'))
                elif products:checks['named_brand_phones']=all('سامسونگ' in (p.get('brand') or '') and 'گوشی' in (p.get('category') or '') for p in products)
                else:checks['honest_clarification_present']=bool(result.get('clarification_fa'))
                fact_checks=[]
                for recommendation in result.get('recommendations',[]):
                    pid=recommendation['product_id'];source=value['source_products'].get(pid)
                    for fact in recommendation.get('facts',[]):
                        expected=None;key=fact['id'][len(pid)+1:] if fact['id'].startswith(pid+':') else None
                        if source and key in ('title','brand','category','model'):expected=str(source.get(key))
                        elif source and key=='price':expected=source.get('min_recorded_price')
                        elif source and key and key.startswith('spec:'):
                            try:expected=str(source['specs'][int(key.split(':')[1])]['value'])
                            except (IndexError,KeyError,ValueError):pass
                        expected_evidence=source.get('evidence_ids') if source and key=='price' else [pid]
                        fact_checks.append({'product_id':pid,'fact':fact,'expected':expected,'expected_evidence':expected_evidence,'matches':expected is not None and fact.get('value')==expected and fact.get('evidence_ids')==expected_evidence})
                value['fact_checks']=fact_checks
                checks['cited_facts_resolve']=all(f['matches'] for f in fact_checks)
                checks['recommendations_have_own_evidence']=all(r.get('facts') and r['product_id'] in value['source_products'] for r in result.get('recommendations',[]))
            if case_id=='B3':
                proposed=result.get('proposed_constraints',{})
                checks['origin_not_fabricated_or_relabelled']=all(proposed.get(k)==BASE[k] for k in ('lat','lon','origin_label'))
                checks['explicit_clarification_present']=bool(result.get('clarification_fa'))
                value['geography_semantics_to_review']=result.get('clarification_fa')
            if case_id=='B4':
                after=request('GET',f"/api/missions/{before['mission']['id']}")
                value['mission_after']=after
                obs=result.get('observation')
                checks['locked_mission_unchanged']=after['mission']==before['mission']
                checks['variant_not_declared_available']=obs is None or obs.get('kind') in ('variant_mismatch','unavailable','unclear')
                checks['preview_unconfirmed_simulation']=obs is None or obs.get('confirmed') is False and obs.get('confirmed_at') is None and obs.get('provenance')=='simulation'
                checks['no_observation_requires_honest_clarification']=obs is not None or bool(result.get('clarification_fa'))
            value['machine_checks']=checks
            value['machine_pass']=all(checks.values())
            value['status']='completed_for_semantic_review'
        except Exception as error:
            value['status']='failed_or_blocked'
            value['error']=repr(error)
            value['machine_pass']=False
            # No repeat/coaching/new model submission. Preserve every failure.
        finally:
            client.close();save(output,report)
        if report['completed_trace_stages']>8:break
    report['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(output,report)
    print(json.dumps({'results':str(output),'cases':[(c['id'],c['status'],c.get('machine_pass')) for c in report['cases']],'completed_trace_stages_lower_bound':report['completed_trace_stages']},ensure_ascii=False))


if __name__=='__main__':main()
