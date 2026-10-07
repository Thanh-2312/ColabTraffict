#!/usr/bin/env python3
"""
==============================================================================
GAMA TRAFFIC ENV - Moi truong giao thong dang Gym cho DQN agent (PyTorch)
==============================================================================
Giao tiep voi gama-server qua thu vien chinh thuc `gama-client` (WebSocket).

CHU Y: gama-client 2.x yeu cau event loop dang chay khi tao client va khi goi
lenh -> moi method o day la ASYNC, dung ben trong `asyncio.run(main())`:

    Python                                    GAMA (intersection-dqn-python.gaml)
    ------                                    -----------------------------------
    await load_awaitable(...)     ->  exp_id
    await expression_awaitable(GET state) -> state_pack (18 truong, cach '|')
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

from gama_client.sync_client import GamaSyncClient

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

# Tham so chuan hoa state (phai khop voi mo hinh GAML)
QUEUE_NORM = 20.0          # queue/20 -> [0,1]
MAX_GREEN_CYCLES = 600     # 60s
MIN_GREEN_CYCLES = 100     # 10s


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
                 w_queue=1.0, w_wait=0.0, verbose=True, timeout=600.0):
        self.host = host
        self.port = int(port)
        self.model_path = model_path or DEFAULT_MODEL
        self.experiment = experiment
        self.w_queue = float(w_queue)
        self.w_wait = float(w_wait)
        self.verbose = verbose
        self.timeout = float(timeout)
        self.exp_id = None
        self.client = None
        self._server_messages = []

    # --------------------------------------------------------- server events
    async def _on_server_message(self, message):
        """Nhan cac message khong phai answer lenh (console, status, error...)."""
        self._server_messages.append(message)
        mtype = message.get("type", "") if isinstance(message, dict) else ""
        if mtype in ("SimulationError", "RuntimeError", "GamaServerError",
                     "SimulationErrorDialog"):
            print(f"[GamaEnv][SERVER-{mtype}] {message}")

    # ------------------------------------------------------------ lifecycle
    async def setup(self):
        """Connect to gama-server; first reset loads the seeded experiment."""
        self.client = GamaSyncClient(
            self.host, self.port,
            other_message_handler=self._on_server_message,
            default_timeout=self.timeout,
        )
        await self.client.connect_awaitable()
        if self.verbose:
            print(f"[GamaEnv] Da ket noi ws://{self.host}:{self.port}")
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
                self.client.close_connection()
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
    async def read_state(self):
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
        return state

    async def set_action(self, action):
        """Gui action (0=EXTEND, 1=SWITCH) vao GAMA qua lenh 'ask'.

        QUAN TRONG:
          - agent phai la dang tham chieu '<ten>.0' (world agent index 0) vi
            `AgentReference` ben server split theo dau cham; neu khong co duoi
            `.0` thi loi AIOOBE lam server khong tra loi (timeout).
          - args phai la mot JSON STRING (server lam `Json.parse((String) args)`);
            neu gui dict -> ClassCastException -> timeout.
        """
        if action not in (0, 1) and action != -1:
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
            chunk = min(10, remaining)
            resp = await self.client.step_awaitable(
                self.exp_id, chunk, sync=True, timeout=self.timeout)
            if resp.get("type") != "CommandExecutedSuccessfully":
                raise GamaEnvError(f"GAMA step failed: {resp}")
            remaining -= chunk

    async def get_next_decision_in(self):
        return int(float(await self._exec_expression("next_decision_in_cycles")))

    # -------------------------------------------------------------- gym API
    async def reset(self, seed=None, parameters=None):
        """Load the first seeded episode, then reload for later episodes.

        Luu y: tham so dac biet "seed" cua gama-server reload bi bo qua
        (cac episode trung lap) -> phai truyen qua tham so thuong "rng_seed"
        (model se gan seed <- rng_seed trong init, truoc khi sinh xe).
        """
        params = list(parameters or [])
        if seed is not None:
            params.append({"type": "float", "value": str(float(int(seed))),
                           "name": "rng_seed"})
        if self.exp_id is None:
            await self.load_experiment(parameters=params)
        else:
            await self.pause()
            await asyncio.sleep(0.2)
            resp = await self.client.reload_awaitable(
                self.exp_id, parameters=params, timeout=self.timeout)
            if resp.get("type") != "CommandExecutedSuccessfully":
                raise GamaEnvError(f"Loi reload experiment (seed={seed}): {resp}")
            await self.pause()
        state = await self.read_state()
        if state["cycle"] != 0:
            raise GamaEnvError(f"Reset did not start at cycle 0: {state['cycle']}")
        return state

    async def step(self, action):
        """
        Thuc hien 1 buong quyet dinh DQN (protocol handshake day du).
        Tra ve (next_state, reward, done=False, info).
        Horizon episode do train.py/evaluate.py tu quan ly qua state['cycle'].
        """
        current_state = await self.read_state()
        if not current_state["dqn_waiting_action"]:
            raise GamaEnvError(
                f"DQN action sent outside a decision tick (cycle={current_state['cycle']})"
            )
        await self.set_action(action)
        await self.step_cycles(1)                      # handshake: GAMA ap dung action
        nb = await self.get_next_decision_in()
        if nb <= 0:
            raise GamaEnvError(f"Invalid next decision interval: {nb}")
        await self.step_cycles(nb)                     # chay den tick quyet dinh ke tiep
        next_state = await self.read_state()
        # Yellow may stay active until vehicles already inside the junction clear.
        # Advance to an actual decision tick instead of returning an intermediate state.
        advanced = nb + 1
        while not next_state["dqn_waiting_action"]:
            if advanced >= 1200:
                raise GamaEnvError("No DQN decision within 1200 cycles after action")
            more = max(1, int(next_state["next_decision_in_cycles"]))
            more = min(more, 1200 - advanced)
            await self.step_cycles(more)
            advanced += more
            next_state = await self.read_state()

        # Reward giong Q-learning tabular: -tong queue; co the them trong so wait
        reward = -(self.w_queue * next_state["current_queue_length"]
                   + self.w_wait * next_state["average_waiting_time"])
        info = {"next_decision_in_cycles": advanced - 1}
        return next_state, reward, False, info


# ---------------------------------------------------------------------------
# Featurization: state dict (GAMA) -> vector float32 cho mang neural
# 8 chieu, chuan hoa ve [0,1]:
#   [queue_ns/20, queue_ew/20, approach_ns/20, approach_ew/20,
#    green_cycles/600, min_green_ok, phase_is_NS, phase_is_EW]
# ---------------------------------------------------------------------------
STATE_DIM = 8


def featurize(state):
    import numpy as np
    return np.asarray([
        min(1.0, state["queue_ns"] / QUEUE_NORM),
        min(1.0, state["queue_ew"] / QUEUE_NORM),
        min(1.0, state["approach_ns"] / QUEUE_NORM),
        min(1.0, state["approach_ew"] / QUEUE_NORM),
        min(1.0, state["green_cycles"] / MAX_GREEN_CYCLES),
        1.0 if state["green_cycles"] >= MIN_GREEN_CYCLES else 0.0,
        1.0 if state["global_phase"] == 0 else 0.0,
        1.0 if state["global_phase"] == 4 else 0.0,
    ], dtype="float32")
