#!/usr/bin/env python3
"""Build the submission report from a completed, recorded experiment run."""
import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import statistics
import zipfile
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String, Line

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'report'
CONFIGS = ['ONE/ONE','QUORUM/ONE','ONE/QUORUM','QUORUM/QUORUM','ALL/ALL']
MODELS = ['RYW','MR','MW','WFR']
SCENARIOS = ['normal','node_failure','partition']
REFERENCES = [
 ('Terry, D. B., Demers, A. J., Petersen, K., Spreitzer, M. J., Theimer, M. M., and Welch, B. B. (1994). Session Guarantees for Weakly Consistent Replicated Data. PDIS, pp. 140-149.', 'https://www.cs.cornell.edu/courses/cs734/2000FA/cached%20papers/SessionGuaranteesPDIS_1.html'),
 ('Apache Cassandra. Dynamo: replication, versioning and tunable consistency.', 'https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo.html'),
 ('Apache Cassandra. Read repair.', 'https://cassandra.apache.org/doc/stable/cassandra/managing/operating/read_repair.html'),
 ('Apache Cassandra. Hints.', 'https://cassandra.apache.org/doc/stable/cassandra/managing/operating/hints.html'),
 ('Apache Cassandra. CQL Data Manipulation: UPDATE and TIMESTAMP.', 'https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html'),
 ('Apache Cassandra Python driver. Policies implementation.', 'https://github.com/apache/cassandra-python-driver/blob/trunk/cassandra/policies.py'),
 ('Docker Official Image packaging. Cassandra.', 'https://github.com/docker-library/cassandra'),
 ('OpenAI. Codex. AI assistance used for this project; disclosure on page 8.', 'https://openai.com/codex/'),
]

def load(path):
    return json.loads(path.read_text())

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results',type=Path)
    args = p.parse_args()
    candidates = sorted((ROOT/'results').glob('*/completion.json'))
    run = args.results or (candidates[-1].parent if candidates else None)
    if run is None or not (run/'completion.json').exists():
        raise SystemExit('No completed experiment run. Run scripts/lab.py run first; results will not be invented.')
    trials = load(run/'trials.json')
    env = load(run/'environment.json')
    runtime = load(run/'runtime_checks.json') if (run/'runtime_checks.json').exists() else {}
    java = runtime.get('n1',{}).get('java','JVM version not recorded').splitlines()[0]
    controls = load(run/'read_repair.json')
    skew = load(run/'timestamp_control.json')
    from verify_results import verify
    verify(run)
    authors = load(OUT/'authors.json')
    expected = 3*5*4*env['repeats']
    if len(trials) != expected:
        raise SystemExit(f'Expected {expected} trials, found {len(trials)}.')
    totals = Counter(t['verdict'] for t in trials)
    ops = [o for t in trials for o in t['operations']]
    errors = Counter(o['error'] for o in ops if o['status']!='ok')
    groups = defaultdict(list)
    for t in trials:
        groups[t['scenario'],t['config'],t['model']].append(t)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyLab',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=9,textColor=colors.HexColor('#243247')))
    styles.add(ParagraphStyle(name='SmallLab',parent=styles['BodyLab'],fontSize=8,leading=10,spaceAfter=5))
    styles.add(ParagraphStyle(name='TitleLab',fontName='Helvetica-Bold',fontSize=28,leading=33,textColor=colors.HexColor('#142e4c'),spaceAfter=18))
    styles['Heading1'].textColor=colors.HexColor('#142e4c')
    story, md = [], []
    def para(text, small=False):
        story.append(Paragraph(html.escape(text),styles['SmallLab' if small else 'BodyLab']))
        md.append(text+'\n')
    def heading(text):
        story.append(Paragraph(html.escape(text),styles['Heading1']))
        md.append('## '+text+'\n')
    def page():
        story.append(PageBreak())
    def table(headers, rows, widths):
        data = [[Paragraph(html.escape(str(c)),styles['SmallLab']) for c in row] for row in [headers]+rows]
        t = Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce9f2')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f9')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),
            ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('LINEBELOW',(0,0),(-1,0),0.7,colors.HexColor('#90a7bb'))]))
        story.append(t); story.append(Spacer(1,10))
        md.extend(['| '+' | '.join(map(str,headers))+' |','| '+' | '.join(['---']*len(headers))+' |'])
        md.extend('| '+' | '.join(map(str,row))+' |' for row in rows)
        md.append('')

    story.append(Spacer(1,25))
    story.append(Paragraph('Client-centric consistency<br/>in Apache Cassandra',styles['TitleLab']))
    md.append('# Client-centric consistency in Apache Cassandra\n')
    para('Replicated database experiments under normal operation, node failure and network partition')
    para(authors['course'])
    for member in authors['members']:
        para(member)
    para('Submission deadline: 27 September 2026 | Group size: at most three')
    para(f"Measured run: {run.name} | {env['repeats']} repetitions per matrix cell")
    heading('Abstract')
    para(f"We deployed three Cassandra 5.0.9 nodes and tested five write/read consistency combinations against four client-centric properties. The main matrix contains {len(trials)} trials: {totals['violation']} violation witnesses, {totals['no_violation_observed']} completed trials without a witness, and {totals['inconclusive']} inconclusive trials. Inconclusive outcomes include unavailable or timed-out operations; they are not counted as consistency failures.")
    para('The experiment isolates the effects of replica divergence, quorum requirements and read repair. Separate controls change the read-repair setting and deliberately reverse mutation timestamps. Results apply to the specified sequential workloads and fault schedules; they do not prove a general causal-consistency guarantee for Cassandra.')
    para('All result tables are generated from saved database responses. Predictions are preserved separately in report/predictions.md. The reproduction archive contains code, environment metadata, initialization records and operation histories.',small=True)
    page()

    heading('1. Database and deployment')
    para('Cassandra is a replicated, partitioned database in which any node can coordinate a request. Our keyspace uses NetworkTopologyStrategy with dc1:3. With exactly three nodes, every test key has a replica on every node. ONE, QUORUM and ALL require respectively one, two and three replica responses in this deployment. [2]')
    diagram = Drawing(490,140)
    for x,label in [(15,'n1'),(185,'n2'),(355,'n3')]:
        diagram.add(Rect(x,15,115,48,fillColor=colors.HexColor('#e5eef5'),strokeColor=colors.HexColor('#7895b0')))
        diagram.add(String(x+44,42,label,fontName='Helvetica-Bold',fontSize=12))
        diagram.add(String(x+15,25,'RF=3 / dc1',fontSize=9))
        diagram.add(Line(245,105,x+57,64,strokeColor=colors.HexColor('#7895b0')))
    diagram.add(Rect(180,105,130,28,fillColor=colors.HexColor('#142e4c')))
    diagram.add(String(198,115,'Python client',fillColor=colors.white,fontSize=11))
    story.append(diagram)
    para('Figure 1. One Docker bridge network. The client reaches all CQL endpoints on port 9042. A partition blocks storage traffic on ports 7000/7001 between selected nodes, while CQL remains reachable. No host ports are published.',small=True)
    table(['Component','Measured / configured value'],[
        ['Database','Apache Cassandra 5.0.9; three containers; 16 tokens per node'],
        ['Client / JVM','Python 3.11.13; cassandra-driver 3.29.2; protocol v4; '+java],
        ['Docker',env['docker']['ServerVersion']+'; '+env['compose']+'; '+env['docker']['Architecture']+'; '+str(env['docker']['NCPU'])+' virtual CPUs'],
        ['Memory',f"Docker VM: {env['docker']['MemTotal']/1024**3:.2f} GiB; Cassandra heap: 768 MiB/node"],
        ['Replication','NetworkTopologyStrategy; dc1=3; rack1; persistent named volumes'],
        ['Repair controls','Hints disabled; no scheduled anti-entropy repair; BLOCKING unless specified'],
        ['Query controls','Explicit CL and timestamps; no driver retries or speculative execution; table speculative_retry=NONE'],
    ],[105,385])
    para('Installation uses the Docker Official Image packaging [7], with pinned base-image digests. A derived image installs iptables and disables hinted handoff. Run python3 scripts/lab.py up to build and start nodes sequentially; readiness checks require three UN nodes and working CQL/schema operations. Exact runtime/image details are saved in environment.json and initial_cluster.json.')
    page()

    heading('2. Models and predictions')
    para('The four session guarantees describe the view and ordering experienced by one logical client, even when it changes servers. RYW requires later reads to include that client’s earlier writes; MR disallows losing previously observed writes. MW orders one client’s writes. WFR preserves dependencies from an observed write to a later write by the reader. [1]')
    para('Our checks use a monotone cell a for reads, and distinct cells a (predecessor) and b (successor) for dependencies. We use one logical writer per key, sequential operations, no deletions or TTLs, and increasing timestamps except in the explicit timestamp control. These assumptions make returned values interpretable as evidence about the intended history.')
    table(['Write/read','RYW','MR (BLOCKING)','MW / WFR'],[
        ['ONE/ONE','May fail','May fail','May expose missing dependency'],
        ['QUORUM/ONE','May fail','May fail','No general replica-order guarantee'],
        ['ONE/QUORUM','May fail','Expected for successful quorum reads','No general replica-order guarantee'],
        ['QUORUM/QUORUM','Expected under assumptions','Expected for successful quorum reads','No general replica-order guarantee'],
        ['ALL/ALL','Expected under assumptions','Expected for successful reads','No completed witness expected in this workload'],
    ],[102,105,133,150])
    para('These are predictions, not observations. For RF=3, W+R>3 ensures acknowledgement-set intersection; ONE/QUORUM has 1+2=3 and lacks that argument. The overlap argument supports our RYW prediction for QUORUM/QUORUM, but does not order every mutation at every replica. [2; deduction for this workload]')
    para('BLOCKING read repair is documented to provide monotonic quorum reads; NONE reconciles a read without repairing divergent replicas. [3] The focused control therefore predicts a possible 1-to-0 regression only with NONE. The main partition schedule may prevent a quorum read from completing at all, which is an availability result rather than evidence of a regression.')
    para('For normal operation we expect mostly successful histories. With n3 killed, ONE and QUORUM should remain usable through n1/n2, whereas ALL should fail. With {n1,n2} isolated from {n3}, weak isolated reads can be stale; isolated quorum operations should fail. report/predictions.md contains the complete pre-execution reasoning.')
    page()

    heading('3. Experimental design')
    para(f"Each of five configurations is tested under three scenarios for four models, with {env['repeats']} fresh-key repetitions: 5 x 3 x 4 x {env['repeats']} = {len(trials)} main trials. Each row is initialized to (a=0,b=0) at ALL before the fault is injected. Initialization errors abort the run. Writes use explicit increasing microsecond timestamps to separate replication effects from clock effects. CQL supports the TIMESTAMP parameter. [5]")
    table(['Model','Ordered operations','Violation witness'],[
        ['RYW','W(a=1) at n1; R(a,b) at target','Final a=0 after acknowledged W'],
        ['MR','W(a=1) at n1; R at n1; R at target','Second read a < first read a'],
        ['MW','W(a=1) at n1; W(b=1) at target; R at target','Final (a=0,b=1)'],
        ['WFR','Producer W(a=1) at n1; client R(a=1) at n1; client W(b=1) at target; observer R at target','Final (a=0,b=1), with dependency read confirmed'],
    ],[45,295,150])
    para('Target is n3 for normal operation and partition, and n2 for node failure. W and R use the selected configuration. The WFR producer is logically distinct from the reader/writer even though operations use the same harness. The MW/WFR observer selects both cells together; separate reads could themselves introduce a misleading observation order. A visible successor with its predecessor absent is a counterexample to dependency visibility, but absence of a witness cannot establish every replica’s application order.')
    para('Node failure sends SIGKILL to n3, then allows 15 seconds for failure detection. Network partition installs symmetric packet-drop rules for n3 versus n1/n2 and also waits 15 seconds. Rules match both source and destination storage ports to block established streams in both directions. New restrictions are installed before obsolete ones are removed during topology changes.')
    para('The driver pins each connection to its named coordinator and propagates errors instead of retrying or downgrading CL. [6] Coordinator pinning does not generally force a local replica read. During isolation, however, a successful ONE read on n3 cannot obtain data from n1/n2. The two-node read-repair control forces both available replicas to participate in a quorum.')
    para('Every trial retains the requested CL, query, parameters, nanosecond start/end times, latency, coordinator, value or error. Any operation error makes the trial inconclusive; WFR also requires its dependency read to observe a=1. A successor not observed is likewise inconclusive. Fault rules and packet counters are preserved separately.')
    page()

    heading('4. Main results: consistency witnesses')
    para('Each cell is V / N / I: violation witnesses / no violation observed / inconclusive trials. N describes a finite observation, not a proven guarantee. The table is computed from trials.json.')
    rows=[]
    for scenario in SCENARIOS:
        for config in CONFIGS:
            values=[]
            for model in MODELS:
                count=Counter(t['verdict'] for t in groups[scenario,config,model])
                values.append(f"{count['violation']} / {count['no_violation_observed']} / {count['inconclusive']}")
            rows.append([scenario.replace('_',' '),config]+values)
    table(['Scenario','Write/read']+MODELS,rows,[83,107,75,75,75,75])
    para(f"Across the matrix: {totals['violation']} V, {totals['no_violation_observed']} N and {totals['inconclusive']} I. Counts are not estimates of production anomaly probability: fresh keys repeat a deliberately selected schedule on one shared cluster, in a fixed configuration order.")
    witnesses=[t for t in trials if t['verdict']=='violation']
    if witnesses:
        sample=witnesses[0]
        para(f"Example witness: {sample['scenario']}, {sample['config']}, {sample['model']}, repetition {sample['repetition']}. Key: {sample['key']}",small=True)
        for op in sample['operations']:
            result = 'write acknowledged' if op['query'].startswith('UPDATE') and op['status']=='ok' else str(op.get('value'))
            para(f"{op['node']} {op['cl']}: {op['query'].split(' ')[0]} -> {result} ({op['status']})",small=True)
    page()

    heading('5. Availability and latency')
    para('An operation can fail to obtain enough replicas without returning stale data. The table separates successful requests from errors. Latency is measured at the Python application and includes initial connection setup where applicable; these figures are diagnostic, not a throughput benchmark. p95 uses the nearest-rank definition.')
    rows=[]
    for scenario in SCENARIOS:
        for config in CONFIGS:
            selected=[o for t in trials if t['scenario']==scenario and t['config']==config for o in t['operations']]
            success=[o for o in selected if o['status']=='ok']
            lat=sorted(o['latency_ms'] for o in success)
            import math
            rows.append([scenario.replace('_',' '),config,f'{len(success)}/{len(selected)}',
                f'{100*len(success)/len(selected):.1f}%',f'{statistics.median(lat):.1f}' if lat else '-',
                f'{lat[math.ceil(.95*len(lat))-1]:.1f}' if lat else '-'])
    table(['Scenario','Write/read','OK / total','OK %','p50 ms','p95 ms'],rows,[83,107,83,65,76,76])
    para('Recorded error categories: '+', '.join(f'{name}: {count}' for name,count in errors.items())+'.')
    para('A write timeout is an indeterminate outcome: some replicas may already contain the mutation. The harness does not assume failed writes were rolled back, and does not retry them. Even if later operations succeed, the affected model trial remains inconclusive. Fresh keys prevent such partial writes from contaminating later trials.')
    page()

    heading('6. Read-repair and timestamp controls')
    para('Read repair: seed a minority-only version by writing a=1 on isolated n3 at ONE. Permit only {n2,n3} to communicate and read at QUORUM through n3; then permit only {n1,n2} and read at QUORUM through n1. Repeat with each table setting. Hints remain disabled, and transitions never temporarily reconnect all three nodes.')
    rows=[]
    for table_name in ('blocking','no_repair'):
        selected=[s for s in controls if s['table']==table_name]
        sequences=Counter()
        for s in selected:
            if all(s[k]['status']=='ok' for k in ('write','first','second')):
                sequences[f"{s['first']['value']['a']} -> {s['second']['value']['a']}"]+=1
            else:
                sequences['inconclusive']+=1
        rows.append([table_name, '; '.join(f'{seq}: {n}' for seq,n in sequences.items()),len(selected)])
    table(['Table setting','Observed read sequences and counts','Trials'],rows,[110,320,60])
    regressions={t:sum(s['first']['status']=='ok' and s['second']['status']=='ok' and s['second']['value']['a']<s['first']['value']['a'] for s in controls if s['table']==t) for t in ('blocking','no_repair')}
    para(f"Observed regressions: BLOCKING={regressions['blocking']}, NONE={regressions['no_repair']}. "+('This matches the predicted contrast.' if regressions['blocking']==0 and regressions['no_repair']>0 else 'The expected contrast was not fully observed; inspect the sequences and error records before drawing conclusions.'))
    para('The intended difference is whether the first quorum read carries the minority value onto n2, the intersection member of the next quorum. This control deliberately uses an initial ONE write and changes network topology between quorum reads. It is distinct from the main fixed-topology matrix and tests the documented read-repair mechanism. [3]')
    para('Timestamp control: initialize at T, write a=1 at T+100 through n1 using ALL, then write a=2 at T+50 through n2 using ALL, and read through n3 using ALL. This models a later request carrying an older timestamp; it does not change the machines’ clocks.')
    table(['Step','Status','Returned value / effect'],[
        ['Write a=1 at T+100',skew[0]['status'],'Acknowledgement only' if skew[0]['status']=='ok' else skew[0].get('message')],
        ['Write a=2 at T+50',skew[1]['status'],'Acknowledgement only' if skew[1]['status']=='ok' else skew[1].get('message')],
        ['Read at ALL',skew[2]['status'],str(skew[2].get('value'))],
    ],[160,70,260])
    para('Cassandra resolves conflicting cell values by mutation timestamp. [2] Thus a later acknowledged request need not win if its supplied timestamp is lower. This control tests the boundary of our increasing-timestamp assumption; it is excluded from the main violation counts.')
    page()

    heading('7. Discussion, limitations and AI disclosure')
    para('The measurements distinguish consistency violations from loss of availability. Weak reads exposed replica divergence; quorum requirements instead made isolated operations unavailable. Successful quorum reads in the focused control address a different question: whether an earlier observed minority version remains visible after the read quorum changes.')
    normal=Counter(t['verdict'] for t in trials if t['scenario']=='normal')
    failure=Counter(t['verdict'] for t in trials if t['scenario']=='node_failure')
    partition=Counter(t['verdict'] for t in trials if t['scenario']=='partition')
    transient=any(o.get('error')=='ReadTimeout' for t in trials if t['scenario']=='node_failure' and t['config']=='ONE/ONE' for o in t['operations'])
    para(f"Normal operation produced {normal['no_violation_observed']} trials without a witness and {normal['violation']} witnesses. Node failure produced {failure['no_violation_observed']} trials without a witness and {failure['inconclusive']} inconclusive trials."+(' A ReadTimeout at ONE shows that the surviving replica count alone did not ensure every request completed; replica selection or detection timing may contribute, but the trace does not establish the cause.' if transient else ''))
    observed=[]
    for config in CONFIGS:
        names=[m for m in MODELS if any(t['verdict']=='violation' for t in groups['partition',config,m])]
        if names:
            observed.append(config+': '+', '.join(names))
    para(f"The partition produced {partition['violation']} witnesses ({'; '.join(observed) or 'none'}). Stale reads and missing dependencies demonstrate the predicted risks where observed. Isolated operations that require two or three replicas cannot meet that requirement. Their inconclusive trials do not empirically establish the corresponding session guarantees.")
    para('Quorum intersection is insufficient to claim all four guarantees in every execution. Our dependency checks search for a specific out-of-order visibility witness. They do not observe replica execution logs, cross-partition dependencies, concurrent writers, or all possible schedules. ALL/ALL results likewise concern completed operations under the test assumptions, not arbitrary timestamp choices or failed writes.')
    para(f"The deployment shares one host, one network bridge and one datacenter. Resource contention, pauses and connection establishment affect timing. The {env['repeats']} fixed-schedule repetitions per case cannot establish universal correctness or production failure rates. The failure scenario tests one killed node and routes subsequent work to survivors; it does not measure automatic client failover or permanent loss of storage.")
    para('Hints are normally a catch-up mechanism for unavailable replicas. [4] We disable them to retain controlled divergence and perform no background anti-entropy repair. Consequently the measurements do not estimate convergence time with default settings. Future work should repeat with hints enabled, inject latency and packet loss, vary timestamps and concurrent writers, inspect replica histories, and expand the number of machines and trials.')
    para('AI usage: OpenAI Codex assisted with experiment design, source-code creation, documentation lookup, local execution, result analysis, report generation and verification on 12 September 2026. [8] Report tables are derived from saved responses of the actual Cassandra containers; no synthetic outcomes are substituted. Group members should review and understand the code, interpretations and citations before submission. Names and course details remain editable in report/authors.json.')
    page()

    heading('8. Reproduction and references')
    para('Run python3 scripts/lab.py up, then python3 scripts/lab.py run --repeats 5. Install requirements-report.txt (ReportLab 4.4.3 and PyMuPDF 1.26.4) in a virtual environment and run scripts/build_report.py with that interpreter. The report generator selects the latest completed run; use --results results/<run> to select this one explicitly. Run python3 scripts/lab.py down afterward to release container resources while preserving volumes.')
    para('Use scripts/lab.py heal after an interruption. Review README.md for prerequisites, the macOS Compose executable override, file descriptions and cleanup. Unit tests exercise stale reads, read regression, dependency witnesses and inconclusive errors. A completion marker is required before a run can be used for the report.')
    para(f'Included run directory: results/{run.name}. Detailed deployment status, raw initialization writes, fault evidence, operation histories and both controls are retained. The generated submission.zip contains these records and the source files. SHA256SUMS.txt identifies the archived files.',small=True)
    para('References below were accessed on 12 September 2026. Cassandra documentation uses the stable branch; the installed server release and Docker digests are recorded independently.',small=True)
    for i,(title,url) in enumerate(REFERENCES,1):
        story.append(Paragraph(f'[{i}] {html.escape(title)} <link href="{html.escape(url)}" color="#235c8f">Source</link>',styles['SmallLab']))
        md.append(f'[{i}] {title} [{url}]({url})\n')
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor('#cfdae3')); canvas.line(50,43,545,43)
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#536778'))
        canvas.drawString(50,30,'Cassandra consistency experiments | '+run.name)
        canvas.drawRightString(545,30,str(doc.page))
    pdf=OUT/'Cassandra_Consistency_Report.pdf'
    SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=58,
                      title='Client-centric consistency in Apache Cassandra',author='Project group').build(story,onFirstPage=footer,onLaterPages=footer)
    (OUT/'Cassandra_Consistency_Report.md').write_text('\n'.join(md)+'\n')
    # Render every page for independent visual inspection.
    import fitz
    qa=OUT/'qa'; qa.mkdir(exist_ok=True)
    document=fitz.open(pdf)
    for index,page_obj in enumerate(document):
        page_obj.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(qa/f'page-{index+1:02}.png')
    print(f'Generated {pdf} ({len(document)} pages) from {run}')
    files=[ROOT/name for name in ['README.md','compose.yaml','Dockerfile.cassandra','Dockerfile.client','requirements-report.txt']]
    files += [f for directory in ('src','scripts','tests') for f in (ROOT/directory).glob('*.py')]
    files += [OUT/name for name in ['authors.json','predictions.md','Cassandra_Consistency_Report.pdf','Cassandra_Consistency_Report.md']]
    files += sorted(run.glob('*.json'))
    sums=''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(ROOT))+'\n' for f in files)
    (OUT/'SHA256SUMS.txt').write_text(sums)
    with zipfile.ZipFile(OUT/'submission.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for f in files+[OUT/'SHA256SUMS.txt']:
            archive.write(f,f.relative_to(ROOT))

if __name__=='__main__':
    main()
