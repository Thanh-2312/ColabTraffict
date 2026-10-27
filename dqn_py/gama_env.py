#!/usr/bin/env python3
"""
==============================================================================
GAMA TRAFFIC ENV - WebSocket bridge for the four-phase DTSE 3DQN agent
==============================================================================
Giao tiep voi gama-server qua thu vien chinh thuc `gama-client` (WebSocket).

CHU Y: gama-client 2.x yeu cau event loop dang chay khi tao client va khi goi
lenh -> moi method o day la ASYNC, dung ben trong `asyncio.run(main())`:

    Python                                    GAMA (intersection-dqn-python.gaml)
    ------                                    -----------------------------------
    await load_awaitable(...)     ->  exp_id
    await expression_awaitable(GET state) -> metrics (18 fields)
    await ask_awaitable(capture_dtse) -> 3x8x20 DTSE and squared delay
    await expression_awaitable("dqn_action <- a")
    await step_awaitable(exp_id, 1, sync=True)  ->  controller ap dung action
    await expression_awaitable(GET next_decision_in_cycles)
    await step_awaitable(exp_id, nb, sync=True) ->  chay dung den tick ke tiep

Protocol chi tiet xem header cua Traffic/models/intersection-dqn-python.gaml
==============================================================================
"""

import asyncio
import json
import os
import re

# Vo hieu hoa nest_asyncio.apply vi no lam hong asyncio.current_task() tren Python 3.12+ (dac biet Python 3.14)
try:
    import nest_asyncio
    nest_asyncio.apply = lambda *args, **kwargs: None
except Exception:
    pass

import numpy as np
from gama_client.sync_client import GamaSyncClient

# Tang timeout mo WebSocket len 180s va vo hieu hoa keepalive ping timeout
# (GAMA xu ly nang trong Java se bi cham phan hoi Ping -> gay loi 'sent 1011 keepalive ping timeout')
try:
    import websockets
    _orig_ws_connect = websockets.connect
    def _patched_ws_connect(*args, **kwargs):
        kwargs["open_timeout"] = 180.0
        kwargs["ping_interval"] = None
        kwargs["ping_timeout"] = None
        kwargs["close_timeout"] = 30.0
        return _orig_ws_connect(*args, **kwargs)
    websockets.connect = _patched_ws_connect
    if hasattr(websockets, "legacy") and hasattr(websockets.legacy, "client"):
        websockets.legacy.client.connect = _patched_ws_connect
        if hasattr(websockets.legacy.client, "Connect"):
            _orig_c_init = websockets.legacy.client.Connect.__init__
            def _patched_c_init(self, *args, **kwargs):
                kwargs["open_timeout"] = 180.0
                kwargs["ping_interval"] = None
                kwargs["ping_timeout"] = None
                kwargs["close_timeout"] = 30.0
                return _orig_c_init(self, *args, **kwargs)
            websockets.legacy.client.Connect.__init__ = _patched_c_init
except Exception:
    pass

# Duong dan mac dinh
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(
    os.path.dirname(BASE_DIR), "Traffic", "models", "intersection-dqn-python.gaml"
)

# Bieu thuc GAML: dong goi 18 bien thanh 1 chuoi "|" de 1 request lay het state
STATE_PACK_EXPR = (
    '"" + cycle + "|" + global_phase + "|" + green_cycles + "|" + yellow_cycles'
    + ' + "|" + queue_ns + "|" + queue_ew + "|" + approach_ns + "|" + approach_ew'
    + ' + "|" + current_queue_length'
    + ' + "|" + (round(average_waiting_time*100.0)/100.0)'
    + ' + "|" + (round(max_waiting_time*100.0)/100.0)'
    + ' + "|" + (round(average_speed*100.0)/100.0)'
    + ' + "|" + (round(average_travel_time*100.0)/100.0)'
    + ' + "|" + total_vehicles_passed + "|" + total_vehicles_created'
    + ' + "|" + decision_count + "|" + dqn_waiting_action'
    + ' + "|" + next_decision_in_cycles'
)

STATE_FIELDS = [
    "cycle", "global_phase", "green_cycles", "yellow_cycles",
    "queue_ns", "queue_ew", "approach_ns", "approach_ew",
    "current_queue_length", "average_waiting_time", "max_waiting_time",
    "average_speed", "average_travel_time",
    "total_vehicles_passed", "total_vehicles_created",
    "decision_count", "dqn_waiting_action", "next_decision_in_cycles",
]

INT_FIELDS = {
    "cycle", "global_phase", "green_cycles", "yellow_cycles",
    "queue_ns", "queue_ew", "approach_ns", "approach_ew",
    "current_queue_length", "total_vehicles_passed",
    "total_vehicles_created", "decision_count", "next_decision_in_cycles",
}

# DTSE shape and normalization are defined by capture_dtse in the GAML model.
class GamaEnvError(Exception):
    pass


class GamaTrafficEnv:
    """
    Moi truong giao thong GAMA (async, giao dien gym-ish).

    Cach dung (ben trong asyncio.run):
        env = GamaTrafficEnv(port=6868)
        await env.setup()          # ket noi; reset se load experiment
        state = await env.reset(seed=42)
        next_state, reward, done, info = await env.step(action)
        await env.close()
    """

    def __init__(self, host="localhost", port=6868,
                 model_path=DEFAULT_MODEL, experiment="dqn_server_experiment",
                 verbose=True, timeout=600.0, reward_scope="all",
                 reward_mode="reference", max_delay_sq=None):
        if reward_scope not in ("all", "near"):
            raise ValueError(f"Unknown reward scope: {reward_scope}")
        if reward_mode not in ("reference", "queue_time"):
            raise ValueError(f"Unknown reward mode: {reward_mode}")
        self.max_delay_sq = float(max_delay_sq) if max_delay_sq is not None else None
        self.host = host
        self.port = int(port)
        self.model_path = model_path or DEFAULT_MODEL
        self.experiment = experiment
        self.verbose = verbose
        self.timeout = float(timeout)
        self.reward_scope = reward_scope
        self.reward_mode = reward_mode
        self.action_count = 4
        self.exp_id = None
        self.client = None
        self._server_messages = []
        self._worst_delay_sq = 0.0

    # --------------------------------------------------------- server events
    async def _on_server_message(self, message):
        """Nhan cac message khong phai answer lenh (console, status, error...)."""
        self._server_messages.append(message)
        mtype = message.get("type", "") if isinstance(message, dict) else ""
        if mtype in ("SimulationError", "RuntimeError", "GamaServerError",
                     "SimulationErrorDialog"):
            print(f"[GamaEnv][SERVER-{mtype}] {message}")

    # ------------------------------------------------------------ lifecycle
    async def setup(self, max_retries=15, retry_delay=3.0):
        """Connect to gama-server; first reset loads the seeded experiment."""
        for attempt in range(1, max_retries + 1):
            try:
                self.client = GamaSyncClient(
                    self.host, self.port,
                    other_message_handler=self._on_server_message,
                    default_timeout=self.timeout,
                )
                await self.client.connect_awaitable(ping_interval=None, ping_timeout=None)
                if self.verbose:
                    print(f"[GamaEnv] Da ket noi ws://{self.host}:{self.port}")
                return
            except (TimeoutError, asyncio.TimeoutError, OSError, Exception) as ex:
                if attempt == max_retries:
                    raise GamaEnvError(f"Khong the ket noi ws://{self.host}:{self.port} sau {max_retries} lan thu: {ex}")
                print(f"[GamaEnv] Cho WebSocket port {self.port} on dinh (lan {attempt}/{max_retries})...")
                await asyncio.sleep(retry_delay)
        # The first reset will load the model with its episode seed. Loading
        # here and immediately reloading it races GAMA's simulation startup.

    async def load_experiment(self, parameters=None):
        resp = await self.client.load_awaitable(
            self.model_path, self.experiment,
            console=False, status=False, dialog=False, runtime=True,
            parameters=parameters,
            timeout=self.timeout,
        )
        rtype = resp.get("type", "")
        if rtype != "CommandExecutedSuccessfully":
            raise GamaEnvError(f"Loi load experiment: {resp}")
        self.exp_id = resp.get("content")
        # gama-server may start the newly loaded GUI experiment immediately.
        # Pause before the first reload/step so its worker cannot mutate the
        # vehicle population while a new simulation is being initialized.
        await self.pause()
        if self.verbose:
            print(f"[GamaEnv] Da load '{self.experiment}' -> exp_id={self.exp_id}")
        return self.exp_id

    async def close(self):
        try:
            if self.client is not None and self.exp_id is not None:
                await self.pause()
                # Let the simulation worker finish its current reflex before
                # disconnecting. Stopping a just-paused experiment can clear
                # its agent scope while the traffic driving skill is running.
                await asyncio.sleep(0.5)
        finally:
            if self.client is not None:
                try:
                    await self.client.close_connection_async()
                except Exception:
                    try:
                        self.client.close_connection()
                    except Exception:
                        pass
                self.client = None
            self.exp_id = None

    async def pause(self):
        resp = await self.client.pause_awaitable(self.exp_id, timeout=self.timeout)
        if resp.get("type") != "CommandExecutedSuccessfully":
            raise GamaEnvError(f"Could not pause GAMA experiment: {resp}")

    # ------------------------------------------------------------ primitives
    async def _exec_expression(self, expr):
        """Chay 1 bieu thuc GAML trong exp_id, tra ve content."""
        resp = await self.client.expression_awaitable(
            self.exp_id, expr, timeout=self.timeout)
        rtype = resp.get("type", "")
        if rtype != "CommandExecutedSuccessfully":
            raise GamaEnvError(f"Expression failed: '{expr}' -> {resp}")
        content = resp.get("content")
        if isinstance(content, list) and content:
            content = content[0]
        return content

    # ------------------------------------------------------------ state I/O
    async def read_state(self, force_dtse=False):
        """Doc 18 bien state cua GAMA trong 1 request."""
        raw = await self._exec_expression(STATE_PACK_EXPR)
        parts = str(raw).split("|")
        if len(parts) != len(STATE_FIELDS):
            raise GamaEnvError(
                f"state_pack sai dinh dang ({len(parts)} truong thay vi "
                f"{len(STATE_FIELDS)}): '{raw}'"
            )
        state = {}
        for name, val in zip(STATE_FIELDS, parts):
            if name == "dqn_waiting_action":
                state[name] = str(val).strip().lower() == "true"
            elif name in INT_FIELDS:
                state[name] = int(float(val))
            else:
                state[name] = float(val)
        if state["dqn_waiting_action"] or force_dtse:
            resp = await self.client.ask_awaitable(
                self.exp_id, "capture_dtse", "{}", "world.0", timeout=self.timeout)
            if resp.get("type") != "CommandExecutedSuccessfully":
                raise GamaEnvError(f"capture_dtse failed: {resp}")
            raw_dtse = str(await self._exec_expression("dtse_pack"))
            values = np.asarray([float(x) for x in re.findall(
                r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", raw_dtse
            )], dtype=np.float32)
            if values.size != 480:
                raise GamaEnvError(f"DTSE has {values.size} values; expected 480")
            state["dtse"] = values.reshape(3, 8, 20)
            delay_field = ("dtse_delay_sq" if self.reward_scope == "all"
                           else "dtse_delay_sq_near")
            state["delay_sq"] = float(await self._exec_expression(delay_field))
            state["queue_time_integral"] = float(await self._exec_expression("queue_time_integral"))
            raw_mask = str(await self._exec_expression("'' + dqn_action_mask"))
            state["action_mask"] = np.asarray(
                [int(x) for x in re.findall(r"\d+", raw_mask)], dtype=np.bool_)
            if state["action_mask"].shape != (4,) or not state["action_mask"].any():
                raise GamaEnvError(f"Invalid action mask: {raw_mask}")
            if not np.isfinite(values).all() or not np.isfinite(state["delay_sq"]):
                raise GamaEnvError("Non-finite DTSE or reward input")
        return state

    async def set_action(self, action):
        """Send selected green phase (0..3) to GAMA through an ask command.

        QUAN TRONG:
          - agent phai la dang tham chieu '<ten>.0' (world agent index 0) vi
            `AgentReference` ben server split theo dau cham; neu khong co duoi
            `.0` thi loi AIOOBE lam server khong tra loi (timeout).
          - args phai la mot JSON STRING (server lam `Json.parse((String) args)`);
            neu gui dict -> ClassCastException -> timeout.
        """
        if action not in range(self.action_count):
            raise GamaEnvError(f"Action khong hop le: {action}")
        args = json.dumps({"a": float(action)})
        resp = await self.client.ask_awaitable(
            self.exp_id, "set_dqn_action", args, "world.0", timeout=self.timeout)
        if resp.get("type") != "CommandExecutedSuccessfully":
            raise GamaEnvError(f"ask set_dqn_action failed: {resp}")

    async def step_cycles(self, n):
        """Run n cycles in short synchronous batches and check each response."""
        remaining = int(n)
        if remaining < 0:
            raise ValueError(f"Cycle count must be non-negative: {n}")
        while remaining:
            chunk = min(100, remaining)
            resp = await self.client.step_awaitable(
                self.exp_id, chunk, sync=True, timeout=self.timeout)
            if resp.get("type") != "CommandExecutedSuccessfully":
                raise GamaEnvError(f"GAMA step failed: {resp}")
            remaining -= chunk

    async def get_next_decision_in(self):
        return int(float(await self._exec_expression("next_decision_in_cycles")))

    def reward_from_state(self, state):
        delay_sq = state["delay_sq"]
        if self.max_delay_sq is not None and self.max_delay_sq > 0:
            norm = self.max_delay_sq
        else:
            self._worst_delay_sq = max(self._worst_delay_sq, delay_sq)
            norm = self._worst_delay_sq
        return 0.0 if norm == 0.0 else max(0.0, min(1.0, 1.0 - delay_sq / norm))

    def transition_reward(self, previous, current):
        if self.reward_mode == "queue_time":
            return -(current["queue_time_integral"] - previous["queue_time_integral"]) / 50.0
        return self.reward_from_state(current)

    # -------------------------------------------------------------- gym API
    async def reset(self, seed=None, parameters=None):
        """Load the first seeded episode, then reload for later episodes.

        Luu y: tham so dac biet "seed" cua gama-server reload bi bo qua
        (cac episode trung lap) -> phai truyen qua tham so thuong "rng_seed"
        (model se gan seed <- rng_seed trong init, truoc khi sinh xe).
        """
        params = list(parameters or [])
        self._server_messages.clear()
        if seed is not None:
            params.append({"type": "float", "value": str(float(int(seed))),
                           "name": "rng_seed"})
        if self.exp_id is None:
            await self.load_experiment(parameters=params)
        else:
            try:
                await self.pause()
                await asyncio.sleep(0.2)
                resp = await self.client.reload_awaitable(
                    self.exp_id, parameters=params, timeout=self.timeout)
                if resp.get("type") != "CommandExecutedSuccessfully":
                    raise GamaEnvError(f"Loi reload experiment (seed={seed}): {resp}")
                await self.pause()
            except Exception as reload_err:
                # Neu reload that bai hoac session bi mat ("Unable to find the experiment or simulation"),
                # ta tu dong load lai mot experiment moi thay vi crash worker.
                if self.verbose:
                    print(f"[GamaEnv][Port {self.port}] Reload khong thanh cong ({reload_err}), dang load lai experiment moi...")
                self.exp_id = None
                await self.load_experiment(parameters=params)
        state = await self.read_state()
        if state["cycle"] != 0:
            raise GamaEnvError(f"Reset did not start at cycle 0: {state['cycle']}")
        return state

    async def step(self, action, horizon=None):
        """
        Thuc hien 1 buong quyet dinh DQN (protocol handshake day du).
        Optional horizon truncates exactly, including during junction clearance.
        A truncated state is not a terminal traffic state. Only decision states
        are valid bootstrap states for this action interface.
        """
        current_state = await self.read_state()
        if action not in range(self.action_count):
            raise GamaEnvError(f"Action khong hop le: {action}")
        if not current_state["dqn_waiting_action"]:
            raise GamaEnvError(
                f"DQN action sent outside a decision tick (cycle={current_state['cycle']})"
            )
        if horizon is not None and horizon <= current_state["cycle"]:
            raise GamaEnvError("Action cannot be applied at or after the horizon")
        if "action_mask" in current_state and not current_state["action_mask"][action]:
            raise GamaEnvError(f"Action {action} violates the phase service constraints")
        await self.set_action(action)
        await self.step_cycles(1)                      # handshake: GAMA ap dung action
        nb = await self.get_next_decision_in()
        if nb <= 0:
            raise GamaEnvError(f"Invalid next decision interval: {nb}")
        count = nb if horizon is None else min(nb, horizon - current_state["cycle"] - 1)
        await self.step_cycles(count)
        next_state = await self.read_state()
        # Yellow may stay active until vehicles already inside the junction clear.
        # Advance to an actual decision tick instead of returning an intermediate state.
        advanced = count + 1
        while not next_state["dqn_waiting_action"] and (horizon is None or next_state["cycle"] < horizon):
            if advanced >= 1200:
                raise GamaEnvError("No DQN decision within 1200 cycles after action")
            more = max(1, int(next_state["next_decision_in_cycles"]))
            more = min(more, 1200 - advanced)
            if horizon is not None:
                more = min(more, horizon - next_state["cycle"])
            await self.step_cycles(more)
            advanced += more
            next_state = await self.read_state()

        # Ducrocq/Farhi: clipped improvement over the worst squared speed
        # delay observed since this environment was created. The first
        # nonzero delay gives 0.
        truncated = horizon is not None and next_state["cycle"] >= horizon
        if truncated and "dtse" not in next_state:
            next_state = await self.read_state(force_dtse=True)
        reward = self.transition_reward(current_state, next_state)
        info = {"next_decision_in_cycles": advanced - 1,
                "elapsed_seconds": advanced * .1, "truncated": truncated,
                "bootstrap_valid": next_state["dqn_waiting_action"]}
        return next_state, reward, truncated, info


# ---------------------------------------------------------------------------
# Featurization: state dict -> DTSE tensor (occupancy, speed, signal).
# ---------------------------------------------------------------------------
STATE_DIM = (3, 8, 20)


def featurize(state):
    return np.asarray(state["dtse"], dtype=np.float32)
