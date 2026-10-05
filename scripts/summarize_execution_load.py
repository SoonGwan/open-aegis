"""Summarize completed owned rehearsal measurements; no SLO/pass inference."""
import argparse
import json
from pathlib import Path
import statistics


def summarize(data,progress=()):
    if data.get('valid') is not True or data.get('temporary_resources_removed') is not True:
        raise ValueError('A completed successful rehearsal with cleanup evidence is required')
    elapsed=data['elapsed_seconds'];samples=data['samples'];baseline=data['baseline']
    if not samples or elapsed<=0:raise ValueError('Resource samples and positive duration required')
    quarters=[];previous=baseline;previous_reads=0
    for index in range(4):
        low=elapsed*index/4;high=elapsed*(index+1)/4
        selected=[sample for sample in samples if low<=sample['elapsed'] and (sample['elapsed']<high or index==3)]
        if not selected:
            quarters.append({'quarter':index+1,'sample_count':0});continue
        rss=[row['rss_kib'] for row in selected];end=selected[-1]
        quarters.append({'quarter':index+1,'sample_count':len(selected),
            'first_elapsed_seconds':selected[0]['elapsed'],'last_elapsed_seconds':end['elapsed'],
            'rss_median_kib':statistics.median(rss),'rss_min_kib':min(rss),'rss_max_kib':max(rss),
            'cpu_seconds_since_previous_window':round(end['cpu_seconds']-previous['cpu_seconds'],3)})
        previous=end
        read_window=[row for row in progress if low<=row['elapsed_seconds']<high or (index==3 and row['elapsed_seconds']>=low)]
        if read_window:
            observed=read_window[-1];quarters[-1].update(read_responses_since_previous_observed_window=observed['read_responses']-previous_reads,
                read_observation_end_seconds=observed['elapsed_seconds'])
            previous_reads=observed['read_responses']
    return {'measurement_only':True,'backend':data['backend'],'source_sha256':data['source_sha256'],
        'elapsed_seconds':elapsed,'cycles':data['cycles'],'read_responses':sum(data['read_responses'].values()),
        'resource_windows':quarters,'peak_pending_events':data.get('peak_pending_events'),
        'peak_event_age_seconds':data.get('peak_event_age_seconds'),
        'disk':data.get('disk'),'last_sample_rss_kib':samples[-1]['rss_kib'],
        'last_sample_minus_baseline_rss_kib':samples[-1]['rss_kib']-baseline['rss_kib'],
        'sampled_latency_seconds':data['sampled_latency_seconds'],'recovery':data['recovery'],
        'limits':'Quarter windows are observations, not memory growth attribution or production SLO certification.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--progress-log',type=Path,help='Optional same-run stdout receipts for observed read counts by window')
    args=parser.parse_args();data=json.loads(args.input.read_text());progress=[]
    if args.progress_log:
        for line in args.progress_log.read_text().splitlines():
            try:row=json.loads(line)
            except json.JSONDecodeError:continue
            if row.get('stage')=='execution_and_reads':
                if row.get('backend')!=data['backend']:raise ValueError('Progress backend mismatch')
                progress.append(row)
        if not progress:raise ValueError('No execution progress receipts found')
        if any(a['elapsed_seconds']>=b['elapsed_seconds'] or a['read_responses']>b['read_responses'] for a,b in zip(progress,progress[1:])):
            raise ValueError('Progress receipts must retain increasing time and cumulative read counts')
    summary=summarize(data,progress)
    encoded=json.dumps(summary,indent=2)
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded)
    print(encoded)


if __name__=='__main__':main()
