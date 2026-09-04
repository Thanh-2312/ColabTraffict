/**
* Name: intersection_qlearning
* Description: Q-Learning reinforcement learning traffic signal controller.
*/

model intersection_qlearning

import "../includes/collision_avoidance.gaml"

global {
	// =====================================================
	// Q-LEARNING REINFORCEMENT LEARNING CONTROLLER
	// =====================================================
	// Phase 0: NS-GREEN, Phase 1: NS-YELLOW (3s fixed)
	// Phase 2: EW-GREEN, Phase 3: EW-YELLOW (3s fixed)
	float phase_timer <- 0.0;
	
	// Timing & Safety constraints
	float min_green_time <- 10#s;   // Thời gian xanh tối thiểu (tránh đổi liên tục)
	float max_green_time <- 60#s;   // Thời gian xanh tối đa (tránh starvation)
	float yellow_time <- 3#s;       // Thời gian đèn vàng an toàn
	float decision_interval <- 5#s; // AI quyết định mỗi 5 giây
	
	// Q-Learning Hyperparameters
	float alpha_lr <- 0.1;          // Tốc độ học (Learning rate)
	float gamma_discount <- 0.9;    // Hệ số chiết khấu (Discount factor)
	float epsilon <- 0.5;           // Xác suất khám phá (Exploration rate)
	float epsilon_decay <- 0.995;   // Giảm dần khám phá
	float epsilon_min <- 0.05;      // Mức khám phá tối thiểu
	
	// Q-Table: Map[State, [Q(Extend), Q(Switch)]]
	map<string, list<float>> q_table <- [];
	string prev_state <- "";
	int prev_action <- -1;
	int current_action <- 0;
	float last_reward <- 0.0;
	int q_updates_count <- 0;
	
	// Road collections for queue observation
	list<road> ns_incoming_roads <- [];
	list<road> ew_incoming_roads <- [];
	int queue_ns <- 0;
	int queue_ew <- 0;

	init {
		// FIX (headless): khong build danh sach duong o day vi intersection = nil
		// khi init cua model chay (mang duong tao trong init cua include) ->
		// danh sach rong -> queue_ns/queue_ew luon = 0 -> khong gian state suy bien
		// (chi hoc trong 1-2 state thay vi 18). Khoi tao muon nhu model DQN.

		// Khởi tạo Q-Table với các giá trị mặc định cho 18 states (2 pha xanh x 3 NS x 3 EW)
		loop p over: [0, 2] {
			loop n_lvl over: [0, 1, 2] {
				loop e_lvl over: [0, 1, 2] {
					string st <- "" + p + "_" + n_lvl + "_" + e_lvl;
					q_table[st] <- [0.0, 0.0];
				}
			}
		}
	}

	// Khoi tao muon danh sach duong vao khi mang duong da san sang
	reflex init_road_lists when: (empty(ns_incoming_roads) and length(intersection) > 3) {
		ns_incoming_roads <- intersection(1).incoming_outer_roads + intersection(3).incoming_outer_roads;
		ew_incoming_roads <- intersection(0).incoming_outer_roads + intersection(2).incoming_outer_roads;
	}
	
	// =====================================================
	// Q-LEARNING CONTROLLER REFLEX
	// =====================================================
	reflex qlearning_controller {
		phase_timer <- phase_timer + step;
		
		// --- YELLOW PHASES (1, 3): Chuyển tiếp 3s cố định đảm bảo an toàn ---
		if (global_phase = 1 or global_phase = 3) {
			if (phase_timer >= yellow_time) {
				phase_timer <- 0.0;
				global_phase <- (global_phase + 1) mod 4;
			}
		} 
		// --- GREEN PHASES (0, 2): AI Q-Learning ra quyết định ---
		else {
			bool check_now <- (phase_timer >= min_green_time) and 
			                  (round(phase_timer * 10) mod int(decision_interval * 10) = 0);
			bool force_switch <- phase_timer >= max_green_time;
			
			if (check_now or force_switch) {
				// 1. Quan sát trạng thái môi trường
				queue_ns <- 0;
				queue_ew <- 0;
				loop v over: base_vehicle_species {
					if (v.current_road != nil and v.speed < 1.0 #km/#h) {
						road r <- road(v.current_road);
						if (ns_incoming_roads contains r) {
							queue_ns <- queue_ns + 1;
						} else if (ew_incoming_roads contains r) {
							queue_ew <- queue_ew + 1;
						}
					}
				}
				
				int ns_lvl <- 0;
				if (queue_ns >= 15) { ns_lvl <- 2; }
				else if (queue_ns >= 5) { ns_lvl <- 1; }
				
				int ew_lvl <- 0;
				if (queue_ew >= 15) { ew_lvl <- 2; }
				else if (queue_ew >= 5) { ew_lvl <- 1; }
				
				string curr_state <- "" + global_phase + "_" + ns_lvl + "_" + ew_lvl;
				
				if not (q_table contains_key curr_state) {
					q_table[curr_state] <- [0.0, 0.0];
				}
				
				// 2. Tính Reward từ bước trước & Cập nhật Q-Table (Bellman Equation)
				if (prev_state != "" and prev_action >= 0) {
					// Reward âm tỷ lệ thuận với hàng đợi (khuyến khích giải tỏa nhanh)
					float reward <- - float(current_queue_length);
					last_reward <- reward;
					
					list<float> curr_q <- q_table[curr_state];
					float max_next_q <- max(curr_q);
					
					list<float> prev_q <- q_table[prev_state];
					float old_val <- prev_q[prev_action];
					float new_val <- (1.0 - alpha_lr) * old_val + alpha_lr * (reward + gamma_discount * max_next_q);
					prev_q[prev_action] <- new_val;
					q_table[prev_state] <- prev_q;
					q_updates_count <- q_updates_count + 1;
				}
				
				// 3. Chọn Action theo Epsilon-Greedy
				int chosen_action <- 0; // 0: Extend (Giữ xanh), 1: Switch (Đổi đèn)
				if (force_switch) {
					chosen_action <- 1; // Bắt buộc đổi để tránh kẹt xe kéo dài
				} else {
					if (rnd(1.0) < epsilon) {
						chosen_action <- rnd(1); // Khám phá (Explore)
					} else {
						// Khai thác (Exploit)
						list<float> q_vals <- q_table[curr_state];
						if (q_vals[0] > q_vals[1]) {
							chosen_action <- 0;
						} else if (q_vals[1] > q_vals[0]) {
							chosen_action <- 1;
						} else {
							chosen_action <- rnd(1);
						}
					}
				}
				
				// Giảm dần tỷ lệ khám phá (Epsilon Decay)
				if (epsilon > epsilon_min) {
					epsilon <- epsilon * epsilon_decay;
				}
				
				// Lưu lại state và action để học ở bước kế tiếp
				prev_state <- curr_state;
				prev_action <- chosen_action;
				current_action <- chosen_action;
				
				// 4. Thực thi Action
				if (chosen_action = 1) {
					phase_timer <- 0.0;
					global_phase <- global_phase + 1; // GREEN -> YELLOW (0->1 hoặc 2->3)
				}
			}
		}
	}

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
		
		if (cycle mod 10 = 0 and cycle > 0) {
			write "METRIC_CSV," + cycle + "," + total_vehicles_passed + "," + (round(average_waiting_time*100.0)/100.0) + "," + current_queue_length + "," + (round(average_speed*100.0)/100.0) + "," + (round(average_travel_time*100.0)/100.0) + "," + (round(max_waiting_time*100.0)/100.0);
		}
		
		if (cycle mod 50 = 0 and cycle > 0) {
			write ">> [Q-Learning] Cycle: " + cycle + " | " + phase_names[global_phase] + " (" + (round(phase_timer*10.0)/10.0) + "s) | Action: " + (current_action = 0 ? "EXTEND" : "SWITCH") + " | Eps: " + (round(epsilon*100.0)/100.0) + " | Passed: " + total_vehicles_passed + " | Queue: " + current_queue_length + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s | Avg Speed: " + (round(average_speed*10.0)/10.0) + " km/h";
		}
	}
}

experiment my_experiment type: gui {
	float minimum_cycle_duration <- 0.05#s;
	output {
		display intersection_view background: #black {
			species road aspect: base;
			species base_vehicle_species aspect: base;
			species intersection aspect: base;
			graphics "HUD" {
				draw "Q-LEARNING AI CONTROLLER" at: {20, 15} color: #cyan font: font("Helvetica", 14, #bold);
				draw "Phase: " + phase_names[global_phase] + " (" + int(phase_timer) + "s)" at: {20, 35} color: (global_phase = 0 or global_phase = 2 ? #lime : (global_phase = 1 or global_phase = 3 ? #yellow : #red)) font: font("Helvetica", 16, #bold);
				draw "Action: " + (current_action = 0 ? "EXTEND (0)" : "SWITCH (1)") + " | Epsilon: " + (round(epsilon*100.0)/100.0) at: {20, 55} color: #cyan font: font("Helvetica", 13, #plain);
				draw "Queue NS: " + queue_ns + " | EW: " + queue_ew + " | Q-Updates: " + q_updates_count at: {20, 75} color: #orange font: font("Helvetica", 13, #plain);
				draw "Passed: " + total_vehicles_passed + " | Active: " + length(base_vehicle_species) + " | Queue: " + current_queue_length at: {20, 95} color: #white font: font("Helvetica", 13, #plain);
			}
		}
		display performance_charts {
			chart "Performance Metrics (Q-Learning)" type: series {
				data "Queue Length" value: current_queue_length color: #crimson;
				data "Avg Waiting Time (s)" value: average_waiting_time color: #darkorange;
				data "Avg Speed (km/h)" value: average_speed color: #dodgerblue;
				data "Epsilon" value: epsilon * 10 color: #violet;
			}
		}
	}
}

experiment my_batch_experiment type: batch until: (cycle >= 2000) {
	// Seed giam de 4 thuat toan (Fixed-Time/MaxPressure/Q-Learning/DQN) chay
	// cung luong yeu cau xe -> so sanh cong bang & kha lap lai
	parameter "Seed" var: seed init: 5001.0;
}
