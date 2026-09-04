/**
* Name: intersection_dqn_python
* Description: Deep Q-Learning (DQN) traffic signal controller driven by an EXTERNAL
*   Python agent (PyTorch) through gama-server (WebSocket, JSON protocol).
*
*   Architecture (GAMA + Python/PyTorch):
*     - GAMA (this file, headless server): giu toan bo logic thoi gian & an toan
*       (min_green 10s, max_green 60s, yellow 3s, decision moi 5s) nhu mo hinh
*       Q-Learning tabular de dam bao so sanh cong bang.
*     - Python (dqn_py/): DQN agent nhan state tu GAMA, chon action
*       (0 = EXTEND, 1 = SWITCH) roi gui nguoc ve GAMA.
*
*   Handshake protocol (Python <- -> GAMA), moi diem quyet dinh:
*     1. Python GET  state_pack        (tai cycle co tick, dqn_waiting_action = true)
*     2. Python SET  dqn_action
*     3. Python step(1)                (controller ap dung action)
*     4. Python GET  next_decision_in_cycles
*     5. Python step(next_decision_in_cycles)  -> ve lai dung tick ke tiep
*
*   Counter nguyen (green_cycles / yellow_cycles) duoc dung thay float phase_timer
*   de tick quyet dinh hoan toan deterministic (tranh loi lam tron float cua 0.1s).
*   Timing van tuong duong: tick tai 10s, 15s, ..., 55s; force switch tai 60s.
*/

model intersection_dqn_python

import "../includes/collision_avoidance.gaml"

global {

	// =====================================================
	// TIMING & SAFETY CONSTRAINTS (giong intersection-qlearning.gaml)
	// =====================================================
	// Phase 0: NS-GREEN, Phase 1: NS-YELLOW (3s co dinh)
	// Phase 2: EW-GREEN, Phase 3: EW-YELLOW (3s co dinh)
	float phase_timer <- 0.0;         // chi dung cho hien thi HUD
	int green_cycles <- 0;            // so cycle da troi trong pha xanh hien tai
	int yellow_cycles <- 0;           // so cycle da troi trong pha vang hien tai

	int min_green_cycles <- 100;      // min_green_time 10s / step 0.1s
	int max_green_cycles <- 600;      // max_green_time 60s / step 0.1s
	int yellow_len_cycles <- 30;      // yellow_time 3s / step 0.1s
	int decision_cycles <- 50;        // decision_interval 5s / step 0.1s

	// =====================================================
	// PYTHON DQN AGENT INTERFACE
	// =====================================================
	int dqn_action <- -1;             // Python set truoc handshake: 0=EXTEND, 1=SWITCH
	bool dqn_waiting_action <- false; // true = controller dang cho action tu Python
	int next_decision_in_cycles <- 100; // Python step den tick ke tiep
	int current_action <- 0;          // action cuoi cung da ap dung
	int decision_count <- 0;          // tong so quyet dinh AI da thuc hien
	bool python_controlled <- true;   // false = chay heuristic fallback (demo khong can Python)

	// =====================================================
	// STATE OBSERVATION (dau vao cua DQN)
	// =====================================================
	list<road> ns_incoming_roads <- [];
	list<road> ew_incoming_roads <- [];
	int queue_ns <- 0;      // xe dang cho (speed < 1 km/h) tren duong NS vao
	int queue_ew <- 0;      // xe dang cho tren duong EW vao
	int approach_ns <- 0;   // xe dang di chuyen tren duong NS vao
	int approach_ew <- 0;   // xe dang di chuyen tren duong EW vao
	float rng_seed <- 1093.0; // Seed RNG truyen tu Python (fix: tham so 'seed'
	                          // dac biet cua server reload bi bo qua -> dung tham so thuong)

	init {
		// FIX bug seed: tham so dac biet "seed" truyen qua gama-server reload
		// khong duoc ap dung (tat ca episode trung lap). Truyen seed nhu mot
		// tham so thuong "rng_seed" roi gan vao RNG tai init, truoc khi bat
		// ky xe nao duoc sinh (sinh xe bat dau tu cycle 1).
		seed <- int(rng_seed);
		// Initialization moved to observe_state reflex to avoid nil agent errors in headless mode
	}

	// Goi tu Python qua gama-server: lenh "ask" (agent="world.0", args la JSON string):
	//   {"type":"ask","exp_id":...,"action":"set_dqn_action","agent":"world.0","args":"{\"a\": 1.0}"}
	action set_dqn_action(int a) {
		dqn_action <- a;
	}

	// =====================================================
	// REFLEX 1: Quan sat state moi cycle (den xanh + vang deu quan sat)
	// =====================================================
	reflex observe_state {
		if (empty(ns_incoming_roads) and length(intersection) > 3) {
			ns_incoming_roads <- intersection(1).incoming_outer_roads + intersection(3).incoming_outer_roads;
			ew_incoming_roads <- intersection(0).incoming_outer_roads + intersection(2).incoming_outer_roads;
		}
		queue_ns <- 0;
		queue_ew <- 0;
		approach_ns <- 0;
		approach_ew <- 0;
		loop v over: base_vehicle_species {
			if (v.current_road != nil) {
				road r <- road(v.current_road);
				bool is_ns <- ns_incoming_roads contains r;
				bool is_ew <- ew_incoming_roads contains r;
				if (is_ns or is_ew) {
					if (v.speed < 1.0 #km/#h) {
						if (is_ns) { queue_ns <- queue_ns + 1; } else { queue_ew <- queue_ew + 1; }
					} else {
						if (is_ns) { approach_ns <- approach_ns + 1; } else { approach_ew <- approach_ew + 1; }
					}
				}
			}
		}
	}

	// =====================================================
	// REFLEX 2: DQN CONTROLLER
	// =====================================================
	reflex dqn_controller {
		phase_timer <- phase_timer + step;

		// --- YELLOW PHASES (1, 3): chuyen tiep 3s co dinh, khong AI can thiep ---
		if (global_phase = 1 or global_phase = 3) {
			yellow_cycles <- yellow_cycles + 1;
			if (yellow_cycles >= yellow_len_cycles) {
				yellow_cycles <- 0;
				phase_timer <- 0.0;
				global_phase <- (global_phase + 1) mod 4;
				green_cycles <- 0;
			}
		}
		// --- GREEN PHASES (0, 2): AI DQN ra quyet dinh ---
		else {
			green_cycles <- green_cycles + 1;

			if (dqn_waiting_action) {
				// Handshake cycle: ap dung action Python vua gui
				if (dqn_action >= 0) {
					current_action <- dqn_action;
					decision_count <- decision_count + 1;
					dqn_waiting_action <- false;
					dqn_action <- -1;
					if (current_action = 1) {
						phase_timer <- 0.0;
						yellow_cycles <- 0;
						global_phase <- global_phase + 1; // GREEN -> YELLOW
					}
				}
				// dqn_action chua hop le -> tiep tuc cho (Python se step 1 cycle nua)
			}
			else {
				// Tick dung tren luoi nguyen: 100, 150, 200, ... cycles (10s, 15s, 20s, ...)
				bool tick_now <- (green_cycles >= min_green_cycles) and
				                 ((green_cycles - min_green_cycles) mod decision_cycles = 0);
				bool force_switch <- green_cycles >= max_green_cycles;

				if (tick_now or force_switch) {
					if (force_switch) {
						// An toan: bat buoc doi pha o 60s, khong can hoi AI (nhu Q-learning)
						phase_timer <- 0.0;
						yellow_cycles <- 0;
						global_phase <- global_phase + 1;
						green_cycles <- 0;
					} else if (python_controlled) {
						dqn_waiting_action <- true;   // hoi Python
					} else {
						// Fallback heuristic kieu MaxPressure (demo GUI khong can Python)
						bool want_switch <- false;
						if (global_phase = 0 and queue_ew > queue_ns + 2) { want_switch <- true; }
						if (global_phase = 2 and queue_ns > queue_ew + 2) { want_switch <- true; }
						if (want_switch) {
							phase_timer <- 0.0;
							yellow_cycles <- 0;
							global_phase <- global_phase + 1;
							green_cycles <- 0;
						}
					}
				}
			}
		}
	}

	// =====================================================
	// REFLEX 3: Scheduler - bao Python can step bao nhieu cycle
	// de den dung diem quyet dinh ke tiep
	// =====================================================
	reflex update_schedule {
		if (dqn_waiting_action) {
			next_decision_in_cycles <- 1;   // handshake cycle
		}
		else if (global_phase = 1 or global_phase = 3) {
			// Con lai cua vang + min green cua pha xanh ke tiep (tick dau tai dung 10s)
			int rem_yellow <- max([0, yellow_len_cycles - yellow_cycles]);
			next_decision_in_cycles <- rem_yellow + min_green_cycles;
		}
		else {
			// Pha xanh: tick ke tiep tren luoi 50 cycles, tinh bang so nguyen
			int next_tick;
			if (green_cycles < min_green_cycles) {
				next_tick <- min_green_cycles;
			} else {
				next_tick <- min_green_cycles + decision_cycles * (floor((green_cycles - min_green_cycles) / decision_cycles) + 1);
			}
			if (next_tick < max_green_cycles) {
				next_decision_in_cycles <- next_tick - green_cycles;
			} else {
				// Force switch tai 60s -> vang 30 + min green 100 cycles truoc tick ke tiep
				int rem_green <- max([0, max_green_cycles - green_cycles]);
				next_decision_in_cycles <- rem_green + yellow_len_cycles + min_green_cycles;
			}
		}
	}

	// =====================================================
	// REFLEX 4: PERFORMANCE METRICS (giu nguyen dinh nghia nhu 3 model kia)
	// =====================================================
	reflex update_metrics {
		int queue <- 0;
		float sum_wait <- 0.0;
		float sum_speed <- 0.0;
		int count <- length(base_vehicle_species);

		if (count > 0) {
			loop v over: base_vehicle_species {
				if (v.speed < 1.0 #km/#h) {
					queue <- queue + 1;
				}
				sum_wait <- sum_wait + v.waiting_time;
				sum_speed <- sum_speed + v.speed;
			}
			average_waiting_time <- sum_wait / count;
			max_waiting_time <- max(base_vehicle_species collect each.waiting_time);
			average_speed <- (sum_speed / count) * 3.6;
			current_queue_length <- queue;
		} else {
			average_waiting_time <- 0.0;
			max_waiting_time <- 0.0;
			average_speed <- 0.0;
			current_queue_length <- 0;
		}
	}

	// =====================================================
	// REFLEX 5: Sinh xe NS (giong het 3 model kia -> so sanh cong bang)
	// =====================================================
	reflex spawn_traffic_ns when: every(spawn_rate_NS #cycle) {
		loop start_inter over: [intersection(5), intersection(7)] {
			if (empty(base_vehicle_species at_distance 7.0 #m where (distance_to(each.location, start_inter.location) < 7.0 #m))) {
				create base_vehicle_species number: 1 {
					total_vehicles_created <- total_vehicles_created + 1;
					bool is_car <- flip(0.4);
					if (is_car) {
						vehicle_length <- 4.5 #m;
						num_lanes_occupied <- 2;
						max_speed <- (25 + rnd(15)) #km / #h;
					} else {
						vehicle_length <- 2.5 #m;
						num_lanes_occupied <- 1;
						max_speed <- (20 + rnd(15)) #km / #h;
					}

					location <- start_inter.location;
					intersection target_straight; intersection target_left; intersection target_right;

					if (start_inter = intersection(5)) {
						target_straight <- intersection(7); target_right <- intersection(6); target_left <- intersection(4);
					} else if (start_inter = intersection(7)) {
						target_straight <- intersection(5); target_right <- intersection(4); target_left <- intersection(6);
					}

					intersection chosen_target <- rnd_choice([target_straight :: 0.5, target_left :: 0.25, target_right :: 0.25]);
					target <- chosen_target;
					do compute_path graph: road_network target: target;

					if (chosen_target = target_left) {
						current_lane <- is_car ? 4 : rnd(4, 5);
						color <- #cyan;
					} else if (chosen_target = target_right) {
						current_lane <- is_car ? 0 : rnd(0, 1);
						color <- #magenta;
					} else {
						current_lane <- is_car ? 2 : rnd(2, 3);
						color <- #lime;
					}
				}
			}
		}
	}

	// =====================================================
	// REFLEX 6: Sinh xe EW (giong het 3 model kia -> so sanh cong bang)
	// =====================================================
	reflex spawn_traffic_ew when: every(spawn_rate_EW #cycle) {
		loop start_inter over: [intersection(4), intersection(6)] {
			if (empty(base_vehicle_species at_distance 7.0 #m where (distance_to(each.location, start_inter.location) < 7.0 #m))) {
				create base_vehicle_species number: 1 {
					total_vehicles_created <- total_vehicles_created + 1;
					bool is_car <- flip(0.4);
					if (is_car) {
						vehicle_length <- 4.5 #m;
						num_lanes_occupied <- 2;
						max_speed <- (25 + rnd(15)) #km / #h;
					} else {
						vehicle_length <- 2.5 #m;
						num_lanes_occupied <- 1;
						max_speed <- (20 + rnd(15)) #km / #h;
					}

					location <- start_inter.location;
					intersection target_straight; intersection target_left; intersection target_right;

					if (start_inter = intersection(4)) {
						target_straight <- intersection(6); target_right <- intersection(5); target_left <- intersection(7);
					} else if (start_inter = intersection(6)) {
						target_straight <- intersection(4); target_right <- intersection(7); target_left <- intersection(5);
					}

					intersection chosen_target <- rnd_choice([target_straight :: 0.5, target_left :: 0.25, target_right :: 0.25]);
					target <- chosen_target;
					do compute_path graph: road_network target: target;

					if (chosen_target = target_left) {
						current_lane <- is_car ? 4 : rnd(4, 5);
						color <- #cyan;
					} else if (chosen_target = target_right) {
						current_lane <- is_car ? 0 : rnd(0, 1);
						color <- #magenta;
					} else {
						current_lane <- is_car ? 2 : rnd(2, 3);
						color <- #lime;
					}
				}
			}
		}
	}
}

// Experiment chinh cho Python/gama-server.
// LUU Y: phai la type: gui (GAMA 2025 chi chap nhan [test, batch, gui]) nhung
// KHONG co output/display nao -> gama-server khong tao display surface (SWT),
// tranh bi block main thread khi chay headless. Khong nhin thay nhung chay duoc.
experiment dqn_server_experiment type: gui {
	parameter "Python Controlled" var: python_controlled init: true;
	parameter "Seed" var: seed init: 1093.0;
	// Seed RNG thuc su (truyen tu Python qua reload; tham so "Seed" dac biet
	// ben tren khong duoc server ap dung -> xem init cua global)
	parameter "DQN_RNG_Seed" var: rng_seed init: 1093.0;
}

experiment dqn_gui_server_experiment type: gui {
	parameter "Python Controlled" var: python_controlled init: true;
	parameter "Seed" var: seed init: 1093.0;
	float minimum_cycle_duration <- 0.05#s; // toc do xem x2 (0.05s/cycle)
	output {
		display intersection_view background: #black {
			species road aspect: base;
			species base_vehicle_species aspect: base;
			species intersection aspect: base;
			graphics "HUD" {
				draw "DQN CONTROLLER (Python via IDE Server)" at: {20, 15} color: #lightgreen font: font("Helvetica", 13, #bold);
				draw "Phase: " + phase_names[global_phase] + " | Green: " + green_cycles + "c" at: {20, 35} color: (global_phase = 0 or global_phase = 2 ? #lime : (global_phase = 1 or global_phase = 3 ? #yellow : #red)) font: font("Helvetica", 14, #bold);
				draw "Last action: " + (current_action = 0 ? "EXTEND (0)" : "SWITCH (1)") + " | Next decision in: " + next_decision_in_cycles + "c" at: {20, 55} color: #orange font: font("Helvetica", 12, #plain);
				draw "Queue NS: " + queue_ns + " | EW: " + queue_ew at: {20, 75} color: #orange font: font("Helvetica", 12, #plain);
				draw "Passed: " + total_vehicles_passed + " | Active: " + length(base_vehicle_species) + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s" at: {20, 95} color: #white font: font("Helvetica", 12, #plain);
			}
		}
	}
}

// Ban GUI de xem truc quan trong GAMA IDE (khong dung voi Python).
// Khi chay khong co Python: dat "Python Controlled" = false -> dung heuristic fallback.
experiment dqn_gui_preview type: gui {
	parameter "Python Controlled" var: python_controlled init: false;
	float minimum_cycle_duration <- 0.05#s; // toc do xem x2 (0.05s/cycle)
	output {
		display intersection_view background: #black {
			species road aspect: base;
			species base_vehicle_species aspect: base;
			species intersection aspect: base;
			graphics "HUD" {
				draw "DQN CONTROLLER (Python/PyTorch via gama-server)" at: {20, 15} color: #lightgreen font: font("Helvetica", 13, #bold);
				draw "Mode: " + (python_controlled ? "Python DQN (chay qua gama-server)" : "Heuristic fallback") + " | Waiting: " + dqn_waiting_action at: {20, 35} color: #lightgreen font: font("Helvetica", 12, #plain);
				draw "Phase: " + phase_names[global_phase] + " | Green: " + green_cycles + "c / " + max_green_cycles + "c" at: {20, 55} color: (global_phase = 0 or global_phase = 2 ? #lime : (global_phase = 1 or global_phase = 3 ? #yellow : #red)) font: font("Helvetica", 14, #bold);
				draw "Last action: " + (current_action = 0 ? "EXTEND (0)" : "SWITCH (1)") + " | Decisions: " + decision_count + " | Next decision in: " + next_decision_in_cycles + "c" at: {20, 75} color: #orange font: font("Helvetica", 12, #plain);
				draw "Queue NS: " + queue_ns + " | EW: " + queue_ew + " | Approach NS: " + approach_ns + " | EW: " + approach_ew at: {20, 95} color: #orange font: font("Helvetica", 12, #plain);
				draw "Passed: " + total_vehicles_passed + " | Active: " + length(base_vehicle_species) + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s" at: {20, 115} color: #white font: font("Helvetica", 12, #plain);
			}
		}
		display performance_charts {
			chart "Performance Metrics (DQN-Python)" type: series {
				data "Queue Length" value: current_queue_length color: #crimson;
				data "Avg Waiting Time (s)" value: average_waiting_time color: #darkorange;
				data "Avg Speed (km/h)" value: average_speed color: #dodgerblue;
			}
		}
	}
}