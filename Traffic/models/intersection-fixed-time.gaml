/**
* Name: intersection_traffic
* Description: 4-way traffic intersection simulation with Fixed-Time baseline signal controller.
*/

model intersection_traffic

import "../includes/collision_avoidance.gaml"

global {
	// GLOBAL TRAFFIC LIGHT CONTROLLER (4-Phase Cycle with Yellow Lights)
	// Phase 0: North-South GREEN (30s), East-West RED
	// Phase 1: North-South YELLOW (3s), East-West RED
	// Phase 2: East-West GREEN (30s), North-South RED
	// Phase 3: East-West YELLOW (3s), North-South RED
	float global_counter <- 0.0;
	list<float> phase_durations <- [30#s, 3#s, 30#s, 3#s];
	
	reflex traffic_light_controller {
		global_counter <- global_counter + step;
		if (global_counter >= phase_durations[global_phase]) {
			global_counter <- 0.0;
			global_phase <- (global_phase + 1) mod length(phase_durations);
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
			write ">> Cycle: " + cycle + " | Phase: " + phase_names[global_phase] + " (" + round(global_counter*10.0)/10.0 + "s/" + phase_durations[global_phase] + "s) | Passed: " + total_vehicles_passed + " | Queue: " + current_queue_length + " | Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s | Max Wait: " + (round(max_waiting_time*10.0)/10.0) + "s | Avg Speed: " + (round(average_speed*10.0)/10.0) + " km/h | Avg Travel: " + (round(average_travel_time*10.0)/10.0) + "s";
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
				draw "FIXED-TIME BASELINE" at: {20, 15} color: #yellow font: font("Helvetica", 14, #bold);
				draw "Phase: " + phase_names[global_phase] + " (" + int(global_counter) + "s / " + int(phase_durations[global_phase]) + "s)" at: {20, 35} color: (global_phase = 0 or global_phase = 2 ? #lime : (global_phase = 1 or global_phase = 3 ? #yellow : #red)) font: font("Helvetica", 16, #bold);
				draw "Passed: " + total_vehicles_passed + " | Active: " + length(base_vehicle_species) + " | Queue: " + current_queue_length at: {20, 60} color: #white font: font("Helvetica", 13, #plain);
				draw "Avg Wait: " + (round(average_waiting_time*10.0)/10.0) + "s | Avg Speed: " + (round(average_speed*10.0)/10.0) + " km/h" at: {20, 80} color: #cyan font: font("Helvetica", 13, #plain);
			}
		}
		display performance_charts {
			chart "Performance Metrics (Fixed-Time Baseline)" type: series {
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
