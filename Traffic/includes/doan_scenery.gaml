/** Visual structures ported from the former DoAn project.
 * North/south coordinates are mirrored to Traffic's GAMA convention.
 * The network, signals and vehicles are supplied by the shared Traffic model.
 */
model doan_scenery

global {
	bool show_tunnel_cutaway <- false;
	// Keep signal state available when this scenery model is validated on its own.
	int global_phase <- 0;
	float phase_timer <- 0.0;
	int signal_display_seconds <- 0;
	float signal_yellow_seconds <- 3#s;
	list<float> signal_phase_schedule <- [];
	action init_doan_scenery {
		create doan_ground;
		create flyover_structure with: (location: {1000,1000,50});
		create tunnel_structure with: (location: {1000,1000,-60});
		create metro_structure with: (location: {1000,1000,95});
		loop y over: [167,433,700,867,1133,1300,1567,1833] {
			create bridge_pillar with: (location: {1000,y,0});
		}
		loop x over: [200,500,767,1233,1500,1800] {
			create metro_pillar with: (location: {x,1000,0});
		}
		create doan_metro with: (location: {133,995.5,96.5}, direction: 1.0);
		create doan_metro with: (location: {1867,1004.5,96.5}, direction: -1.0);
		create traffic_signal_post with: (post_id: 1, direction_axis: 0, location: {967,953}, heading: 180.0);
		create traffic_signal_post with: (post_id: 2, direction_axis: 0, location: {1033,1047}, heading: 0.0);
		create traffic_signal_post with: (post_id: 3, direction_axis: 1, location: {953,1033}, heading: 90.0);
		create traffic_signal_post with: (post_id: 4, direction_axis: 1, location: {1047,967}, heading: 270.0);
	}
}

species doan_ground {
	geometry portals <- (rectangle(160,16) at_location {840,1045}) +
		(rectangle(160,16) at_location {1160,1045}) +
		(rectangle(160,16) at_location {840,955}) +
		(rectangle(160,16) at_location {1160,955});
	// The cutaway keeps a roof beneath the north/south surface carriageway.
	geometry tunnel_cut <- (rectangle(170,16) at_location {845,1045}) +
		(rectangle(170,16) at_location {1155,1045}) +
		(rectangle(170,16) at_location {845,955}) +
		(rectangle(170,16) at_location {1155,955});
	aspect base {
		geometry opening <- show_tunnel_cutaway ? tunnel_cut : portals;
		draw ((square(2000) at_location {1000,1000}) - opening) at: {1000,1000,-0.5} color: rgb(15,20,30);

				// Trục Ngang Nguyễn Trãi (Đông - Tây): 4 LÀN XE MỖI CHIỀU (Rộng 60m)
				draw ((rectangle(2000,60) at_location {1000,1000}) - opening) depth: 0.6 color: rgb(35, 42, 55) border: rgb(0, 242, 254, 100);

				// Trục Dọc Khuất Duy Tiến - Nguyễn Xiển (Bắc - Nam): 4 LÀN XE MỖI CHIỀU (Rộng 60m)
			draw ((rectangle(60,2000) at_location {1000,1000}) - opening) depth: 0.6 color: rgb(35, 42, 55) border: rgb(0, 242, 254, 100);
			// Dedicated feeder lanes continue to the scene boundary on each side.
			loop feeder_y over: [955.0,1045.0] {
				loop feeder_x over: [385.0,1615.0] {
					draw box(750.0,8.0,0.6) at: {feeder_x,feeder_y,0.3}
						color: rgb(35,42,55) border: rgb(94,112,124);
				}
			}

				// VẠCH TIM ĐƯỜNG ĐÔI MÀU VÀNG NÉT LIỀN (DOUBLE YELLOW MEDIAN DIVIDERS)
				// Đường Nguyễn Trãi (Y = 1000.0)
				draw line([{0, 1000.6, 0.72}, {950, 1000.6, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{0, 999.4, 0.72}, {950, 999.4, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{1050, 1000.6, 0.72}, {2000, 1000.6, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{1050, 999.4, 0.72}, {2000, 999.4, 0.72}]) color: rgb(255, 215, 0) width: 2.0;

				// Đường Khuất Duy Tiến - Nguyễn Xiển (X = 1000.0)
				draw line([{999.4, 2000, 0.72}, {999.4, 1050, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{1000.6, 2000, 0.72}, {1000.6, 1050, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{999.4, 950, 0.72}, {999.4, 0, 0.72}]) color: rgb(255, 215, 0) width: 2.0;
				draw line([{1000.6, 950, 0.72}, {1000.6, 0, 0.72}]) color: rgb(255, 215, 0) width: 2.0;

				// 4 VẠCH SƠN DỪNG ĐÈN ĐỎ (STOP BARS) MÀU TRẮNG DÀY SÁT MÉP NGÃ TƯ (ĐÚNG NỬA ĐƯỜNG ĐI VÀO THEO RHT)
				// Nhánh Tây: vạch X=955, phần xe đi Đông.
				draw box(1.8, 25.0, 0.2) at: {955, 1015, 0.75} color: #white;
				// Nhánh Đông: vạch X=1045, phần xe đi Tây.
				draw box(1.8, 25.0, 0.2) at: {1045, 985, 0.75} color: #white;
				// Nhánh Bắc: vạch Y=955, phần xe đi Nam.
				draw box(25.0, 1.8, 0.2) at: {985, 955, 0.75} color: #white;
				// Nhánh Nam: vạch Y=1045, phần xe đi Bắc.
				draw box(25.0, 1.8, 0.2) at: {1015, 1045, 0.75} color: #white;

				// Subtle dashed guides follow the same cubic Bézier control points
				// as the four protected left-turn connectors in the road graph.
				list<point> turn_starts <- [{1040.5,998.0},{998.0,959.5},
					{959.5,1002.0},{1002.0,1040.5}];
				list<point> turn_ends <- [{1002.0,1040.5},{1040.5,1002.0},
					{1002.0,959.5},{959.5,998.0}];
				list<point> turn_controls_1 <- [{1015.5,998.0},{998.0,984.5},
					{984.5,1002.0},{1002.0,1015.5}];
				list<point> turn_controls_2 <- [{1002.0,1015.5},{1015.5,1002.0},
					{1002.0,984.5},{984.5,998.0}];
				loop turn_index from: 0 to: 3 {
					loop dash from: 0 to: 9 {
						float t0 <- dash / 10.0;
						float t1 <- t0 + 0.06;
						point a <- turn_starts[turn_index] * ((1-t0)^3) +
							turn_controls_1[turn_index] * (3*(1-t0)^2*t0) +
							turn_controls_2[turn_index] * (3*(1-t0)*t0*t0) +
							turn_ends[turn_index] * (t0^3);
						point b <- turn_starts[turn_index] * ((1-t1)^3) +
							turn_controls_1[turn_index] * (3*(1-t1)^2*t1) +
							turn_controls_2[turn_index] * (3*(1-t1)*t1*t1) +
							turn_ends[turn_index] * (t1^3);
						draw line([a + {0,0,0.95},b + {0,0,0.95}])
							color: rgb(225,225,210,125) width: 1.2;
					}
				}

				// (Đã bỏ vẽ vạch qua đường cho người đi bộ theo yêu cầu của người dùng)

				// 4 NHÁNH RẼ PHẢI ƯU TIÊN 2 LÀN RIÊNG BIỆT TẠI 4 GÓC PHẦN TƯ (RHT VIỆT NAM)
				// Góc Tây-Nam (Rẽ từ Nguyễn Trãi đi Đông sang Nguyễn Xiển đi Nam)
				draw line([{935, 1026, 0.6}, {974, 1065, 0.6}]) color: rgb(35, 42, 55) width: 22.0;
				draw line([{935, 1026, 0.8}, {974, 1065, 0.8}]) color: #white width: 2.0;
				draw line([{938, 1029, 0.85}, {971, 1062, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;
				draw line([{932, 1023, 0.85}, {977, 1068, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;

				// Góc Tây-Bắc (Rẽ từ Khuất Duy Tiến đi Nam sang Nguyễn Trãi đi Tây)
				draw line([{974, 935, 0.6}, {935, 974, 0.6}]) color: rgb(35, 42, 55) width: 22.0;
				draw line([{974, 935, 0.8}, {935, 974, 0.8}]) color: #white width: 2.0;
				draw line([{971, 938, 0.85}, {938, 971, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;
				draw line([{977, 932, 0.85}, {932, 977, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;

				// Góc Đông-Bắc (Rẽ từ Nguyễn Trãi đi Tây sang Khuất Duy Tiến đi Bắc)
				draw line([{1065, 974, 0.6}, {1026, 935, 0.6}]) color: rgb(35, 42, 55) width: 22.0;
				draw line([{1065, 974, 0.8}, {1026, 935, 0.8}]) color: #white width: 2.0;
				draw line([{1062, 971, 0.85}, {1029, 938, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;
				draw line([{1068, 977, 0.85}, {1023, 932, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;

				// Góc Đông-Nam (Rẽ từ Nguyễn Xiển đi Bắc sang Nguyễn Trãi đi Đông)
				draw line([{1026, 1065, 0.6}, {1065, 1026, 0.6}]) color: rgb(35, 42, 55) width: 22.0;
				draw line([{1026, 1065, 0.8}, {1065, 1026, 0.8}]) color: #white width: 2.0;
				draw line([{1029, 1062, 0.85}, {1062, 1029, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;
				draw line([{1023, 1068, 0.85}, {1068, 1023, 0.85}]) color: rgb(255, 255, 255, 160) width: 1.0;

				// 4 VÒNG QUAY ĐẦU CHỮ U VÀNG (ĐẶT NGAY TRƯỚC VẠCH DỪNG 955 & 1045)
				// 1. U-Turn Bắc (Đón từ Tây X=995 vòng sang Đông X=1005 đi ra hướng Bắc)
				draw line([{995, 930, 0.72}, {995, 940, 0.72}, {1005, 940, 0.72}, {1005, 930, 0.72}]) color: rgb(255, 215, 0) width: 4.0;

				// 2. U-Turn Nam (Đón từ Đông X=1005 vòng sang Tây X=995 đi ra hướng Nam)
				draw line([{1005, 1070, 0.72}, {1005, 1060, 0.72}, {995, 1060, 0.72}, {995, 1070, 0.72}]) color: rgb(255, 215, 0) width: 4.0;

				// 3. U-Turn Tây (Đón từ Nam Y=995 vòng sang Bắc Y=1005 đi ra hướng Tây)
				draw line([{930, 1005, 0.72}, {940, 1005, 0.72}, {940, 995, 0.72}, {930, 995, 0.72}]) color: rgb(255, 215, 0) width: 4.0;

				// 4. U-Turn Đông (Đón từ Bắc Y=1005 vòng sang Nam Y=995 đi ra hướng Đông)
				draw line([{1070, 995, 0.72}, {1060, 995, 0.72}, {1060, 1005, 0.72}, {1070, 1005, 0.72}]) color: rgb(255, 215, 0) width: 4.0;

				// VẠCH PHÂN LÀN TRẮNG NÉT ĐỨT (LÀN ĐƯỜNG NGUYỄN TRÃI)
				loop y_off over: [977.0, 984.0, 991.0, 1009.0, 1016.0, 1023.0] {
					draw line([{0.0, y_off, 0.7}, {2000.0, y_off, 0.7}]) color: rgb(255, 255, 255, 160) width: 1.5;
				}

				// VẠCH PHÂN LÀN TRẮNG NÉT ĐỨT (LÀN ĐƯỜNG KHUẤT DUY TIẾN - NGUYỄN XIỂN)
				loop x_off over: [977.0, 984.0, 991.0, 1009.0, 1016.0, 1023.0] {
					draw line([{x_off, 0.0, 0.7}, {x_off, 2000.0, 0.7}]) color: rgb(255, 255, 255, 160) width: 1.5;
				}

				// MŨI TÊN CHỈ HƯỚNG TRÊN MẶT ĐƯỜNG (LÀN VÀO HƯỚNG VÀO NGÃ TƯ, LÀN RA HƯỚNG RA KHỎI NGÃ TƯ)
				// 1. Nhánh Tây (Nguyễn Trãi): Nam đi Đông (vào), Bắc đi Tây (ra khỏi ngã tư)
				draw line([{880, 1015, 0.72}, {900, 1015, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Vào
				draw line([{900, 985, 0.72}, {880, 985, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Ra khỏi ngã tư
				// 2. Nhánh Đông (Nguyễn Trãi): Bắc đi Tây (vào), Nam đi Đông (ra khỏi ngã tư)
				draw line([{1120, 985, 0.72}, {1100, 985, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Vào
				draw line([{1100, 1015, 0.72}, {1120, 1015, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Ra khỏi ngã tư
				// 3. Nhánh Bắc (Khuất Duy Tiến): Tây đi Nam (vào), Đông đi Bắc (ra khỏi ngã tư)
				draw line([{985, 880, 0.72}, {985, 900, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Vào
				draw line([{1015, 900, 0.72}, {1015, 880, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Ra khỏi ngã tư
				// 4. Nhánh Nam (Nguyễn Xiển): Đông đi Bắc (vào), Tây đi Nam (ra khỏi ngã tư)
				draw line([{1015, 1120, 0.72}, {1015, 1100, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Vào
				draw line([{985, 1100, 0.72}, {985, 1120, 0.72}]) color: rgb(255, 255, 255, 200) width: 2.0; // Ra khỏi ngã tư

	}
}

species bridge_pillar {
	float pillar_h <- 49.0;

	aspect default {
	// 1 Trụ bê tông đơn hình trụ tròn đặt chính giữa
		draw cylinder(4.5, pillar_h) at: {location.x, location.y, 0.0} color: rgb(90, 100, 115) border: rgb(180, 195, 215);
		// Xà mũ đỡ ngang dạng chữ T đỡ dưới đáy dầm cầu vượt
		draw box(28.0, 8.0, 1.0) at: {location.x, location.y, pillar_h} color: rgb(110, 120, 135) border: #white;
	}

}

species metro_pillar {

	aspect default {
	// Trụ bê tông cao vút chạm đất Z=0m vươn lên Z=94m đỡ dầm ray Metro Z=95m
		draw cylinder(4.5, 94.0) at: {location.x, location.y, 0.0} color: rgb(120, 135, 150) border: rgb(200, 215, 230);
		// Xà đỡ ngang (Cap) nằm ngay dưới đáy dầm đường sắt Metro (Z=94m -> 95m)
		draw box(12.0, 26.0, 1.0) at: {location.x, location.y, 94.0} color: rgb(130, 145, 160) border: #white;
	}

}

// =============================================================================
// SPECIES 2: CẦU VƯỢT VÀNH ĐAI 3 (KẾT NỐI TỪ MẶT ĐẤT QUA DỐC LÊN/XUỐNG VÀ NHỊP CHÍNH Z = +50m)
// =============================================================================
// SPECIES 2: CẦU VƯỢT VÀNH ĐAI 3 (CÁC DỐC RAM XA NGÃ TƯ GẤP 3 LẦN, DẦM CHÍNH DÀI 3000m, Z = +50m)
// =============================================================================
species flyover_structure {

	aspect default {
	// 1. DẦM CẦU CẠN CHÍNH VÀNH ĐAI 3 - 2000m (scale 2/3), Rộng 24m, Z=50m
		draw box(24.0, 2000.0, 1.8) at: {1000, 1000, 50} color: rgb(35, 42, 55) border: rgb(0, 242, 254, 180);
		draw box(1.8, 2000.0, 1.0) at: {1000, 1000, 51} color: rgb(180, 190, 205);
		draw box(1.0, 2000.0, 2.0) at: {987.5, 1000, 51.2} color: rgb(255, 60, 100, 220);
		draw box(1.0, 2000.0, 2.0) at: {1012.5, 1000, 51.2} color: rgb(255, 60, 100, 220);
		draw box(0.35, 2000.0, 0.1) at: {996, 1000, 52} color: #white;
		draw box(0.35, 2000.0, 0.1) at: {1004, 1000, 52} color: #white;

		// 2. NHÁNH RAM LÊN PHÍA BẮC (heading 180 đi Nam, bên Tây X < 1000) - chân Y=1520, đỉnh Y=1360
		point n_on_bL <- {985, 480, 1.5};
		point n_on_bR <- {991, 480, 1.5};
		point n_on_tR <- {997, 640, 50};
		point n_on_tL <- {992, 640, 50};
		draw polygon([n_on_bL, n_on_bR, n_on_tR, n_on_tL]) color: rgb(35, 42, 55) border: rgb(0, 242, 254, 140);
		draw polygon([n_on_bL - {0, 0, 1.4}, n_on_bR - {0, 0, 1.4}, n_on_tR - {0, 0, 1.4}, n_on_tL - {0, 0, 1.4}]) color: rgb(25, 30, 42);
		draw polygon([n_on_bL, n_on_tL, n_on_tL - {0, 0, 1.4}, n_on_bL - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([n_on_bR, n_on_tR, n_on_tR - {0, 0, 1.4}, n_on_bR - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([n_on_bL, n_on_tL, n_on_tL + {0, 0, 1.2}, n_on_bL + {0, 0, 1.2}]) color: rgb(0, 242, 254, 220);
		draw line([{988, 480, 1.6}, {995, 640, 50.1}]) color: #white width: 2.0;

		// 3. NHÁNH RAM XUỐNG PHÍA BẮC (heading 0 đi Bắc, bên Đông X > 1000) - đỉnh Y=1360, chân Y=1520
		point n_off_tL <- {1003, 640, 50};
		point n_off_tR <- {1008, 640, 50};
		point n_off_bR <- {1015, 480, 1.5};
		point n_off_bL <- {1009, 480, 1.5};
		draw polygon([n_off_tL, n_off_tR, n_off_bR, n_off_bL]) color: rgb(35, 42, 55) border: rgb(0, 242, 254, 140);
		draw polygon([n_off_tL - {0, 0, 1.4}, n_off_tR - {0, 0, 1.4}, n_off_bR - {0, 0, 1.4}, n_off_bL - {0, 0, 1.4}]) color: rgb(25, 30, 42);
		draw polygon([n_off_tL, n_off_bL, n_off_bL - {0, 0, 1.4}, n_off_tL - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([n_off_tR, n_off_bR, n_off_bR - {0, 0, 1.4}, n_off_tR - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([n_off_tR, n_off_bR, n_off_bR + {0, 0, 1.2}, n_off_tR + {0, 0, 1.2}]) color: rgb(255, 200, 0, 220);
		draw line([{1005, 640, 50.1}, {1012, 480, 1.6}]) color: #white width: 2.0;

		// 4. NHÁNH RAM LÊN PHÍA NAM (heading 0 đi Bắc, bên Đông X > 1000) - chân Y=480, đỉnh Y=640
		point s_on_bL <- {1009, 1520, 1.5};
		point s_on_bR <- {1015, 1520, 1.5};
		point s_on_tR <- {1008, 1360, 50};
		point s_on_tL <- {1003, 1360, 50};
		draw polygon([s_on_bL, s_on_bR, s_on_tR, s_on_tL]) color: rgb(35, 42, 55) border: rgb(0, 242, 254, 140);
		draw polygon([s_on_bL - {0, 0, 1.4}, s_on_bR - {0, 0, 1.4}, s_on_tR - {0, 0, 1.4}, s_on_tL - {0, 0, 1.4}]) color: rgb(25, 30, 42);
		draw polygon([s_on_bL, s_on_tL, s_on_tL - {0, 0, 1.4}, s_on_bL - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([s_on_bR, s_on_tR, s_on_tR - {0, 0, 1.4}, s_on_bR - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([s_on_bR, s_on_tR, s_on_tR + {0, 0, 1.2}, s_on_bR + {0, 0, 1.2}]) color: rgb(0, 242, 254, 220);
		draw line([{1012, 1520, 1.6}, {1005, 1360, 50.1}]) color: #white width: 2.0;

		// 5. NHÁNH RAM XUỐNG PHÍA NAM (heading 180 đi Nam, bên Tây X < 1000) - đỉnh Y=640, chân Y=480
		point s_off_tL <- {992, 1360, 50};
		point s_off_tR <- {997, 1360, 50};
		point s_off_bR <- {991, 1520, 1.5};
		point s_off_bL <- {985, 1520, 1.5};
		draw polygon([s_off_tL, s_off_tR, s_off_bR, s_off_bL]) color: rgb(35, 42, 55) border: rgb(0, 242, 254, 140);
		draw polygon([s_off_tL - {0, 0, 1.4}, s_off_tR - {0, 0, 1.4}, s_off_bR - {0, 0, 1.4}, s_off_bL - {0, 0, 1.4}]) color: rgb(25, 30, 42);
		draw polygon([s_off_tL, s_off_bL, s_off_bL - {0, 0, 1.4}, s_off_tL - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([s_off_tR, s_off_bR, s_off_bR - {0, 0, 1.4}, s_off_tR - {0, 0, 1.4}]) color: rgb(30, 36, 48);
		draw polygon([s_off_tL, s_off_bL, s_off_bL + {0, 0, 1.2}, s_off_tL + {0, 0, 1.2}]) color: rgb(255, 200, 0, 220);
		draw line([{995, 1360, 50.1}, {988, 1520, 1.6}]) color: #white width: 2.0;
	}

}

// =============================================================================
// SPECIES 3: HẦM CHUI NGUYỄN TRÃI
// =============================================================================
species tunnel_structure {

	aspect default {
		// Each direction has its own trench beyond the outer surface lanes.
		loop tunnel_y over: [955.0,1045.0] {
			float low_y <- tunnel_y - 8.0;
			float high_y <- tunnel_y + 8.0;
			draw polygon([{760,low_y,0},{920,low_y,-60},{920,high_y,-60},{760,high_y,0}])
				color: rgb(43,49,57) border: rgb(129,137,143);
			draw box(160.0,16.0,1.5) at: {1000,tunnel_y,-60}
				color: rgb(39,45,52) border: rgb(129,137,143);
			draw polygon([{1080,low_y,-60},{1240,low_y,0},{1240,high_y,0},{1080,high_y,-60}])
				color: rgb(43,49,57) border: rgb(129,137,143);
			loop edge_y over: [low_y,high_y] {
				draw polygon([{760,edge_y,0},{920,edge_y,-60},{920,edge_y,-53},{760,edge_y,7}])
					color: rgb(104,112,119) border: rgb(173,179,181);
				draw polygon([{1080,edge_y,-60},{1240,edge_y,0},{1240,edge_y,7},{1080,edge_y,-53}])
					color: rgb(104,112,119) border: rgb(173,179,181);
				draw box(160.0,1.5,7.0) at: {1000,edge_y,-56.5} color: rgb(86,95,103);
			}
			draw line([{760,tunnel_y,0.9},{920,tunnel_y,-59.1},
				{1080,tunnel_y,-59.1},{1240,tunnel_y,0.9}])
				color: rgb(235,238,235,185) width: 1.2;
			loop portal_x over: [760.0,1240.0] {
				loop wall_y over: [low_y,high_y] {
					draw box(2.8,3.2,8.0) at: {portal_x,wall_y,4.0}
						color: rgb(145,150,151) border: rgb(208,211,210);
				}
				draw box(3.2,19.0,2.0) at: {portal_x,tunnel_y,8.0}
					color: rgb(145,150,151) border: rgb(208,211,210);
			}
		}
	}

}

// =============================================================================
// SPECIES 4: ĐƯỜNG SẮT TRÊN CAO & NHÀ GA METRO CÁT LINH - HÀ ĐÔNG
// =============================================================================
species metro_structure {

	aspect default {
	// METRO - scale 2/3: dài 2000m, tâm {1000, 1000, 95}
		draw box(2000.0, 18.0, 1.5) at: location color: rgb(30, 40, 55) border: rgb(0, 230, 118, 200);
		draw box(2000.0, 0.8, 0.4) at: location + {0, 4.5, 0.9} color: #cyan;
		draw box(2000.0, 0.8, 0.4) at: location + {0, -4.5, 0.9} color: #cyan;
		// Nhà ga: X=1560 (2340*2/3), dài 133m
		draw box(133.0, 30.0, 2.5) at: {1560, 1000, 96.2} color: rgb(220, 210, 180) border: rgb(255, 220, 100);
		draw box(133.0, 32.0, 4.0) at: {1560, 1000, 100} color: rgb(240, 230, 190, 220) border: #white;
	}

}

// =============================================================================
// SPECIES 5: CỘT ĐÈN TÍN HIỆU GIAO THÔNG 3D TẠI MẶT ĐẤT (Z = 0m)
// =============================================================================

species doan_metro {
	float direction <- 1.0;
	float train_speed <- 16.0;
	reflex move_train {
		location <- location + {direction * train_speed * step,0,0};
		if (location.x > 1990) { location <- {10,location.y,location.z}; }
		if (location.x < 10) { location <- {1990,location.y,location.z}; }
	}
	aspect base {
		draw box(75,5,4.5) at: location color: rgb(0,230,118) border: #white;
		draw box(70,4.5,2.5) at: location + {0,0,3} color: #cyan;
	}
}

// =========================================================================
// LOÀI TÁC TỬ: TRAFFIC SIGNAL POST (ĐÈN THẲNG VÀ RẼ TRÁI RIÊNG)
// =========================================================================
species traffic_signal_post {
	int post_id;
	int direction_axis; // 0: NS, 1: EW
	float heading <- 0.0;

	// movement 0: straight; movement 1: protected left turn.
	rgb get_active_light(int movement) {
		int green_phase <- direction_axis = 0 ? (movement = 0 ? 0 : 2) :
			(movement = 0 ? 4 : 6);
		if (global_phase = green_phase) { return #lime; }
		if (global_phase = green_phase + 1 and phase_timer < signal_yellow_seconds) { return #yellow; }
		return #red;
	}

	int red_wait_seconds(int movement) {
		if (length(signal_phase_schedule) != 8) { return -1; }
		int green_phase <- direction_axis = 0 ? (movement = 0 ? 0 : 2) :
			(movement = 0 ? 4 : 6);
		float remaining <- max([0.0, signal_phase_schedule[global_phase] - phase_timer]);
		int next_phase <- (global_phase + 1) mod 8;
		loop i from: 0 to: 7 {
			if (next_phase != green_phase) {
				remaining <- remaining + signal_phase_schedule[next_phase];
				next_phase <- (next_phase + 1) mod 8;
			}
		}
		return min([99,int(remaining / (1#s) + 0.999)]);
	}

	aspect base {
		draw circle(1.0) at: location color: rgb(56, 66, 80) border: #black;
		// Keep the two heads in a fixed screen order at every approach:
		// protected left on the left, through on the right.
		point board_center <- location;
		if (post_id = 1) { board_center <- location + {7.0, -10.0}; }
		else if (post_id = 2) { board_center <- location + {-7.0, -4.0}; }
		else if (post_id = 3) { board_center <- location + {-23.0, 8.0}; }
		else { board_center <- location + {23.0, -9.0}; }
		draw line([location, board_center]) color: rgb(90, 103, 120);
		draw line([board_center + {-6.3, 0.0}, board_center + {6.3, 0.0}])
			color: rgb(90, 103, 120);
		loop movement over: [0, 1] {
			float side <- movement = 1 ? -6.3 : 6.3;
			rgb movement_color <- movement = 0 ? rgb(93, 204, 252) : rgb(255, 194, 86);
			point box_loc <- board_center + {side, 0.0};
			draw rectangle(3.0, 7.2) at: box_loc color: rgb(15, 20, 29)
				border: movement_color;
			rgb active_c <- get_active_light(movement);
			point red_pt <- box_loc + {0.0, -2.2};
			point yel_pt <- box_loc;
			point grn_pt <- box_loc + {0.0, 2.2};
			if (active_c = #red) { draw circle(1.15) at: red_pt color: rgb(255, 60, 60, 65); }
			if (active_c = #yellow) { draw circle(1.15) at: yel_pt color: rgb(255, 205, 50, 65); }
			if (active_c = #lime) { draw circle(1.15) at: grn_pt color: rgb(50, 245, 125, 65); }
			draw circle(active_c = #red ? 0.85 : 0.65) at: red_pt
				color: (active_c = #red ? rgb(255, 65, 65) : rgb(72, 28, 31)) border: #black;
			draw circle(active_c = #yellow ? 0.85 : 0.65) at: yel_pt
				color: (active_c = #yellow ? rgb(255, 208, 42) : rgb(76, 64, 29)) border: #black;
			draw circle(active_c = #lime ? 0.85 : 0.65) at: grn_pt
				color: (active_c = #lime ? rgb(48, 239, 113) : rgb(23, 72, 46)) border: #black;
			point timer_box <- box_loc + {0.0, 6.0};
			draw rectangle(3.5, 2.3) at: timer_box color: rgb(12, 16, 24)
				border: rgb(100, 114, 133);
			int head_seconds <- active_c = #red ? red_wait_seconds(movement) : signal_display_seconds;
			string shown_time <- head_seconds < 0 ? "-" : "" + head_seconds;
			draw shown_time at: timer_box - {0.8, -0.45} color: active_c
				font: font("Helvetica", 12, #bold);
		}
	}

	aspect doan_3d {
		// One mast carries separate protected-left and through heads over the approach.
		float arm_x <- direction_axis = 0 ? (location.x < 1000 ? 20.0 : -20.0) : 0.0;
		float arm_y <- direction_axis = 1 ? (location.y < 1000 ? 20.0 : -20.0) : 0.0;
		float arm_sign <- direction_axis = 0 ? (location.x < 1000 ? 1.0 : -1.0) :
			(location.y < 1000 ? 1.0 : -1.0);
		draw cylinder(1.0, 15.0) at: location + {0,0,7.5}
			color: rgb(105,115,124) border: rgb(140,151,160);
		draw box(direction_axis = 0 ? 20.0 : 1.0,
			direction_axis = 1 ? 20.0 : 1.0, 0.9)
			at: location + {arm_x / 2.0, arm_y / 2.0, 14.2}
			color: rgb(105,115,124);
		loop movement over: [0,1] {
			// The left-turn head sits nearer the centreline; both face approaching cars.
			float lateral <- arm_sign * (movement = 1 ? 9.5 : -9.5);
			point head <- location + {arm_x + (direction_axis = 0 ? lateral : 0.0),
				arm_y + (direction_axis = 1 ? lateral : 0.0), 15.3};
			draw box(direction_axis = 0 ? 17.0 : 2.7,
				direction_axis = 1 ? 17.0 : 2.7, 4.5)
				at: head color: rgb(20,24,27) border: rgb(80,89,95);
			// Raised countdown housing is unobstructed in the default oblique view.
			draw box(direction_axis = 0 ? 0.8 : 2.7,
				direction_axis = 1 ? 0.8 : 2.7, 4.2)
				at: head + {0,0,3.8} color: rgb(88,97,104);
			draw box(direction_axis = 0 ? 7.4 : 2.7,
				direction_axis = 1 ? 7.4 : 2.7, 6.4)
				at: head + {0,0,6.5} color: rgb(9,13,17) border: rgb(138,148,154);
			rgb active_c <- get_active_light(movement);
			// Opposite approaches share one phase, so both faces remain readable in 3D.
			loop face over: [-1.0,1.0] {
				float visual_sign <- direction_axis = 0 ? -face : face;
				float face_depth <- face * 1.5;
				// Red, amber, green are fixed left to right on a dark housing.
				loop lamp over: [0,1,2] {
					float lamp_u <- visual_sign * (-6.3 + lamp * 3.4);
					point lens <- head + (direction_axis = 0 ?
						{lamp_u,face_depth,0.0} : {face_depth,lamp_u,0.0});
					rgb lens_color <- lamp = 0 ?
						(active_c = #red ? rgb(255,46,37) : rgb(75,22,20)) :
						(lamp = 1 ? (active_c = #yellow ? rgb(255,192,35) : rgb(72,54,18)) :
						(active_c = #lime ? rgb(36,228,85) : rgb(18,64,33)));
					draw sphere(1.55) at: lens color: rgb(5,7,9);
					// In GAMA sphere() uses a radius; offset the lens beyond its bezel.
					draw sphere(1.25) at: lens + (direction_axis = 0 ?
						{0.0,face * 1.05,0.0} : {face * 1.05,0.0,0.0})
						color: lens_color;
				}
				// The timer uses the opposite horizontal orientation from the lamps.
				// Apply it to both digit order and each seven-segment glyph.
				int head_seconds <- active_c = #red ? red_wait_seconds(movement) : signal_display_seconds;
				if (head_seconds >= 0) {
					int seconds <- min([99,max([0,head_seconds])]);
					float digit_sign <- -visual_sign;
					loop digit_index over: [0,1] {
						int digit <- digit_index = 0 ? int(seconds / 10) : seconds mod 10;
						float digit_u <- digit_sign * (digit_index = 0 ? -1.45 : 1.45);
						loop segment over: [0,1,2,3,4,5,6] {
							bool lit <- (segment = 0 and digit != 1 and digit != 4) or
								(segment = 1 and digit != 5 and digit != 6) or
								(segment = 2 and digit != 2) or
								(segment = 3 and digit != 1 and digit != 4 and digit != 7) or
								(segment = 4 and (digit = 0 or digit = 2 or digit = 6 or digit = 8)) or
								(segment = 5 and (digit = 0 or digit = 4 or digit = 5 or digit = 6 or digit = 8 or digit = 9)) or
								(segment = 6 and digit != 0 and digit != 1 and digit != 7);
							if (lit) {
								float seg_u <- digit_u + digit_sign * ((segment = 1 or segment = 2) ? 0.78 :
									((segment = 4 or segment = 5) ? -0.78 : 0.0));
								float seg_z <- segment = 0 ? 2.15 : (segment = 3 ? -2.15 :
									(segment = 6 ? 0.0 : ((segment = 1 or segment = 5) ? 1.08 : -1.08)));
								float seg_width <- (segment = 0 or segment = 3 or segment = 6) ? 1.52 : 0.28;
								float seg_height <- (segment = 0 or segment = 3 or segment = 6) ? 0.28 : 1.75;
								point seg_pos <- head + (direction_axis = 0 ?
									{seg_u,face * 1.72,6.5 + seg_z} : {face * 1.72,seg_u,6.5 + seg_z});
								draw box(direction_axis = 0 ? seg_width : 0.16,
									direction_axis = 1 ? seg_width : 0.16, seg_height)
									at: seg_pos color: active_c;
							}
						}
					}
				}
			}
		}
	}
}
