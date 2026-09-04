/**
* Name: collision_avoidance
* Description: Base model với IDM car-following đơn giản (built-in driving skill GAMA).
*              Nếu 2 xe va chạm nhau thì cứ cho đi bình thường — trọng tâm là so sánh 3 thuật toán đèn.
*              Tham khảo: IDM (Treiber et al., 2000), MOBIL (Kesting et al., 2007)
*/

model collision_avoidance

global {
	float step <- 0.1 #s;
	float lane_width <- 1.5#m;  
	int nb_lanes <- 6;
	
	graph road_network;
	
	point intersection_center <- {220, 220};
	float distance_to_intersection_center <- 20 #m;
	float road_length <- 100 #m;

	// Intersection entry points (internal nodes)
	point p1 <- intersection_center + {distance_to_intersection_center, 0};   // East entry
	point p2 <- intersection_center - {0, distance_to_intersection_center};   // North entry
	point p3 <- intersection_center - {distance_to_intersection_center, 0};   // West entry
	point p4 <- intersection_center + {0, distance_to_intersection_center};   // South entry
	
	// Outer endpoints where vehicles spawn/despawn
	point p5 <- p1 + {road_length, 0};  // East spawn (intersection 4)
	point p6 <- p2 - {0, road_length};  // North spawn (intersection 5)
	point p7 <- p3 - {road_length, 0};  // West spawn (intersection 6)
	point p8 <- p4 + {0, road_length};  // South spawn (intersection 7)

	// Straight roads (Outer)
	geometry road1 <- line(p1, p5);
	geometry road2 <- line(p2, p6);
	geometry road3 <- line(p3, p7);
	geometry road4 <- line(p4, p8);
	
	// Left Turns (Inside intersection)
	float curvature <- 0.5;
	geometry road5 <- curve(p2, p1, curvature); // N to E
	geometry road6 <- curve(p3, p2, curvature); // W to N
	geometry road7 <- curve(p4, p3, curvature); // S to W
	geometry road8 <- curve(p1, p4, curvature); // E to S
	
	// Right Turns (Inside intersection)
	geometry road11 <- curve(p2, p3, -curvature); // N to W
	geometry road12 <- curve(p3, p4, -curvature); // W to S
	geometry road13 <- curve(p4, p1, -curvature); // S to E
	geometry road14 <- curve(p1, p2, -curvature); // E to N

	// Straight through (Inside intersection)
	geometry road9 <- line(p1, p3); // East to West
	geometry road10 <- line(p2, p4); // North to South
	
	list<geometry> my_roads <- [road1, road2, road3, road4, road9, road10, road5, road6, road7, road8, road11, road12, road13, road14];
	list<point> my_points <- [p1, p2, p3, p4, p5, p6, p7, p8];
	
	list<intersection> intersection_target_list;
	geometry shape <- envelope(350);
	
	// Global Traffic Light state variables shared by all models
	int global_phase <- 0;
	list<string> phase_names <- ["NS-GREEN", "NS-YELLOW", "EW-GREEN", "EW-YELLOW"];
	
	// 6 PERFORMANCE METRICS
	int total_vehicles_created <- 0;
	int total_vehicles_passed <- 0;
	float average_waiting_time <- 0.0;
	float max_waiting_time <- 0.0;
	float average_speed <- 0.0;
	int current_queue_length <- 0;
	float total_travel_time_sum <- 0.0;
	float average_travel_time <- 0.0;
	
	// Spawning rates (Lưu lượng xe)
	int spawn_rate_NS <- 15;
	int spawn_rate_EW <- 45;

	init {
		loop my_point over: my_points {
			create intersection with: (location: my_point, shape: my_point);
		}

		intersection_target_list <- [intersection(4), intersection(5), intersection(6), intersection(7)];

		loop my_road_shape over: my_roads {
			create road {
				shape <- my_road_shape;
				num_lanes <- nb_lanes;
				maxspeed <- 60 #km/#h;
				create road {
					num_lanes <- myself.num_lanes;
					shape <- line(reverse(myself.shape.points));
					maxspeed <- myself.maxspeed;
					linked_road <- myself;
					myself.linked_road <- self;
				}
			}
		}
		
		road_network <- as_driving_graph(road, intersection);
		
		// Setup traffic lights at the 4 entry nodes
		ask intersection(0) { is_traffic_signal <- true; direction_type <- 1; do init_signal; } // East (p1)
		ask intersection(1) { is_traffic_signal <- true; direction_type <- 0; do init_signal; } // North (p2)
		ask intersection(2) { is_traffic_signal <- true; direction_type <- 1; do init_signal; } // West (p3)
		ask intersection(3) { is_traffic_signal <- true; direction_type <- 0; do init_signal; } // South (p4)
	}
}

species intersection skills: [intersection_skill] {
	bool is_traffic_signal <- false;
	int direction_type <- 0; // 0: NS, 1: EW
	rgb light_color <- #red;
	list<road> incoming_outer_roads;

	action init_signal {
		stop <- [[]];
		incoming_outer_roads <- road where (distance_to(last(each.shape.points), location) < 1#m and distance_to(first(each.shape.points), location) > 50#m);
	}

	reflex update_lights when: is_traffic_signal {
		if (direction_type = 0) { // North & South
			if (global_phase = 0) {
				light_color <- #green;
				stop[0] <- []; // Green: allow traffic to enter and pass!
			} else if (global_phase = 1) {
				light_color <- #yellow;
				stop[0] <- incoming_outer_roads; // Yellow: block new arrivals to clear intersection
			} else {
				light_color <- #red;
				stop[0] <- incoming_outer_roads; // Red: block incoming traffic!
			}
		} else { // East & West
			if (global_phase = 2) {
				light_color <- #green;
				stop[0] <- []; // Green: allow traffic to enter and pass!
			} else if (global_phase = 3) {
				light_color <- #yellow;
				stop[0] <- incoming_outer_roads; // Yellow: block new arrivals to clear intersection
			} else {
				light_color <- #red;
				stop[0] <- incoming_outer_roads; // Red: block incoming traffic!
			}
		}
	}

	aspect base {
		if is_traffic_signal {
			float angle <- location direction_to intersection_center;
			point offset <- {cos(angle - 90) * 8.0, sin(angle - 90) * 8.0};
			draw circle(4.5) at: location + offset color: light_color border: #white;
		}
	}
}

species road skills: [road_skill] {
	rgb color <- #dimgray; 
	aspect base {
		float road_width <- num_lanes * lane_width + 0.5;
		draw (shape + road_width) color: color border: #white;
	}
}

// ==================================================================================
// BASE VEHICLE SPECIES - CHỈ SỬ DỤNG IDM CAR-FOLLOWING ĐƠN GIẢN (BUILT-IN GAMA)
// Collision avoidance: Dựa hoàn toàn vào IDM built-in (min_safety_distance, time_headway)
// Nếu 2 xe va chạm nhau → cứ cho đi bình thường (không xử lý phức tạp)
// Lý do: Trọng tâm nghiên cứu là SO SÁNH 3 THUẬT TOÁN ĐÈN GIAO THÔNG
// Tham khảo: Hầu hết các nghiên cứu mô phỏng traffic signal control (SUMO, GAMA)
//            đều dùng IDM car-following đơn giản và chấp nhận va chạm nhỏ tại ngã tư
// ==================================================================================
species base_vehicle_species skills: [driving] {
	rgb color;
	intersection target;
	int current_lane <- 0;
	float waiting_time <- 0.0;
	float spawn_time <- 0.0;
	
	init {
		spawn_time <- time;
		right_side_driving <- true;
		
		// Cho phép xe đi xuyên qua node ngã tư mà không bị block
		// => Nếu 2 xe va nhau tại ngã tư thì cứ đi bình thường
		proba_block_node <- 0.0;
		proba_respect_priorities <- 1.0;
		proba_respect_stops <- [1.0];
		lane_change_limit <- 2;
		
		// IDM car-following parameters (Treiber et al., 2000)
		// Đây là cơ chế tránh va chạm chính: xe tự động giảm tốc khi gần xe trước
		max_acceleration <- 2.0;     // m/s² - Gia tốc tối đa
		max_deceleration <- 4.5;     // m/s² - Phanh tối đa
		min_safety_distance <- 2.0;  // m - Khoảng cách an toàn tối thiểu (IDM s0)
		time_headway <- 1.2;         // s - Thời gian headway (IDM T)
		speed_coeff <- 1.0;          // Hệ số tốc độ mong muốn
	}
	
	// ĐẾM THỜI GIAN CHỜ (cho metrics)
	reflex count_waiting {
		if (speed < 1.0 #km/#h) {
			waiting_time <- waiting_time + step;
		}
	}
	
	// DI CHUYỂN - Hoàn toàn dựa vào `do drive` built-in của GAMA driving skill
	// GAMA driving skill đã tích hợp sẵn:
	//   - IDM car-following (giữ khoảng cách xe trước)
	//   - Dừng đèn đỏ (intersection_skill stop)
	//   - Đi theo road graph
	// Nếu 2 xe vô tình đè lên nhau → cứ cho đi tiếp bình thường
	reflex move when: final_target != nil {
		do drive;
		if (final_target = nil) {
			total_vehicles_passed <- total_vehicles_passed + 1;
			total_travel_time_sum <- total_travel_time_sum + (time - spawn_time);
			average_travel_time <- total_travel_time_sum / total_vehicles_passed;
			do unregister;
			do die;
		}
	}
	
	// TÍNH TOÁN VỊ TRÍ HIỂN THỊ CHÍNH XÁC THEO LÀN
	point compute_position {
		if (current_road != nil) {
			float dist <- (road(current_road).num_lanes - lowest_lane - mean(range(num_lanes_occupied - 1)) - 0.5) * lane_width;
			if violating_oneway { dist <- -dist; }
			point shift_pt <- {cos(heading + 90) * dist, sin(heading + 90) * dist};
			return location + shift_pt;
		} else { return {0, 0}; }
	}
	
	// HIỂN THỊ XE
	aspect base {
		if (current_road != nil) {
			point pos <- compute_position();
			float draw_width <- (lane_width * num_lanes_occupied) * 0.85;
			draw rectangle(vehicle_length, draw_width) at: pos color: color rotate: heading border: #black;
			draw triangle(draw_width * 0.9) at: pos color: #white rotate: heading + 90 border: #black;
		}
	}
}
