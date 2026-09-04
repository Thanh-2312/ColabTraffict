/**
* Name: intersection_maxpressure
* Description: 4-way traffic intersection simulation controlled by MaxPressure adaptive traffic signal algorithm.
*/

model intersection_maxpressure

import "../includes/collision_avoidance.gaml"

global {
	// MAXPRESSURE CONTROLLER PARAMETERS
	// Phase 0: NS-GREEN, Phase 1: NS-YELLOW (3s fixed)
	// Phase 2: EW-GREEN, Phase 3: EW-YELLOW (3s fixed)
	float phase_timer <- 0.0;
	
	// Timing constraints for stability & safety
	float min_green_time <- 10#s;   // Thời gian xanh tối thiểu để tránh đổi pha liên tục
	float max_green_time <- 60#s;   // Thời gian xanh tối đa để tránh bỏ đói (starvation)
	float yellow_time <- 3#s;       // Thời gian đèn vàng an toàn
	float check_interval <- 5#s;    // Chu kỳ đánh giá áp lực (mỗi 5 giây)
	
	// Road collections for fast pressure calculation
	list<road> ns_incoming_roads <- [];
	list<road> ns_outgoing_roads <- [];
	list<road> ew_incoming_roads <- [];
	list<road> ew_outgoing_roads <- [];
	
	float pressure_ns <- 0.0;
	float pressure_ew <- 0.0;
	
	init {
		// FIX (headless): mang duong chua duoc tao khi init cua model chay
		// -> intersection(1) = nil -> danh sach duong rong -> ap suat luon = 0
		// -> controller "mu", chi con force-switch theo max_green_time (60s).
		// Khoi tao muon duoc chuyen sang reflex init_road_lists ben duoi
		// (cach lam giong intersection-dqn-python.gaml).
	}

	// Khoi tao muon danh sach duong vao/ra khi mang duong da san sang
	reflex init_road_lists when: (empty(ns_incoming_roads) and length(intersection) > 3) {
		ns_incoming_roads <- intersection(1).incoming_outer_roads + intersection(3).incoming_outer_roads;
		ew_incoming_roads <- intersection(0).incoming_outer_roads + intersection(2).incoming_outer_roads;

		ns_outgoing_roads <- road where (
			(distance_to(first(each.shape.points), intersection(1).location) < 1#m and distance_to(last(each.shape.points), intersection(1).location) > 50#m) or
			(distance_to(first(each.shape.points), intersection(3).location) < 1#m and distance_to(last(each.shape.points), intersection(3).location) > 50#m)
		);

		ew_outgoing_roads <- road where (
			(distance_to(first(each.shape.points), intersection(0).location) < 1#m and distance_to(last(each.shape.points), intersection(0).location) > 50#m) or
			(distance_to(first(each.shape.points), intersection(2).location) < 1#m and distance_to(last(each.shape.points), intersection(2).location) > 50#m)
		);
	}
	
	reflex maxpressure_controller {
		phase_timer <- phase_timer + step;
		
		// --- YELLOW PHASES (1, 3): Chuyển tiếp 3s cố định đảm bảo an toàn ---
		if (global_phase = 1 or global_phase = 3) {
			if (phase_timer >= yellow_time) {
				phase_timer <- 0.0;
				global_phase <- (global_phase + 1) mod 4;
			}
		} 
		// --- GREEN PHASES (0, 2): Đánh giá MaxPressure ---
		else {
			bool check_now <- (phase_timer >= min_green_time) and 
			                  (round(phase_timer * 10) mod int(check_interval * 10) = 0);
			bool force_switch <- phase_timer >= max_green_time;
			
			if (check_now or force_switch) {
				int in_ns <- 0; int out_ns <- 0;
				int in_ew <- 0; int out_ew <- 0;
				
				loop v over: base_vehicle_species {
					if (v.current_road != nil) {
						road r <- road(v.current_road);
						if (ns_incoming_roads contains r) { in_ns <- in_ns + 1; }
						else if (ns_outgoing_roads contains r) { out_ns <- out_ns + 1; }
						else if (ew_incoming_roads contains r) { in_ew <- in_ew + 1; }
						else if (ew_outgoing_roads contains r) { out_ew <- out_ew + 1; }
					}
				}
				
				// Áp lực mạng lưới = Số xe vào - Số xe ra
				pressure_ns <- float(in_ns - out_ns);
				pressure_ew <- float(in_ew - out_ew);
				
				if (global_phase = 0) { // NS-GREEN
					if (force_switch or (pressure_ew > pressure_ns + 2.0)) {
						phase_timer <- 0.0;
						global_phase <- 1; // NS-YELLOW
					}
				} else if (global_phase = 2) { // EW-GREEN
					if (force_switch or (pressure_ns > pressure_ew + 2.0)) {
						phase_timer <- 0.0;
						global_phase <- 3; // EW-YELLOW
					}
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
			write ">> [MaxPressure] Cycle: " + cycle + " | " + phase_names[global_phase] + " (" + (round(phase_timer*10.0)/10.0) + "s) | Pressures [NS: " + int(pressure_ns) + " vs EW: " + int(pressure_ew) + "] | Passed: " + total_vehicles_passed + " | Queue: " + current_queue_length + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s | Avg Speed: " + (round(average_speed*10.0)/10.0) + " km/h";
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
				draw "MAXPRESSURE CONTROLLER" at: {20, 15} color: #lime font: font("Helvetica", 14, #bold);
				draw "Phase: " + phase_names[global_phase] + " (" + int(phase_timer) + "s)" at: {20, 35} color: (global_phase = 0 or global_phase = 2 ? #lime : (global_phase = 1 or global_phase = 3 ? #yellow : #red)) font: font("Helvetica", 16, #bold);
				draw "Pressure NS: " + int(pressure_ns) + " | EW: " + int(pressure_ew) at: {20, 60} color: #cyan font: font("Helvetica", 13, #plain);
				draw "Passed: " + total_vehicles_passed + " | Active: " + length(base_vehicle_species) + " | Queue: " + current_queue_length at: {20, 80} color: #white font: font("Helvetica", 13, #plain);
				draw "Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s | Avg Speed: " + (round(average_speed*10.0)/10.0) + " km/h" at: {20, 100} color: #yellow font: font("Helvetica", 13, #plain);
			}
		}
		display performance_charts {
			chart "Performance Metrics (MaxPressure)" type: series {
				data "Queue Length (vehicles)" value: current_queue_length color: #crimson;
				data "Avg Waiting Time (s)" value: average_waiting_time color: #darkorange;
				data "Avg Speed (km/h)" value: average_speed color: #dodgerblue;
			}
		}
	}
}

experiment my_batch_experiment type: batch until: (cycle >= 2000) {
	// Seed giam de 4 thuat toan (Fixed-Time/MaxPressure/Q-Learning/DQN) chay
	// cung luong yeu cau xe -> so sanh cong bang & kha lap lai
	parameter "Seed" var: seed init: 5001.0;
}
