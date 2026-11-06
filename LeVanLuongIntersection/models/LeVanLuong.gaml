/**
 * Name: LeVanLuong
 * Ngã tư Lê Văn Lương × Hoàng Đạo Thúy / Hoàng Minh Giám (cạnh 27 Lê Văn Lương, Thanh Xuân, Hà Nội).
 * Bố cục đường theo số đo ảnh vệ tinh (scripts/build_layout.py → includes/*.geojson), mô phỏng bằng advanced_driving:
 * mỗi chiều mỗi nhánh là 1 road với num_lanes = số sublane rộng 0,8 m; xe máy chiếm 1 sublane, ô tô 2 sublane.
 * Vùng xung đột = các road "connector" (trái / thẳng / phải) có hình học thật nối vạch dừng → đầu nhánh ra.
 */
model LeVanLuong

global {
	file roads_file <- geojson_file("../includes/roads.geojson");
	file areas_file <- geojson_file("../includes/areas.geojson");
	geometry shape <- envelope(areas_file);
	float step <- 0.2 #s;
	float sublane_width <- 0.8; // m — phải khớp SUBLANE_W trong scripts/build_layout.py (num_lanes đã tính sẵn từ số này)

	// ---- Nhu cầu (giả định, sửa theo số đếm thực tế) ----
	float flow_per_approach <- 2400.0; // xe/h mỗi nhánh vào
	float motorbike_ratio <- 0.85;
	float p_left <- 0.2;
	float p_right <- 0.2;

	// ---- Đèn 2 pha cố định (giả định): pha LVL (NE + SW), pha HĐT (NW + SE) ----
	float green_lvl <- 50.0 #s;
	float green_hdt <- 40.0 #s;
	float all_red <- 3.0 #s;
	float cycle_length <- green_lvl + green_hdt + 2 * all_red; // "cycle" là biến có sẵn của GAMA
	string phase <- "LVL";

	graph road_network;
	list<road> approaches;
	map<string, int> front_row_max; // số sublane bị chiếm đồng thời ở hàng đầu (≤ 1,5 m trước vạch dừng), lớn nhất từ đầu mô phỏng

	init {
		create area from: areas_file with: [kind::string(read("kind"))];
		create road from: roads_file with: [rid::string(read("id")), kind::string(read("kind")), arm::string(read("arm")),
			to_arm::string(read("to_arm")), turn::string(read("turn")), num_lanes::int(read("num_lanes")), width::float(read("width"))] {
			maxspeed <- (kind = "connector" ? 40.0 : 60.0) * #km / #h;
		}
		// nút = đầu/cuối của các road (Python sinh tọa độ trùng khít nên không cần file nút riêng)
		loop p over: remove_duplicates(road accumulate [first(each.shape.points), last(each.shape.points)]) {
			create intersection with: [location::p];
		}
		road_network <- as_driving_graph(road, intersection);
		approaches <- road where (each.kind = "approach");
		ask approaches { // source_node / target_node do as_driving_graph gán sẵn
			ask intersection(target_node) {
				approach <- myself;
				stop << [];
			}
			front_row_max[arm] <- 0;
		}
	}

	reflex signal {
		float t <- time - cycle_length * floor(time / cycle_length);
		phase <- t < green_lvl ? "LVL" : (t < green_lvl + all_red ? "none" : (t < green_lvl + all_red + green_hdt ? "HDT" : "none"));
		ask intersection where (each.approach != nil) {
			bool green <- (approach.arm in ["NE", "SW"]) ? (phase = "LVL") : (phase = "HDT");
			if green { stop[0] <- []; } else { stop[0] <- [approach]; }
		}
	}

	reflex spawn {
		ask approaches {
			if flip(flow_per_approach / 3600 * step) {
				float r <- rnd(1.0);
				string turn_wanted <- r < p_left ? "left" : (r < p_left + p_right ? "right" : "through");
				road c <- road first_with (each.kind = "connector" and each.arm = arm and each.turn = turn_wanted);
				road ex <- road first_with (each.kind = "exit" and each.arm = c.to_arm);
				create vehicle with: [location::source_node.location, dest::intersection(ex.target_node), is_car::flip(1 - motorbike_ratio)];
			}
		}
	}

	reflex measure_front_row {
		ask approaches {
			int n <- front_row();
			if n > front_row_max[arm] { front_row_max[arm] <- n; }
		}
	}
}

species area {
	string kind;
	aspect default {
		switch kind {
			match "asphalt" { draw shape color: rgb(70, 70, 75); }
			match "median" { draw shape color: rgb(90, 140, 80); }
			match "crosswalk" { draw shape color: rgb(220, 220, 220, 0.55); }
			match "conflict" { draw shape color: rgb(255, 80, 60, 0.18) border: rgb(255, 80, 60); }
			match "stopline" { draw shape + 0.15 color: #white; }
			match "sublane" { draw shape color: rgb(255, 255, 255, 0.25); }
		}
	}
}

species road skills: [road_skill] {
	string rid;
	string kind;   // approach | exit | connector
	string arm;    // NE | SE | SW | NW (nhánh xuất phát với connector)
	string to_arm;
	string turn;   // left | through | right (connector)
	float width;

	// số sublane khác nhau đang bị chiếm bởi xe có đầu xe cách vạch dừng ≤ 1,5 m
	int front_row {
		list<int> occ <- [];
		point stop_pt <- last(shape.points);
		loop v over: all_agents where ((each distance_to stop_pt) <= 1.5) {
			vehicle vv <- vehicle(v);
			occ <- occ + range(vv.lowest_lane, vv.lowest_lane + vv.num_lanes_occupied - 1);
		}
		return length(remove_duplicates(occ));
	}

	aspect default {
		if kind = "connector" { draw shape color: rgb(255, 255, 255, 0.15); }
	}

	aspect label {
		if kind != "connector" {
			draw arm + (kind = "approach" ? " vào: " : " ra: ") + num_lanes + " sublane (" + width + " m)"
				at: shape.points[0] color: #yellow font: font("Arial", 11, #bold) anchor: #center;
		}
	}
}

species intersection skills: [intersection_skill] {
	road approach; // khác nil ⇔ nút vạch dừng có đèn
	aspect default {
		if approach != nil {
			draw circle(1.2) color: empty(stop[0]) ? #green : #red border: #black;
		}
	}
}

species vehicle skills: [driving] {
	intersection dest;
	bool is_car;
	rgb color;

	init {
		color <- is_car ? rgb(80, 160, 255) : rgb(255, 210, 60); // gán trong init vì is_car đến từ with:
		num_lanes_occupied <- is_car ? 2 : 1;
		vehicle_length <- is_car ? 4.5 #m : 1.9 #m;
		max_speed <- (is_car ? gauss(50, 5) : gauss(40, 5)) * #km / #h;
		max_acceleration <- is_car ? 2.5 : 2.0;
		time_headway <- is_car ? 1.2 : 0.6;
		min_safety_distance <- is_car ? 1.0 : 0.3;
		lane_change_limit <- -1;
		linked_lane_limit <- 0;
		proba_use_linked_road <- 0.0;
		proba_respect_priorities <- 0.0;
		proba_block_node <- 0.0;
		proba_respect_stops <- [1.0];
		acc_gain_threshold <- 0.05;
		politeness_factor <- 0.1;
	}

	reflex choose_path when: final_target = nil {
		do compute_path graph: road_network target: dest;
	}

	reflex move when: final_target != nil {
		do drive;
		if final_target = nil {
			do unregister;
			do die;
		}
	}

	// đường polyline nằm ở mép dải phân cách; sublane 0 sát bó vỉa bên phải
	point display_position {
		float dist <- (road(current_road).num_lanes - lowest_lane - mean(range(num_lanes_occupied - 1)) - 0.5) * sublane_width;
		return location + {cos(heading + 90) * dist, sin(heading + 90) * dist};
	}

	aspect default {
		if current_road != nil {
			draw rectangle(vehicle_length, is_car ? 1.7 : 0.7) at: display_position() rotate: heading color: color border: #black;
		}
	}
}

experiment main type: gui {
	parameter "Lưu lượng mỗi nhánh vào (xe/h)" var: flow_per_approach min: 0.0 max: 8000.0;
	parameter "Tỷ lệ xe máy" var: motorbike_ratio min: 0.0 max: 1.0;
	parameter "Tỷ lệ rẽ trái" var: p_left min: 0.0 max: 1.0;
	parameter "Tỷ lệ rẽ phải" var: p_right min: 0.0 max: 1.0;
	parameter "Xanh Lê Văn Lương (s)" var: green_lvl;
	parameter "Xanh Hoàng Đạo Thúy (s)" var: green_hdt;

	output {
		display "Ngã tư" type: 2d background: rgb(40, 45, 40) {
			species area;
			species road;
			species intersection;
			species vehicle;
			species road aspect: label;
		}
		monitor "Pha đèn" value: phase;
		monitor "Số xe" value: length(vehicle);
		monitor "NE vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "NE_in")).num_lanes) + " / " + front_row_max["NE"];
		monitor "SE vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "SE_in")).num_lanes) + " / " + front_row_max["SE"];
		monitor "SW vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "SW_in")).num_lanes) + " / " + front_row_max["SW"];
		monitor "NW vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "NW_in")).num_lanes) + " / " + front_row_max["NW"];
	}
}
