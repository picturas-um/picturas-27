#!/usr/bin/env python3
"""Run regression suites and record actual test outcomes in the catalog."""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'docs/REGRESSION_CHECKLIST.md'
REPORTS = ROOT / 'tests/reports'
REPORTS.mkdir(exist_ok=True)

def tags(name):
    prefix = re.match(r'^\[([^]]+)\]', name)
    return re.findall(r'\b[A-Z]+-\d+(?:\.\d+)?\b', prefix.group(1)) if prefix else []

def legacy(name):
    mappings = {
        'captions apply to all videos': ['PIPE-01', 'VID-02', 'VID-04'],
        'extraction is project-wide': ['VID-05.1'],
        'extraction validates active': ['VID-05.1'],
        'manifest validation rejects': ['VID-05.2'],
        'all extracted images retain': ['VID-05.2', 'RUN-02'],
        'a fast first worker': ['RUN-01'],
        'registration failure starts': ['RUN-01', 'RUN-02'],
        'a cancelled run cannot': ['RUN-02', 'CONC-02'],
    }
    for start, ids in mappings.items():
        if name.startswith(start): return ids
    if any(name.startswith(x) for x in ('free ', 'premium ', 'anonymous account', 'unsupported ', 'zero or missing')):
        return ['UP-02.1']
    return []

KNOWN_FAILURE_DIR = ROOT / 'tests/known_failures'
KNOWN_FAILURE_IDS = set().union(*(
    set().union(*(set(re.findall(r'\b[A-Z]+-\d+(?:\.\d+)?\b', group))
                  for group in re.findall(r"(?m)^test\(['\"`]\[([^]]+)\]", path.read_text())))
    for path in KNOWN_FAILURE_DIR.glob('*.test.js')
))

def record(suite, command, code, report, started, output):
    run = 'R-' + started.strftime('%Y%m%d-%H%M%S') + '-' + suite
    outcomes, count = {}, {'PASS': 0, 'FAIL': 0, 'SKIP': 0}
    if report.exists():
        try:
            for case in ET.parse(report).iter('testcase'):
                status = 'FAIL' if case.find('failure') is not None or case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
                # Node emits file-only placeholders when a name filter selects no tests.
                if case.get('name', '').endswith('.test.js') and status == 'PASS': continue
                count[status] += 1
                if status == 'SKIP': continue
                name = case.get('name', '')
                ids = tags(name) or legacy(name)
                if not ids and suite == 'python':
                    cls = case.get('classname', '')
                    if 'test_subtitles' in cls: ids = ['VID-04']
                    elif 'test_frame_extraction' in cls: ids = ['VID-05.1', 'VID-05.2']
                    elif 'test_effects' in cls or 'test_video_processor' in cls: ids = ['VID-01', 'VID-02', 'VID-03']
                    if 'preview_contact_sheet' in name: ids = ['VID-05.3']
                for ident in ids:
                    outcomes.setdefault(ident, []).append(status)
        except ET.ParseError:
            pass
    lines = CATALOG.read_text().splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('| '): continue
        cells = [s.strip() for s in line.strip('|').split('|')]
        if len(cells) != 6 or cells[0] not in outcomes: continue
        if suite != 'known-failures' and cells[0] in KNOWN_FAILURE_IDS: continue
        states = outcomes[cells[0]]
        status = 'FAIL' if 'FAIL' in states else 'BLOCKED' if 'BLOCKED' in states else 'PASS'
        cells[-1] = f'{status} [{run}]'
        lines[i] = '| ' + ' | '.join(cells) + ' |'
    commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    state = 'com alterações locais' if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip() else 'limpo'
    summary = ', '.join(f'{n} {s}' for s, n in count.items())
    if not sum(count.values()): summary = 'BLOCKED: nenhum resultado de teste disponível'
    cmd = ' '.join(command).replace('|', '\\|')
    updated = sorted(set(outcomes) if suite == 'known-failures' else set(outcomes) - KNOWN_FAILURE_IDS)
    lines.append(f'| {run} | {started.isoformat(timespec="seconds")}; {suite}; `{commit}` {state} | `{cmd}` → {summary}; exit {code}; `{output.relative_to(ROOT)}` | {", ".join(updated) or "Nenhum ID atualizado"} |')
    CATALOG.write_text('\n'.join(lines) + '\n')
    print(f'{suite}: {summary} (exit {code}); record {run}', flush=True)
    return code == 0 and bool(count['PASS']) and not count['FAIL'], outcomes, count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('selection', choices=['all', 'unit', 'node', 'python', 'api', 'integration', 'e2e', 'security', 'resilience', 'performance', 'known-failures', 'full'])
    parser.add_argument('--match', help='Run only Node/Playwright tests whose names match this pattern')
    args = parser.parse_args()
    choices = {'all': ['node', 'python', 'api', 'integration', 'security', 'e2e'],
               'unit': ['node', 'python'],
               'full': ['node', 'python', 'api', 'integration', 'security', 'e2e', 'resilience', 'performance']}
    suites = choices.get(args.selection, [args.selection])
    ok, combined, totals, run_ids = True, {}, {'PASS': 0, 'FAIL': 0, 'SKIP': 0}, []
    full_start = dt.datetime.now(dt.timezone.utc)
    for suite in suites:
        stamp = dt.datetime.now(dt.timezone.utc)
        label = stamp.strftime('%Y%m%d-%H%M%S') + '-' + suite
        report, output = REPORTS / (label + '.xml'), REPORTS / (label + '.log')
        if suite == 'node':
            command = ['node', '--test', '--test-reporter=junit', *map(str, sorted((ROOT / 'projects/tests').glob('*.test.js')))]
        elif suite == 'python':
            command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', f'--junitxml={report}']
        elif suite == 'e2e':
            command = ['node_modules/.bin/playwright', 'test', '--reporter=junit']
            if args.match: command += ['--grep', args.match]
        else:
            directory = (ROOT / 'tests' / suite if suite == 'performance' else
                         KNOWN_FAILURE_DIR if suite == 'known-failures' else
                         ROOT / 'tests' / 'functional' / suite)
            files = sorted(directory.rglob('*.test.js'))
            command = ['node', '--test', '--test-concurrency=1', '--test-reporter=junit']
            if args.match: command += ['--test-name-pattern=' + args.match]
            command += list(map(str, files))
        print('Running', suite, flush=True)
        registry = REPORTS / (label + '-users.jsonl')
        with output.open('w') as log:
            try:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800,
                                        env={**os.environ, 'TEST_REGISTRY_PATH': str(registry)})
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                log.write(str(error)); code = 2
        if suite != 'python':
            content = output.read_text(errors='replace')
            start = content.find('<?xml')
            if start < 0: start = content.find('<testsuites')
            end = content.rfind('</testsuites>')
            if start >= 0 and end >= 0: report.write_text(content[start:end + len('</testsuites>')])
        with (REPORTS / 'catalog.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            passed, outcomes, count = record(suite, command, code, report, stamp, output)
            ok = passed and ok
        for ident, states in outcomes.items(): combined.setdefault(ident, []).extend(states)
        for status, n in count.items(): totals[status] += n
        run_ids.append(label)
        if registry.exists():
            cleanup = subprocess.run(['node', 'scripts/cleanup-test-data.js', str(registry)], cwd=ROOT, capture_output=True, text=True)
            with output.open('a') as log: log.write('\nCLEANUP\n' + cleanup.stdout + cleanup.stderr)
            if cleanup.returncode:
                print(f'Cleanup failed; see {output}', flush=True); ok = False
    if len(suites) > 1:
        run = 'R-' + full_start.strftime('%Y%m%d-%H%M%S') + '-' + args.selection
        with (REPORTS / 'catalog.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            lines = CATALOG.read_text().splitlines()
            for i, line in enumerate(lines):
                cells = [s.strip() for s in line.strip('|').split('|')]
                if line.startswith('| ') and len(cells) == 6 and cells[0] in combined and cells[0] not in KNOWN_FAILURE_IDS:
                    states = combined[cells[0]]
                    status = 'FAIL' if 'FAIL' in states else 'BLOCKED' if 'BLOCKED' in states else 'PASS'
                    cells[-1] = f'{status} [{run}]'; lines[i] = '| ' + ' | '.join(cells) + ' |'
            summary = ', '.join(f'{n} {s}' for s, n in totals.items())
            updated = sorted(set(combined) - KNOWN_FAILURE_IDS)
            lines.append(f'| {run} | {full_start.isoformat(timespec="seconds")}; execução agregada | `python3 scripts/regression.py {args.selection}` → {summary}; suites: {", ".join(run_ids)} | {", ".join(updated)} |')
            CATALOG.write_text('\n'.join(lines) + '\n')
        print(f'Total: {summary}', flush=True)
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
