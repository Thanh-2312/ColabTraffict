#!/usr/bin/env python3
"""Audit the DoAn graph with real controllers and continuous vehicle checks."""
import argparse
import json
import math
import os
import signal
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'Traffic/models'
HEADLESS = Path(os.environ.get(
    'GAMA_HEADLESS', '/Applications/Gama.app/Contents/headless/gama-headless.sh'
))
FIELDS = ('cycle topology_errors failed_routes red_entries overlaps lane_errors green_idle '
          'phase_errors unsafe_merges empty_changes wrong_routes jumps min_acc ground_created '
          'ground_passed bypass_created bypass_passed left_completed right_completed uturn_completed '
          'phase_changes min_z max_z ramp_samples stopbar_violations '
          'surface_on_open_ramp uturn_wrong_lane uturn_entries_without_green remote_idle').split()
CONTROLLERS = {'fixed': 'fixed-time', 'maxpressure': 'maxpressure', 'qlearning': 'qlearning',
               'dqn': 'dqn-legacy', '3dqn': 'dqn-python'}
CASES = {name: (name, 15, 45, .20, .15, .05, True) for name in CONTROLLERS}
CASES.update({turn: ('fixed', 100, 100, float(turn == 'left'), float(turn == 'right'),
                    float(turn == 'uturn'), False) for turn in ('left', 'right', 'uturn')})
CASES['empty'] = ('fixed', 100, 100, .2, .15, .05, False)
CASES['merge_recovery'] = CASES['fixed']
CASES['overtaken_owner'] = CASES['fixed']


def run_case(name, output, horizon, seed):
    controller, ns, ew, left, right, uturn, bypass = CASES[name]
    source = (MODELS / 'test_doan_integration.gaml').read_text()
    source = source.replace('intersection-fixed-time.gaml', f'intersection-{CONTROLLERS[controller]}.gaml')
    source = source.replace('int audit_horizon <- 6000', f'int audit_horizon <- {horizon}')
    source = source.replace('5001.0', f'{seed}.0')
    source = source.replace('var: spawn_rate_NS init: 100', f'var: spawn_rate_NS init: {ns}')
    source = source.replace('var: spawn_rate_EW init: 100', f'var: spawn_rate_EW init: {ew}')
    source = source.replace('var: bypass_spawn_interval init: 200', 'var: bypass_spawn_interval init: 120')
    settings = f'''parameter "Left share" var: left_turn_share init: {left};
    parameter "Right share" var: right_turn_share init: {right};
    parameter "U-turn share" var: uturn_share init: {uturn};
    parameter "Bypass" var: enable_bypass_traffic init: {str(bypass).lower()};
    parameter "Force merge stall" var: audit_force_merge_stall init: {str(name == 'merge_recovery').lower()};
    parameter "Force overtaken owner" var: audit_force_overtaken_owner init: {str(name == 'overtaken_owner').lower()};
    parameter "Merge trace" var: debug_merge_arbitration init: true;
    parameter "Ground" var: enable_ground_traffic init: {str(name != 'empty').lower()};'''
    source = source.replace('parameter "Seed"', settings + '\nparameter "Seed"', 1)
    if controller in ('dqn', '3dqn'):
        source = source.replace('global {',
                                'global {\nreflex audit_local_dqn when: cycle = 0 { '
                                f'python_controlled <- false; audit_direct_phase <- {str(controller == "3dqn").lower()}; }}', 1)
    with tempfile.NamedTemporaryFile('w', suffix='.gaml', prefix='tmp_doan_suite_', dir=MODELS, delete=False) as f:
        f.write(source)
        model = Path(f.name)
    log = output / f'{name}.log'
    completed = False
    try:
        with tempfile.TemporaryDirectory(prefix='doan_gama_') as work, log.open('w') as stream:
            configuration = Path(work) / 'configuration'
            configuration.mkdir()
            process = subprocess.Popen(['bash', str(HEADLESS), '-configuration', str(configuration),
                                        '-m', '2048m', '-batch', 'doan_audit_batch', str(model)],
                                    cwd=work, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                                    env={**os.environ, '_JAVA_OPTIONS': os.environ.get('_JAVA_OPTIONS', '') +
                                         ' -Xms256m -Xmx2g -XX:-AlwaysPreTouch'})
            try:
                deadline = time.monotonic() + 1800
                while process.poll() is None and time.monotonic() < deadline:
                    content = log.read_text(errors='replace')
                    if (f'DOAN_AUDIT,{horizon - 1},' in content and
                            'DOAN_ROUTES,' in content and 'DOAN_MOVEMENTS,' in content):
                        completed = True
                        # GAMA 2025 can keep the batch JVM alive after writing
                        # the final audit record. The checked output is complete.
                        os.killpg(process.pid, signal.SIGTERM)
                        break
                    time.sleep(0.5)
                returncode = process.wait(timeout=30)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=30)
                raise
    finally:
        model.unlink(missing_ok=True)
    content = log.read_text()
    rows = re.findall(r'^DOAN_AUDIT,(.+)$', content, re.M)
    if (returncode and not completed) or not rows:
        return dict(case=name, passed=False, error='GAMA failed or no audit records', log=str(log))
    metrics = dict(zip(FIELDS, map(float, rows[-1].split(',')), strict=True))
    checks = {key: metrics[key] == 0 for key in FIELDS[1:12]}
    checks.update(completed=metrics['cycle'] == horizon - 1,
                  finite=all(map(math.isfinite, metrics.values())), braking_bound=metrics['min_acc'] >= -12)
    checks['stop_before_bar'] = metrics['stopbar_violations'] == 0
    checks['surface_vehicles_have_roadbed'] = metrics['surface_on_open_ramp'] == 0
    checks['uturn_bypasses_signal_lane'] = metrics['uturn_wrong_lane'] == 0
    checks['no_unexplained_upstream_stops'] = metrics['remote_idle'] == 0
    if name == 'fixed' and horizon >= 3000:
        checks['no_extended_merge_wait'] = 'DOAN_MERGE_WAIT,' not in content
    if name == 'fixed' and horizon >= 1500:
        checks['follower_recovers'] = 'DOAN_FOLLOW_DELAY,' not in content
    seeds = re.findall(r'^DOAN_SEED,(.+)$', content, re.M)
    actual_seed = float(seeds[-1]) if seeds else None
    checks['seed_applied'] = actual_seed == seed
    if name == 'merge_recovery':
        checks['stall_injected'] = 'DOAN_FORCED_MERGE_STALL,' in content
        checks['reservation_reassigned'] = 'DOAN_MERGE_REASSIGNED,' in content
        checks['old_owner_resumed'] = 'DOAN_MERGE_OWNER_RESUMED,' in content
        checks['old_owner_crossed'] = 'DOAN_MERGE_OWNER_CROSSED,' in content
    if name == 'overtaken_owner':
        inversion = re.search(r'^DOAN_OVERTAKEN_INJECTED,(\d+),', content, re.M)
        readmitted = re.search(r'^DOAN_OVERTAKEN_REASSIGNED,(\d+),', content, re.M)
        checks['reservation_inverted'] = inversion is not None
        checks['front_car_readmitted'] = (inversion is not None and readmitted is not None and
                                          0 < int(readmitted.group(1)) - int(inversion.group(1)) <= 2)
    routes = re.findall(r'^DOAN_ROUTES,(.+)$', content, re.M)[-1]
    movements = re.findall(r'^DOAN_MOVEMENTS,(.+)$', content, re.M)[-1]
    if name == 'empty':
        checks['empty_network'] = metrics['ground_created'] == metrics['bypass_created'] == 0
    else:
        # Protected movements get only a short green in each full signal cycle.
        # Their dedicated cases verify completion on all four approaches below.
        if horizon >= 4000 or name in ('left', 'right', 'uturn'):
            checks['ground_progress'] = metrics['ground_passed'] > (0 if name in ('left', 'right', 'uturn') else 10)
        if name in ('left', 'right', 'uturn'):
            checks['movement_completed'] = metrics[f'{name}_completed'] > 0
            checks['four_approaches'] = all(f"'{arm}_{name}'::" in movements for arm in 'ENWS')
            if name == 'uturn':
                checks['uturn_moves_during_red'] = metrics['uturn_entries_without_green'] > 0
        if bypass:
            checks['grade_separation'] = metrics['min_z'] == -60 and metrics['max_z'] == 50 and metrics['ramp_samples'] > 0
            if horizon >= 6000:
                checks['eight_bypass_routes'] = all(f"'{route}'::" in routes for route in
                    ('flyover_NS', 'flyover_SN', 'on_N', 'on_S', 'off_N', 'off_S', 'tunnel_WE', 'tunnel_EW'))
    if name in ('merge_recovery', 'overtaken_owner'):
        # These cases check reservation recovery before all routes complete.
        if name == 'merge_recovery':
            checks.pop('braking_bound')
        checks.pop('eight_bypass_routes', None)
        checks.pop('ground_progress', None)
    return dict(case=name, seed=seed, actual_seed=actual_seed, horizon=horizon, passed=all(checks.values()), checks=checks,
                metrics=metrics, routes=routes, movements=movements, log=str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=list(CASES), default=list(CASES))
    parser.add_argument('--horizon', type=int, default=8000)
    parser.add_argument('--seed', type=int, default=5001)
    parser.add_argument('--output', type=Path, default=ROOT / 'comparison_results' / ('doan_integration_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for case in args.cases:
        case_horizon = min(args.horizon, 1000) if case == 'empty' else (
            min(args.horizon, 1200) if case in ('merge_recovery', 'overtaken_owner') else args.horizon)
        item = run_case(case, args.output, case_horizon, args.seed)
        results.append(item)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(case, 'PASS' if item['passed'] else 'FAIL', {k: v for k, v in item.get('checks', {}).items() if not v}, flush=True)
    print(args.output, flush=True)
    return 0 if all(x['passed'] for x in results) else 1

if __name__ == '__main__':
    raise SystemExit(main())
