/**
 * Name: LeVanLuong
 * Ngã tư Lê Văn Lương × Hoàng Đạo Thúy / Hoàng Minh Giám (cạnh 27 Lê Văn Lương, Thanh Xuân, Hà Nội).
 * Bố cục đường theo số đo ảnh vệ tinh (scripts/build_layout.py → includes/*.geojson), mô phỏng bằng advanced_driving:
 * mỗi chiều mỗi nhánh là 1 road với num_lanes = số sublane rộng 0,8 m; xe máy chiếm 1 sublane, ô tô 2, buýt 3.
 * Vùng xung đột = các road "connector" (trái / thẳng / phải) có hình học thật nối vạch dừng → đầu nhánh ra.
 *
 * Hai chế độ điều khiển đèn:
 *  - experiment "main" (GUI): đèn 2 pha cố định LVL / HĐT như trước.
 *  - experiment "dqn_server_experiment": 4 pha do Python chọn qua gama-server, cùng giao thức với
 *    Traffic/models/intersection-dqn-python.gaml (xem dqn_py/gama_env.py, chỉ state "spatial" cho rainbow/hybrid).
 *    Slot E, N, W, S của gama_env = NE, NW, SW, SE. Action 0: HĐT/HMG thẳng + phải, 1: HĐT/HMG rẽ trái,
 *    2: LVL thẳng + phải, 3: LVL rẽ trái. Giữ pha = xanh thêm 10 s; đổi pha = vàng 3 s, đỏ toàn phần
 *    ≥ 2 s tới khi vùng xung đột trống (tối đa 10 s), rồi xanh tối thiểu 10 s.
 * Đèn theo từng hướng rẽ: mỗi nút vạch dừng có 3 loại stop (0 thẳng, 1 trái, 2 phải); xe chỉ tôn trọng loại stop
 * của hướng mình đi (proba_respect_stops), nên rẽ trái bảo vệ không cho xe đi thẳng cùng nhánh chạy theo.
 */
model LeVanLuong

global {
	file roads_file <- geojson_file("../includes/roads.geojson");
	file areas_file <- geojson_file("../includes/areas.geojson");
	geometry shape <- envelope(areas_file);
	float step <- 0.1 #s; // gama_env.py tính thời gian và lịch quyết định theo cycle 0,1 s
	float sublane_width <- 0.8; // m — phải khớp SUBLANE_W trong scripts/build_layout.py (num_lanes đã tính sẵn từ số này)

	// ---- Nhu cầu khi không có CSV (giả định, sửa theo số đếm thực tế) ----
	float flow_per_approach <- 2400.0; // xe/h mỗi nhánh vào
	float motorbike_ratio <- 0.85;
	float p_left <- 0.2;
	float p_right <- 0.2;
	// Lịch xe ghép cặp do dqn_py/demand.py (site "lvl") sinh: cycle, slot nhánh 0..3, loại xe 0/1/2, tốc độ mong muốn km/h, rẽ 0 thẳng/1 trái/2 phải, (cột 6 bỏ qua)
	string demand_file_path <- "";
	float rng_seed <- 1093.0; // Python truyền seed qua tham số thường (tham số "seed" của reload bị bỏ qua)
	bool fast_training <- false; // Python luôn gửi; model này không có phần trang trí nào để tắt
	string training_reward_mode <- "all";

	// ---- Đèn 2 pha cố định (GUI): pha LVL (NE + SW), pha HĐT (NW + SE) ----
	float green_lvl <- 50.0 #s;
	float green_hdt <- 40.0 #s;
	float all_red <- 3.0 #s;
	float cycle_length <- green_lvl + green_hdt + 2 * all_red; // "cycle" là biến có sẵn của GAMA
	string phase <- "LVL";

	// ---- Giao diện 4 pha cho Python ----
	bool python_controlled <- false;
	list<string> slot_arms <- ["NE", "NW", "SW", "SE"]; // = E, N, W, S
	map<string, int> arm_slot <- ["NE"::0, "NW"::1, "SW"::2, "SE"::3];
	list<string> turn_names <- ["through", "left", "right"];
	int global_phase <- 0; // chẵn: xanh của action global_phase/2, lẻ: vàng của pha đó
	int green_cycles <- 0;
	int yellow_cycles <- 0;
	int min_green_cycles <- 100;
	int yellow_len_cycles <- 30;
	int min_all_red_cycles <- 20;
	// shortcut: xe trên connector cắt nhau không thấy nhau nên đỏ toàn phần có trần 10 s, tránh xe kẹt vì đường ra đầy chặn mọi pha sau; bỏ trần khi có mô hình xung đột trong nút
	int max_all_red_cycles <- 100;
	int dqn_action <- -1;
	bool dqn_waiting_action <- false;
	int next_decision_in_cycles <- 100;
	int decision_count <- 0;
	int pending_green_phase <- 0;
	int all_red_cycles <- 0;
	bool dqn_all_red <- false;
	list<int> dqn_action_mask <- [1, 1, 1, 1];
	string spatial_pack <- "";
	list<float> spatial_pressure <- [0.0, 0.0, 0.0, 0.0];
	int spatial_capture_cycle <- -1;

	// ---- Chỉ số đọc bởi gama_env.py ----
	int queue_ns <- 0; // NS = slot N, S = Hoàng Minh Giám + Hoàng Đạo Thúy
	int queue_ew <- 0; // EW = Lê Văn Lương
	int approach_ns <- 0;
	int approach_ew <- 0;
	int current_queue_length <- 0;
	float average_waiting_time <- 0.0;
	float max_waiting_time <- 0.0;
	float average_speed <- 0.0;
	float average_travel_time <- 0.0;
	float total_travel_time <- 0.0;
	int total_vehicles_passed <- 0;
	int total_vehicles_created <- 0;
	float system_time_integral <- 0.0; // R1: xe-giây trong mạng + chờ vào mạng
	float stopped_time_integral <- 0.0; // R2: xe-giây dừng dưới 1 km/h
	float external_all_time_integral <- 0.0; // xe-giây chờ vào mạng
	float outgoing_block_integral <- 0.0; // R3: xe-giây chậm dưới 5 km/h trong 80 m đầu đường ra
	float weighted_delay_integral <- 0.0; // R4: PCU × hụt tốc độ so với tốc độ mong muốn, xe chờ vào mạng tính hụt hoàn toàn
	float external_weighted_pending <- 0.0;

	// ---- Hàng đợi ngoài mạng: mỗi yêu cầu [cycle, slot, loại, km/h, rẽ]; xe chỉ được tạo khi nút nguồn trống ----
	list<list<float>> requests <- [];
	int request_cursor <- 0;
	map<int, list<int>> queues <- [0::[], 1::[], 2::[], 3::[]];
	int pending_count <- 0;
	list<vehicle> at_source <- [nil, nil, nil, nil];

	graph road_network;
	list<road> approaches;
	list<road> slot_approach <- [];
	list<intersection> slot_source <- [];
	list<intersection> dest_of <- []; // [slot * 3 + rẽ] → nút cuối đường ra
	list<int> exit_slot_of <- []; // [slot * 3 + rẽ] → slot của nhánh ra
	map<string, int> front_row_max; // số sublane bị chiếm đồng thời ở hàng đầu (≤ 1,5 m trước vạch dừng), lớn nhất từ đầu mô phỏng

	init {
		seed <- int(rng_seed);
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
				stop << []; // 0: đi thẳng
				stop << []; // 1: rẽ trái
				stop << []; // 2: rẽ phải
			}
			front_row_max[arm] <- 0;
		}
		loop k from: 0 to: 3 {
			string a <- slot_arms[k];
			road r <- road first_with (each.kind = "approach" and each.arm = a);
			add r to: slot_approach;
			add intersection(r.source_node) to: slot_source;
			loop t from: 0 to: 2 {
				string tn <- turn_names[t];
				road c <- road first_with (each.kind = "connector" and each.arm = a and each.turn = tn);
				road ex <- road first_with (each.kind = "exit" and each.arm = c.to_arm);
				add intersection(ex.target_node) to: dest_of;
				add arm_slot[c.to_arm] to: exit_slot_of;
			}
		}
		if (demand_file_path != "") {
			matrix<float> m <- matrix<float>(csv_file(demand_file_path, ",", float, false));
			loop i from: 0 to: m.rows - 1 {
				add [m[0, i], m[1, i], m[2, i], m[3, i], m[4, i]] to: requests;
			}
		}
	}

	float pcu(int c) {
		return c = 0 ? 0.3 : (c = 2 ? 2.0 : 1.0);
	}

	bool movement_green(string a, int t) {
		bool lvl_axis <- a in ["NE", "SW"];
		if (!python_controlled) {
			return lvl_axis ? (phase = "LVL") : (phase = "HDT");
		}
		if (dqn_all_red) { return false; }
		int act <- int(global_phase / 2); // vàng vẫn cho đi; đỏ toàn phần chờ xe đã vào nút thoát ra
		return (act = 0 and !lvl_axis and t != 1) or (act = 1 and !lvl_axis and t = 1) or
			(act = 2 and lvl_axis and t != 1) or (act = 3 and lvl_axis and t = 1);
	}

	bool junction_clear {
		return empty(vehicle where (each.current_road != nil and road(each.current_road).kind = "connector"));
	}

	bool source_free(int k) {
		vehicle v <- at_source[k];
		return v = nil or dead(v) or v.current_road != nil;
	}

	action set_dqn_action(int a) {
		dqn_action <- a;
	}

	reflex admit_demand {
		if (demand_file_path = "") {
			loop k from: 0 to: 3 {
				if (flip(flow_per_approach / 3600.0 * step)) {
					int c <- flip(motorbike_ratio) ? 0 : 1;
					float r <- rnd(1.0);
					add [float(cycle), float(k), float(c), c = 0 ? gauss(40.0, 5.0) : gauss(50.0, 5.0),
						r < p_left ? 1.0 : (r < p_left + p_right ? 2.0 : 0.0)] to: requests;
				}
			}
		}
		loop while: request_cursor < length(requests) {
			list<float> q <- requests[request_cursor];
			if (q[0] > cycle) { break; }
			queues[int(q[1])] <- queues[int(q[1])] + request_cursor;
			external_weighted_pending <- external_weighted_pending + pcu(int(q[2]));
			request_cursor <- request_cursor + 1;
		}
		pending_count <- 0;
		loop k from: 0 to: 3 {
			if (!empty(queues[k]) and source_free(k)) {
				int idx <- first(queues[k]);
				list<float> q <- requests[idx];
				int t <- int(q[4]);
				if (t > 2) { t <- 0; } // nút này không có quay đầu
				create vehicle with: [location::slot_source[k].location, dest::dest_of[k * 3 + t], vclass::int(q[2]),
					desired_mps::q[3] / 3.6, move_turn::t, slot::k, spawn_time::time] returns: born;
				at_source[k] <- first(born);
				total_vehicles_created <- total_vehicles_created + 1;
				queues[k] <- queues[k] - idx;
				external_weighted_pending <- max([0.0, external_weighted_pending - pcu(int(q[2]))]);
			}
			pending_count <- pending_count + length(queues[k]);
		}
	}

	reflex fixed_time_signal when: !python_controlled {
		float t <- time - cycle_length * floor(time / cycle_length);
		phase <- t < green_lvl ? "LVL" : (t < green_lvl + all_red ? "none" : (t < green_lvl + all_red + green_hdt ? "HDT" : "none"));
	}

	reflex dqn_controller when: python_controlled {
		if (dqn_all_red) {
			all_red_cycles <- all_red_cycles + 1;
			if (all_red_cycles >= min_all_red_cycles and (all_red_cycles >= max_all_red_cycles or junction_clear())) {
				dqn_all_red <- false;
				all_red_cycles <- 0;
				global_phase <- pending_green_phase;
				green_cycles <- 0;
			}
		} else if (global_phase mod 2 = 1) {
			yellow_cycles <- yellow_cycles + 1;
			if (yellow_cycles >= yellow_len_cycles) {
				yellow_cycles <- 0;
				dqn_all_red <- true;
			}
		} else {
			green_cycles <- green_cycles + 1;
			if (dqn_waiting_action and dqn_action >= 0) {
				decision_count <- decision_count + 1;
				dqn_waiting_action <- false;
				pending_green_phase <- dqn_action * 2;
				dqn_action <- -1;
				if (pending_green_phase != global_phase) {
					global_phase <- global_phase + 1; // xanh hiện tại → vàng của nó
					yellow_cycles <- 0;
				}
			} else if (!dqn_waiting_action and green_cycles >= min_green_cycles and green_cycles mod min_green_cycles = 0) {
				dqn_waiting_action <- true;
			}
		}
	}

	reflex observe_queues when: !python_controlled or dqn_waiting_action {
		queue_ns <- 0;
		queue_ew <- 0;
		approach_ns <- 0;
		approach_ew <- 0;
		loop v over: vehicle where (each.current_road != nil and road(each.current_road).kind = "approach") {
			bool ns <- v.slot = 1 or v.slot = 3;
			if (v.speed < 1.0 #km / #h) {
				if (ns) { queue_ns <- queue_ns + 1; } else { queue_ew <- queue_ew + 1; }
			} else {
				if (ns) { approach_ns <- approach_ns + 1; } else { approach_ew <- approach_ew + 1; }
			}
		}
	}

	reflex apply_signals {
		loop r over: approaches {
			bool g0 <- movement_green(r.arm, 0);
			bool g1 <- movement_green(r.arm, 1);
			bool g2 <- movement_green(r.arm, 2);
			ask intersection(r.target_node) {
				stop[0] <- g0 ? [] : [r];
				stop[1] <- g1 ? [] : [r];
				stop[2] <- g2 ? [] : [r];
			}
		}
	}

	reflex update_schedule when: python_controlled {
		if (dqn_waiting_action) {
			next_decision_in_cycles <- 1;
		} else if (dqn_all_red) {
			next_decision_in_cycles <- all_red_cycles >= min_all_red_cycles ? 1 :
				min_all_red_cycles - all_red_cycles + min_green_cycles;
		} else if (global_phase mod 2 = 1) {
			next_decision_in_cycles <- yellow_len_cycles - yellow_cycles + min_all_red_cycles + min_green_cycles;
		} else {
			next_decision_in_cycles <- min_green_cycles - green_cycles mod min_green_cycles;
		}
	}

	reflex update_metrics {
		int n <- 0;
		int queue <- 0;
		int blocked <- 0;
		float weighted <- external_weighted_pending;
		float sum_wait <- 0.0;
		float max_wait <- 0.0;
		float sum_speed <- 0.0;
		loop v over: vehicle {
			n <- n + 1;
			if (v.speed < 1.0 #km / #h) { queue <- queue + 1; }
			if (v.current_road != nil and road(v.current_road).kind = "exit" and v.speed < 5.0 #km / #h and
				(v.location distance_to first(road(v.current_road).shape.points)) < 80.0 #m) {
				blocked <- blocked + 1;
			}
			weighted <- weighted + pcu(v.vclass) * (1.0 - min([1.0, max([0.0, v.speed / max([0.1, v.desired_mps])])]));
			sum_wait <- sum_wait + v.waiting_time;
			max_wait <- max([max_wait, v.waiting_time]);
			sum_speed <- sum_speed + v.speed;
		}
		current_queue_length <- queue;
		average_waiting_time <- n > 0 ? sum_wait / n : 0.0;
		max_waiting_time <- max_wait;
		average_speed <- n > 0 ? sum_speed / n * 3.6 : 0.0;
		average_travel_time <- total_vehicles_passed > 0 ? total_travel_time / total_vehicles_passed : 0.0;
		system_time_integral <- system_time_integral + (n + pending_count) * step;
		stopped_time_integral <- stopped_time_integral + queue * step;
		external_all_time_integral <- external_all_time_integral + pending_count * step;
		outgoing_block_integral <- outgoing_block_integral + blocked * step;
		weighted_delay_integral <- weighted_delay_integral + weighted * step;
	}

	reflex measure_front_row when: !python_controlled {
		ask approaches {
			int n <- front_row();
			if n > front_row_max[arm] { front_row_max[arm] <- n; }
		}
	}

	// State [4 slot E,N,W,S × 6 kênh × 20 ô dọc 8 m từ vạch dừng × 16 sublane, sublane 0 sát bó vỉa phải].
	// C0–C2: tỷ phần diện tích xe máy / ô tô / buýt; C3: tốc độ dọc /50 km/h; C4: vận tốc ngang lớn nhất kể từ
	// lần chụp trước (âm = sang trái, /5 m/s) — advanced_driving đổi sublane rời rạc nên mỗi lần đổi làn cho ±1;
	// C5: mặt nạ ô có mặt đường thật (theo num_lanes và chiều dài nhánh vào).
	action capture_spatial_state {
		if (spatial_capture_cycle = cycle) { return; }
		list<float> pixels <- list_with(7680, 0.0);
		list<float> moving <- list_with(1280, 0.0);
		list<float> incoming <- list_with(12, 0.0); // [slot * 3 + rẽ]: xe chậm dưới 5 km/h trên nhánh vào
		list<float> outgoing <- list_with(4, 0.0); // [slot]: xe chậm dưới 5 km/h trong 80 m đầu đường ra
		loop k from: 0 to: 3 {
			road r <- slot_approach[k];
			loop h from: 0 to: 19 {
				if (h * 8.0 < r.shape.perimeter) {
					loop w from: 0 to: min([15, r.num_lanes - 1]) {
						pixels[((k * 6 + 5) * 20 + h) * 16 + w] <- 1.0;
					}
				}
			}
		}
		loop v over: vehicle where (each.current_road != nil) {
			road r <- road(v.current_road);
			if (r.kind = "exit") {
				if (v.speed < 5.0 #km / #h and (v.location distance_to first(r.shape.points)) < 80.0 #m) {
					outgoing[arm_slot[r.arm]] <- outgoing[arm_slot[r.arm]] + 1.0;
				}
			} else if (r.kind = "approach") {
				int k <- v.slot;
				float lo <- v.location distance_to last(r.shape.points); // vị trí đầu xe tính từ vạch dừng
				float hi <- lo + v.vehicle_length;
				if (v.speed < 5.0 #km / #h and lo < 160.0 #m) {
					incoming[k * 3 + v.move_turn] <- incoming[k * 3 + v.move_turn] + 1.0;
				}
				int h0 <- max([0, int(floor(lo / 8.0))]);
				int h1 <- min([19, int(floor(hi / 8.0))]);
				int w0 <- max([0, v.lowest_lane]);
				int w1 <- min([15, v.lowest_lane + v.num_lanes_occupied - 1]);
				if (h0 <= h1 and w0 <= w1) {
					int channel <- v.vclass;
					float vlong <- min([1.0, max([0.0, v.speed / (50.0 #km / #h)])]);
					float vlat <- max([-1.0, min([1.0, -v.lat_peak / 5.0])]);
					loop h from: h0 to: h1 {
						float cover <- max([0.0, min([hi, (h + 1) * 8.0]) - max([lo, h * 8.0])]) / 8.0;
						loop w from: w0 to: w1 {
							int cell <- ((k * 6 + channel) * 20 + h) * 16 + w;
							int local <- (k * 20 + h) * 16 + w;
							pixels[cell] <- min([1.0, pixels[cell] + cover]);
							pixels[((k * 6 + 3) * 20 + h) * 16 + w] <- pixels[((k * 6 + 3) * 20 + h) * 16 + w] + cover * vlong;
							pixels[((k * 6 + 4) * 20 + h) * 16 + w] <- pixels[((k * 6 + 4) * 20 + h) * 16 + w] + cover * vlat;
							moving[local] <- moving[local] + cover;
						}
					}
				}
			}
		}
		loop k from: 0 to: 3 {
			loop h from: 0 to: 19 {
				loop w from: 0 to: 15 {
					int local <- (k * 20 + h) * 16 + w;
					if (moving[local] > 0.0) {
						pixels[((k * 6 + 3) * 20 + h) * 16 + w] <- pixels[((k * 6 + 3) * 20 + h) * 16 + w] / moving[local];
						pixels[((k * 6 + 4) * 20 + h) * 16 + w] <- pixels[((k * 6 + 4) * 20 + h) * 16 + w] / moving[local];
					}
				}
			}
		}
		// Max Pressure: mỗi hướng được pha phục vụ cộng (hàng chờ vào − hàng chờ ở đúng nhánh ra của nó)
		loop a from: 0 to: 3 {
			list<int> slots <- a < 2 ? [1, 3] : [0, 2];
			list<int> turns <- a mod 2 = 0 ? [0, 2] : [1];
			float p <- 0.0;
			loop k over: slots {
				loop t over: turns {
					p <- p + incoming[k * 3 + t] - outgoing[exit_slot_of[k * 3 + t]];
				}
			}
			spatial_pressure[a] <- p;
		}
		spatial_pack <- "" + pixels;
		ask vehicle { lat_peak <- 0.0; }
		spatial_capture_cycle <- cycle;
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
	int vclass;        // 0 xe máy, 1 ô tô, 2 buýt
	int slot;          // nhánh vào (slot E, N, W, S)
	int move_turn;     // 0 thẳng, 1 trái, 2 phải
	float desired_mps; // tốc độ mong muốn (m/s), cũng là mốc của R4
	float spawn_time;
	float waiting_time <- 0.0;
	float lat_peak <- 0.0; // vận tốc ngang có dấu lớn nhất kể từ lần chụp state trước, dương = sang trái
	agent prev_road;
	int prev_lane <- -1;
	rgb color;

	init {
		color <- [rgb(255, 210, 60), rgb(80, 160, 255), rgb(230, 90, 90)][vclass];
		num_lanes_occupied <- [1, 2, 3][vclass];
		vehicle_length <- [1.9, 4.5, 10.0][vclass];
		max_speed <- desired_mps;
		max_acceleration <- [2.0, 2.5, 1.2][vclass];
		time_headway <- [0.6, 1.2, 1.5][vclass];
		min_safety_distance <- [0.3, 1.0, 1.5][vclass];
		lane_change_limit <- -1;
		linked_lane_limit <- 0;
		proba_use_linked_road <- 0.0;
		proba_respect_priorities <- 0.0;
		proba_block_node <- 0.0;
		proba_respect_stops <- move_turn = 0 ? [1.0, 0.0, 0.0] : (move_turn = 1 ? [0.0, 1.0, 0.0] : [0.0, 0.0, 1.0]);
		acc_gain_threshold <- 0.05;
		politeness_factor <- 0.1;
	}

	reflex choose_path when: final_target = nil {
		do compute_path graph: road_network target: dest;
	}

	reflex move when: final_target != nil {
		do drive;
		if final_target = nil {
			total_vehicles_passed <- total_vehicles_passed + 1;
			total_travel_time <- total_travel_time + time - spawn_time;
			do unregister;
			do die;
		} else {
			if (speed < 1.0 #km / #h) { waiting_time <- waiting_time + step; }
			if (current_road != nil) {
				if (current_road = prev_road and lowest_lane != prev_lane) {
					float v_lat <- (lowest_lane - prev_lane) * sublane_width / step;
					if (abs(v_lat) > abs(lat_peak)) { lat_peak <- v_lat; }
				}
				prev_road <- current_road;
				prev_lane <- lowest_lane;
			}
		}
	}

	// đường polyline nằm ở mép dải phân cách; sublane 0 sát bó vỉa bên phải
	point display_position {
		float dist <- (road(current_road).num_lanes - lowest_lane - mean(range(num_lanes_occupied - 1)) - 0.5) * sublane_width;
		return location + {cos(heading + 90) * dist, sin(heading + 90) * dist};
	}

	aspect default {
		if current_road != nil {
			draw rectangle(vehicle_length, [0.7, 1.7, 2.5][vclass]) at: display_position() rotate: heading color: color border: #black;
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
		monitor "Xe chờ vào mạng" value: pending_count;
		monitor "NE vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "NE_in")).num_lanes) + " / " + front_row_max["NE"];
		monitor "SE vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "SE_in")).num_lanes) + " / " + front_row_max["SE"];
		monitor "SW vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "SW_in")).num_lanes) + " / " + front_row_max["SW"];
		monitor "NW vào: sublane / hàng đầu max" value: string((road first_with (each.rid = "NW_in")).num_lanes) + " / " + front_row_max["NW"];
	}
}

// Experiment cho Python/gama-server (dqn_py/train.py --site lvl)
experiment dqn_server_experiment type: gui autorun: false {
	parameter "Demand CSV" var: demand_file_path;
	parameter "Python Controlled" var: python_controlled init: true;
	parameter "Seed" var: seed init: 1093.0;
	parameter "DQN_RNG_Seed" var: rng_seed init: 1093.0;
}
