#!/usr/bin/env python3
"""
==============================================================================
SMOKE TEST - Kiem chung giao thuc GAMA <-> Python truoc khi train
==============================================================================
Kiem tra lan luot cac gia dinh cua protocol (chay sau khi gama-server san sang):
  T1. Ket noi WebSocket den gama-server
  T2. describe model -> thay experiment dqn_server_experiment
  T3. load experiment -> nhan exp_id
  T4. expression GET bien (doc state_pack, tach 18 truong)
  T5. expression SET bien (dqn_action <- 1) -> doc lai dung gia tri
  T6. step(sync=True) chay dung so cycle (100 cycles -> dung tick 10s)
  T7. Handshake day du: tai tick -> set action SWITCH -> step(1)
      -> global_phase doi sang THROUGH-YELLOW, next_decision_in_cycles = 280
  T8. reload(seed=...) reset simulation ve cycle 0
  T9. ask command goi action set_dqn_action (duong lut khi SET bi loi)

Vi du:
    venv/bin/python smoke_test.py --port 6868
==============================================================================
"""

import argparse
import asyncio
import json

from gama_client.sync_client import GamaSyncClient

from gama_env import DEFAULT_MODEL, STATE_PACK_EXPR, STATE_FIELDS, GamaEnvError
from server_manager import GAMA_HEADLESS

RESULTS = []


def check(test_id, ok, detail=""):
    RESULTS.append((test_id, ok, detail))
    icon = "✅ PASS" if ok else "❌ FAIL"
    print(f"  {icon} | {test_id:14s} | {detail}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6868)
    parser.add_argument("--host", type=str, default="localhost")
    args = parser.parse_args()

    print("\n=== SMOKE TEST GAMA <-> PYTHON PROTOCOL ===")
    try:
        # GamaSyncClient phai duoc tao BEN TRONG event loop dang chay
        client = GamaSyncClient(args.host, args.port,
                                other_message_handler=_silent_handler,
                                default_timeout=600.0)
        await client.connect_awaitable()
        check("T1-connect", True, f"ws://{args.host}:{args.port}")
    except Exception as e:
        check("T1-connect", False, f"{e} - gama-server da chay chua? "
                                   f"(bash {GAMA_HEADLESS} -socket {args.port})")
        return 1

    model_path = DEFAULT_MODEL

    # T2: Describe
    try:
        resp = await client.describe_awaitable(model_path, timeout=600.0)
        content = str(resp.get("content", ""))
        ok = resp.get("type") == "CommandExecutedSuccessfully" and "dqn_server_experiment" in content
        check("T2-describe", ok, "experiment dqn_server_experiment duoc tim thay"
              if ok else f"resp={json.dumps(resp)[:300]}")
    except Exception as e:
        check("T2-describe", False, str(e)[:200])

    # T3: Load
    try:
        resp = await client.load_awaitable(model_path, "dqn_server_experiment",
                                           console=False, status=False, dialog=False,
                                           runtime=True, timeout=600.0)
        exp_id = resp.get("content")
        ok = resp.get("type") == "CommandExecutedSuccessfully" and exp_id is not None
        check("T3-load", ok, f"exp_id={exp_id}" if ok else f"resp={json.dumps(resp)[:300]}")
    except Exception as e:
        check("T3-load", False, str(e)[:200])
        client.close_connection()
        return 1

    async def expr(e):
        r = await client.expression_awaitable(exp_id, e, timeout=600.0)
        if r.get("type") != "CommandExecutedSuccessfully":
            raise GamaEnvError(f"expr failed: {e} -> {r}")
        c = r.get("content")
        return c[0] if isinstance(c, list) and c else c

    # T4: GET state pack
    try:
        raw = await expr(STATE_PACK_EXPR)
        parts = str(raw).split("|")
        check("T4-get-state", len(parts) == len(STATE_FIELDS),
              f"{len(parts)}/{len(STATE_FIELDS)} truong: cycle={parts[0]}, "
              f"phase={parts[1]}, waiting={parts[16] if len(parts) > 16 else '?'}")
    except Exception as e:
        check("T4-get-state", False, str(e)[:200])

    # T5: SET action qua lenh ask (agent="world.0" + args JSON string)
    try:
        resp = await client.ask_awaitable(exp_id, "set_dqn_action", '{"a": 1.0}',
                                          "world.0", timeout=600.0)
        ok_set = resp.get("type") == "CommandExecutedSuccessfully"
        val = await expr("dqn_action") if ok_set else None
        check("T5-set-action", ok_set and str(val) in ("1", "1.0"),
              f"ask set_dqn_action OK, dqn_action = {val}" if ok_set
              else f"resp={str(resp)[:200]}")
        if ok_set:
            await client.ask_awaitable(exp_id, "set_dqn_action", '{"a": -1.0}',
                                       "world.0", timeout=600.0)
    except Exception as e:
        check("T5-set-action", False, str(e)[:200])

    # T6: step(sync) chay dung so cycle
    try:
        await client.step_awaitable(exp_id, 100, sync=True, timeout=600.0)
        cycle_after = int(float(await expr("cycle")))
        check("T6-step-100", cycle_after == 100,
              f"cycle sau step(100) = {cycle_after} (dung tai tick dau tien 10s)")
    except Exception as e:
        check("T6-step-100", False, str(e)[:200])

    # T7: Handshake day du tai tick dau tien (10s)
    try:
        waiting = str(await expr("dqn_waiting_action")).lower() == "true"
        green_cycles = int(float(await expr("green_cycles")))
        ok_wait = waiting and green_cycles == 100
        check("T7a-waiting-tick", ok_wait,
              f"waiting={waiting}, green_cycles={green_cycles} (tick o 10s)" if ok_wait
              else f"waiting={waiting}, green_cycles={green_cycles}")
        if ok_wait:
            # SWITCH qua lenh ask
            await client.ask_awaitable(exp_id, "set_dqn_action", '{"a": 1.0}',
                                       "world.0", timeout=600.0)
            await client.step_awaitable(exp_id, 1, sync=True, timeout=600.0)
            phase_after = int(float(await expr("global_phase")))
            waiting_after = str(await expr("dqn_waiting_action")).lower() == "true"
            nb = int(float(await expr("next_decision_in_cycles")))
            ok = (phase_after == 1) and (not waiting_after) and (nb == 280)
            check("T7b-handshake", ok,
                  f"phase={phase_after} (1=NS-YELLOW dung), next_decision={nb} "
                  f"(30 vang + 120 re trai + 30 vang + 100 min green = 280)"
                  if ok else f"phase={phase_after}, waiting={waiting_after}, nb={nb}")
    except Exception as e:
        check("T7b-handshake", False, str(e)[:200])

    # T8: reload + seed
    try:
        resp = await client.reload_awaitable(
            exp_id, parameters=[{"type": "float", "value": "123.0", "name": "rng_seed"}],
            timeout=600.0)
        cycle0 = int(float(await expr("cycle")))
        ok = resp.get("type") == "CommandExecutedSuccessfully" and cycle0 == 0
        check("T8-reload-seed", ok, f"reload OK, cycle={cycle0}, seed=123"
              if ok else f"resp={json.dumps(resp)[:200]}, cycle={cycle0}")
    except Exception as e:
        check("T8-reload-seed", False, str(e)[:200])

    # T9: ask command goi action set_dqn_action (phan hoi co kiem tra dung)
    try:
        resp = await client.ask_awaitable(exp_id, "set_dqn_action", '{"a": 0.0}',
                                          "world.0", timeout=600.0)
        ok = resp.get("type") == "CommandExecutedSuccessfully"
        val = await expr("dqn_action") if ok else None
        if ok:
            await client.ask_awaitable(exp_id, "set_dqn_action", '{"a": -1.0}',
                                       "world.0", timeout=600.0)
        check("T9-ask-action", ok and str(val) in ("0", "0.0"),
              f"ask OK, dqn_action={val}" if ok else f"resp={str(resp)[:200]}")
    except Exception as e:
        check("T9-ask-action", False, str(e)[:200])

    # Tong ket
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n=== KET QUA: {n_pass}/{len(RESULTS)} PASS ===")
    if n_pass == len(RESULTS):
        print("🎉 Toan bo giao thuc hoat dong -> chay train: "
              "venv/bin/python train.py --start-server")
    else:
        print("⚠️  Co test FAIL - kiem tra lai protocol/model truoc khi train.")
    client.close_connection()
    return 0 if n_pass == len(RESULTS) else 1

async def _silent_handler(message):
    """An cac message server (console/status) de test sach se."""
    return


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
