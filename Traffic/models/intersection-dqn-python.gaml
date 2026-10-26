/**
* Name: intersection_dqn_python
* Description: Four-phase 3DQN traffic signal controller driven by Python.
*   DTSE is captured at decision ticks; action 0/1/2/3 selects NS through,
*   NS left, EW through or EW left. Repeating a phase extends it for 10 s.
*   A change uses 3 s yellow, at least 2 s all red until clear, then 10 s green.
*
*   Handshake protocol (Python <- -> GAMA), moi diem quyet dinh:
*     1. Python GET state_pack and capture_dtse (at a decision tick)
*     2. Python SET  dqn_action
*     3. Python step(1)                (controller ap dung action)
*     4. Python GET  next_decision_in_cycles
*     5. Python step(next_decision_in_cycles)  -> ve lai dung tick ke tiep
*
*   Integer cycle counters keep the 0.1 s schedule deterministic.
*/

model intersection_dqn_python

import "../includes/collision_avoidance.gaml"

global {

	// =====================================================
	// TIMING & SAFETY CONSTRAINTS
	// =====================================================
	// 0/4: through green, 1/5: through yellow,
	// 2/6: protected left green, 3/7: left yellow.
	int green_cycles <- 0;            // so cycle da troi trong pha xanh hien tai
	int yellow_cycles <- 0;           // so cycle da troi trong pha vang hien tai
	int min_green_cycles <- 100;      // 10 s / 0.1 s
	int yellow_len_cycles <- 30;      // 3 s / 0.1 s

	// =====================================================
	// PYTHON DQN AGENT INTERFACE
	// =====================================================
	int dqn_action <- -1;             // 0=NS through, 1=NS left, 2=EW through, 3=EW left
	bool dqn_waiting_action <- false; // true = controller dang cho action tu Python
	int next_decision_in_cycles <- 100; // Python step den tick ke tiep
	int current_action <- 0;          // action cuoi cung da ap dung
	int decision_count <- 0;          // tong so quyet dinh AI da thuc hien
	bool python_controlled <- true;   // false = chay heuristic fallback (demo khong can Python)
	int pending_green_phase <- 0;
	int all_red_cycles <- 0;
	bool dqn_all_red <- false;
	string dtse_pack <- "";
	float dtse_delay_sq <- 0.0;
	float dtse_delay_sq_near <- 0.0;
	bool dqn_service_guard <- false; // Set to false to match paper's pure 4-phase 3DQN without heuristic phase forcing
	list<int> dqn_action_mask <- [1,1,1,1];
		list<int> phase_wait_cycles <- [0,0,0,0];
		list<int> phase_demand <- [0,0,0,0];
		int max_phase_wait_cycles <- 1200;
		int max_green_cycles <- 600;

	// Called only at decision ticks through gama-server. Shape: [3,8,20].
		// Rows E,N,W,S x (through,left); cells aggregate movement groups.
		// Mean speed makes the grouped observation independent of vehicle order.
	action capture_dtse {
		list<float> cells <- [];
			list<int> hits <- [];
		loop i from: 0 to: 479 { cells <- cells + 0.0; }
			loop i from: 0 to: 159 { hits <- hits + 0; }
		dtse_delay_sq <- 0.0;
		dtse_delay_sq_near <- 0.0;
		loop v over: active_vehicles {
			if (v.current_road != nil and v.uses_signal and v.approach_id >= 4 and v.approach_id <= 7 and
				road(v.current_road).is_outer_road and road(v.current_road).is_incoming) {
				float speed_fraction <- min([1.0, max([0.0, v.speed / (50.0 #km/#h)])]);
				float vehicle_delay_sq <- 1.0 - speed_fraction * speed_fraction;
				// Reward covers every incoming signal vehicle, as in the SUMO reference.
				dtse_delay_sq <- dtse_delay_sq + vehicle_delay_sq;
				float distance_from_stop <- distance_to(v.location, intersection_center) - distance_to_intersection_center;
				if (distance_from_stop >= 0.0 #m and distance_from_stop < 160.0 #m) {
					int row <- (v.approach_id - 4) * 2 + (v.maneuver = "left" ? 1 : 0);
					int col <- int(distance_from_stop / (8.0 #m));
					int index <- row * 20 + col;
					cells[index] <- 1.0;
						hits[index] <- hits[index] + 1;
						cells[160 + index] <- cells[160 + index] + speed_fraction;
					dtse_delay_sq_near <- dtse_delay_sq_near + vehicle_delay_sq;
				}
			}
		}
		// Average each cell once after accumulating every vehicle. Doing this
		// inside the vehicle loop makes the result depend on vehicle order/count.
		loop i from: 0 to: 159 {
			if (hits[i] > 0) { cells[160 + i] <- cells[160 + i] / hits[i]; }
		}
		loop row from: 0 to: 7 {
			int approach <- 4 + floor(row / 2);
			int served_phase <- (approach = 5 or approach = 7) ? (row mod 2 = 1 ? 2 : 0) :
				(row mod 2 = 1 ? 6 : 4);
			if (global_phase = served_phase and !dqn_all_red) {
				loop col from: 0 to: 19 { cells[320 + row * 20 + col] <- 1.0; }
			}
		}
		dtse_pack <- "" + cells;
	}

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
			phase_demand <- [0,0,0,0];
		if (empty(ns_incoming_roads) and length(intersection) > 3) {
			ns_incoming_roads <- controller_roads(true,true);
			ew_incoming_roads <- controller_roads(false,true);
		}
		queue_ns <- 0;
		queue_ew <- 0;
		approach_ns <- 0;
		approach_ew <- 0;
		loop v over: active_vehicles {
			if (v.current_road != nil and v.uses_signal and distance_to(v.location,intersection_center) <= detector_distance) {
				road r <- road(v.current_road);
				bool is_ns <- ns_incoming_roads contains r;
				bool is_ew <- ew_incoming_roads contains r;
				if (is_ns or is_ew) {
					int movement <- (is_ns ? 0 : 2) + (v.maneuver = "left" ? 1 : 0);
					phase_demand[movement] <- phase_demand[movement] + 1;
					if (v.speed < 1.0 #km/#h) {
						if (is_ns) { queue_ns <- queue_ns + 1; } else { queue_ew <- queue_ew + 1; }
					} else {
						if (is_ns) { approach_ns <- approach_ns + 1; } else { approach_ew <- approach_ew + 1; }
					}
				}
			}
		}
		// Expose restrictions before action selection; Python uses the same
		// mask for exploration and Bellman bootstrap, so no action is relabelled.
		dqn_action_mask <- [1,1,1,1];
		int oldest <- -1;
		loop a from: 0 to: 3 {
			if (phase_demand[a] = 0 or (global_phase = a * 2 and !dqn_all_red)) {
				phase_wait_cycles[a] <- 0;
			} else { phase_wait_cycles[a] <- phase_wait_cycles[a] + 1; }
			if (phase_wait_cycles[a] >= max_phase_wait_cycles and
				(oldest < 0 or phase_wait_cycles[a] > phase_wait_cycles[oldest])) { oldest <- a; }
		}
		if (dqn_service_guard) {
			if (oldest >= 0) {
				dqn_action_mask <- [0,0,0,0]; dqn_action_mask[oldest] <- 1;
			} else if (global_phase mod 2 = 0 and green_cycles >= max_green_cycles - 1) {
				int current <- int(global_phase / 2);
				if (sum(phase_demand) > phase_demand[current]) { dqn_action_mask[current] <- 0; }
			}
		}
	}

	// =====================================================
	// REFLEX 2: DQN CONTROLLER
	// =====================================================
	reflex dqn_controller {
		phase_timer <- phase_timer + step;
		if (dqn_all_red) {
			all_red_cycles <- all_red_cycles + 1;
			// Paper specifies clearance Tr = 2s (20 cycles). Cap at 25 cycles (2.5s) to prevent red gridlock.
			if (all_red_cycles >= 20 and (signal_junction_clear() or all_red_cycles >= 25)) {
				dqn_all_red <- false;
				all_red_cycles <- 0;
				global_phase <- pending_green_phase;
				green_cycles <- 0;
				phase_timer <- 0.0;
			}
		} else if (global_phase mod 2 = 1) {
			yellow_cycles <- yellow_cycles + 1;
			if (yellow_cycles >= yellow_len_cycles) {
				yellow_cycles <- 0;
				dqn_all_red <- true;
				// Keep the yellow phase index; elapsed time makes all shared GAMA
				// signal and vehicle rules show red during clearance.
				phase_timer <- signal_yellow_seconds;
			}
		} else {
			green_cycles <- green_cycles + 1;
			if (dqn_waiting_action and dqn_action >= 0) {
				current_action <- dqn_action;
				decision_count <- decision_count + 1;
				dqn_waiting_action <- false;
				dqn_action <- -1;
				pending_green_phase <- current_action * 2;
				if (pending_green_phase != global_phase) {
					global_phase <- global_phase + 1; // current green -> its yellow
					yellow_cycles <- 0;
					phase_timer <- 0.0;
				}
			} else if (!dqn_waiting_action and green_cycles >= min_green_cycles and
				green_cycles mod min_green_cycles = 0) {
				if (python_controlled) {
					dqn_waiting_action <- true;
				} else {
						// Preview serves all four movements and obeys the service guard.
						int selected <- -1;
						float best_score <- -1.0;
						loop a from: 0 to: 3 {
							float score <- phase_demand[a] + phase_wait_cycles[a] / 100.0;
							if (dqn_action_mask[a] = 1 and score > best_score) {
								selected <- a; best_score <- score;
							}
						}
						pending_green_phase <- selected * 2;
					current_action <- int(pending_green_phase / 2);
					if (pending_green_phase != global_phase) {
						global_phase <- global_phase + 1;
						yellow_cycles <- 0;
						phase_timer <- 0.0;
					}
				}
			}
		}
		if (dqn_all_red) {
			signal_display_seconds <- int(max([0, 20 - all_red_cycles]) * step / (1 #s) + 0.999);
		} else if (global_phase mod 2 = 1) {
			signal_display_seconds <- int((yellow_len_cycles - yellow_cycles) * step / (1 #s) + 0.999);
		} else {
			signal_display_seconds <- int(max([0, min_green_cycles - (green_cycles mod min_green_cycles)]) * step / (1 #s) + 0.999);
		}
		signal_countdown <- "" + signal_display_seconds + "s";
	}

	// =====================================================
	// REFLEX 3: Scheduler - bao Python can step bao nhieu cycle
	// de den dung diem quyet dinh ke tiep
	// =====================================================
	reflex update_schedule {
		if (dqn_waiting_action) {
			next_decision_in_cycles <- 1;
		} else if (dqn_all_red) {
			next_decision_in_cycles <- all_red_cycles >= 20 ? 1 :
				20 - all_red_cycles + min_green_cycles;
		} else if (global_phase mod 2 = 1) {
			next_decision_in_cycles <- yellow_len_cycles - yellow_cycles + 20 + min_green_cycles;
		} else {
			next_decision_in_cycles <- min_green_cycles - green_cycles mod min_green_cycles;
		}
	}

}

// Experiment chinh cho Python/gama-server.
experiment dqn_server_experiment type: gui autorun: false {
	parameter "Phase service guard" var: dqn_service_guard;
	parameter "Demand CSV" var: demand_file_path;
	parameter "Python Controlled" var: python_controlled init: true;
	parameter "Seed" var: seed init: 1093.0;
	parameter "DQN_RNG_Seed" var: rng_seed init: 1093.0;
}

experiment dqn_gui_server_experiment type: gui {
	parameter "Xe cầu vượt và hầm" var: enable_bypass_traffic;
	parameter "Xem mặt cắt hầm" var: show_tunnel_cutaway;
	// Opening this experiment manually must remain live without a Python
	// client. External training/evaluation uses dqn_server_experiment above.
	parameter "Python Controlled" var: python_controlled init: false;
	parameter "Seed" var: seed init: 1093.0;
	float minimum_cycle_duration <- 0.033#s; // About 3 model seconds per wall second (step = 0.1 s)
	output synchronized: true {
		monitor "Xe hoàn thành mặt đất" value: total_vehicles_passed;
		monitor "Xe hoàn thành cầu vượt/hầm" value: bypass_vehicles_passed;
		monitor "Hàng đợi mặt đất" value: current_queue_length;
		monitor "Pha đèn" value: phase_names[global_phase];
		monitor "Đếm ngược pha" value: signal_countdown;
		monitor "Chờ trung bình (s)" value: average_waiting_time;
		display doan_3d type: opengl background: rgb(8,12,22) {
			camera 'default' location: {820,1210,220} target: {1000,1000,16};
			species doan_ground aspect: base;
			species bridge_pillar;
			species metro_pillar;
			species tunnel_structure;
			species flyover_structure;
			species metro_structure;
			species traffic_signal_post aspect: doan_3d;
			species base_vehicle_species aspect: doan_3d;
			species doan_metro aspect: base;
		}

		display intersection_view background: rgb(18, 22, 28) {
			species doan_ground aspect: base;
			species road aspect: base;
			species traffic_signal_post aspect: base;
			species conflict_zone aspect: base;
			species base_vehicle_species aspect: base;
			graphics "HUD" {
				rgb phase_c <- dqn_all_red ? #red : (global_phase mod 2 = 0 ? #lime : #yellow);
				draw rectangle(310, 115) at: {165, 62} color: rgb(15, 23, 42, 215) border: rgb(71, 85, 105);
				draw "TRAFFIC-LIGHT ABM | DQN PYTORCH" at: {20, 22} color: #lime font: font("Helvetica", 13, #bold);
				draw circle(4.5) at: {26, 42} color: phase_c;
				draw "Phase: " + phase_names[global_phase] + " | Green: " + green_cycles + "c" at: {38, 45} color: phase_c font: font("Helvetica", 14, #bold);
				draw "Selected phase: " + current_action + " | Next in: " + next_decision_in_cycles + "c" at: {20, 68} color: #orange font: font("Helvetica", 12, #plain);
				draw "Queue NS: " + queue_ns + " | EW: " + queue_ew at: {20, 88} color: rgb(56, 189, 248) font: font("Helvetica", 12, #plain);
				draw "Passed: " + total_vehicles_passed + " xe | Queue: " + current_queue_length + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s" at: {20, 108} color: rgb(226, 232, 240) font: font("Helvetica", 12, #plain);
			}
		}
	}
}

experiment dqn_gui_preview type: gui {
	parameter "Xe cầu vượt và hầm" var: enable_bypass_traffic;
	parameter "Xem mặt cắt hầm" var: show_tunnel_cutaway;
	parameter "Python Controlled" var: python_controlled init: false;
	float minimum_cycle_duration <- 0.033#s; // About 3 model seconds per wall second (step = 0.1 s)
	output synchronized: true {
		monitor "Xe hoàn thành mặt đất" value: total_vehicles_passed;
		monitor "Xe hoàn thành cầu vượt/hầm" value: bypass_vehicles_passed;
		monitor "Hàng đợi mặt đất" value: current_queue_length;
		monitor "Pha đèn" value: phase_names[global_phase];
		monitor "Đếm ngược pha" value: signal_countdown;
		monitor "Chờ trung bình (s)" value: average_waiting_time;
		display doan_3d type: opengl background: rgb(8,12,22) {
			camera 'default' location: {820,1210,220} target: {1000,1000,16};
			species doan_ground aspect: base;
			species bridge_pillar;
			species metro_pillar;
			species tunnel_structure;
			species flyover_structure;
			species metro_structure;
			species traffic_signal_post aspect: doan_3d;
			species base_vehicle_species aspect: doan_3d;
			species doan_metro aspect: base;
		}

		display intersection_view background: rgb(18, 22, 28) {
			species doan_ground aspect: base;
			species road aspect: base;
			species traffic_signal_post aspect: base;
			species conflict_zone aspect: base;
			species base_vehicle_species aspect: base;
			graphics "HUD" {
				rgb phase_c <- dqn_all_red ? #red : (global_phase mod 2 = 0 ? #lime : #yellow);
				draw rectangle(310, 125) at: {165, 68} color: rgb(15, 23, 42, 215) border: rgb(71, 85, 105);
				draw "TRAFFIC-LIGHT ABM | DQN PYTORCH" at: {20, 22} color: #lime font: font("Helvetica", 13, #bold);
				draw circle(4.5) at: {26, 42} color: phase_c;
				draw "Phase: " + phase_names[global_phase] + " | Green: " + green_cycles + "c" at: {38, 45} color: phase_c font: font("Helvetica", 14, #bold);
				draw "Selected phase: " + current_action + " | Dec: " + decision_count at: {20, 68} color: #orange font: font("Helvetica", 12, #plain);
				draw "Passed: " + total_vehicles_passed + " xe | Queue: " + current_queue_length + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s" at: {20, 88} color: rgb(226, 232, 240) font: font("Helvetica", 12, #plain);
				draw "TIT: " + (round(total_tit_sum*10.0)/10.0) + "s | TTC<1s: " + severe_conflicts_count + " | HardBrakes: " + hard_braking_count + " | PET: " + (round(min_pet_observed*10.0)/10.0) + "s" at: {20, 108} color: rgb(248, 113, 113) font: font("Helvetica", 11, #plain);
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
