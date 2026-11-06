# Kiểm tra mức sẵn sàng trước khảo sát nút Lê Văn Lương – Vành Đai 2.5

Ngày kiểm tra: 05/11/2026. Phạm vi: mô phỏng GAMA, cấu hình nhu cầu xe và giao diện state/action của đường train 3DQN hiện có. Số liệu hình học và giao thông của nút nghiên cứu chưa được khảo sát, nên báo cáo này không xác nhận mô hình đã khớp thực địa.

## Kết luận

**Chưa thể thay nút nghiên cứu bằng cách chỉ sửa số sublane và vài con số.** Mã hiện tại là một mạng giao thông bốn nhánh hình học đối xứng, có cầu vượt, hầm, nhánh rẽ phải và quay đầu riêng. Nhiều quyết định về làn, tuyến, tín hiệu, quan sát và hình vẽ đã được gắn trực tiếp vào mã. Chỉ giảm `nb_lanes` có thể tạo chỉ số làn không hợp lệ, vì xe rẽ trái dùng làn 12 và quay đầu dùng làn 14.

Đường train **3DQN bốn pha, state 3×8×20** đã chạy qua bài smoke test GAMA–Python ở lượt kiểm tra source trước. Đó là bằng chứng nền tảng chạy được, chưa phải bằng chứng nút thật đã được dựng, hay state sáu kênh và vận tốc lách ngang của đề xuất đã được triển khai.

## Các phụ thuộc cần sửa sau khảo sát

| Thành phần | Hiện tại trong mã | Việc cần làm khi có dữ liệu thực địa |
|---|---|---|
| Mạng đường | `init_doan_network` tạo các nhánh E/N/W/S đối xứng, nút cách tâm 40,5 m, đầu tuyến cách 990 m; thêm cầu vượt, hầm, lối lên/xuống và nhánh rẽ/quay đầu tại các cự ly gắn cứng. `road_length` được khai báo nhưng không được dùng để dựng mạng. | Đo và dựng lại các hướng vào/ra, vạch dừng, đảo phân cách, làn rẽ, chiều dài đoạn mô phỏng và những tuyến khác mức thực sự có liên quan. |
| Sublane và loại xe | `nb_lanes=16`, `lane_width=1,75 m`; xe máy chiếm 1 sublane, ô tô/buýt chiếm 2. Làn thẳng 4–11, rẽ trái 12, quay đầu 14, rẽ phải 0–3; bypass dùng 9 hoặc 14. | Chọn độ rộng sublane và số slot **theo từng đoạn và từng hướng**; tính lại làn hợp lệ cho mỗi chuyển động và kiểm tra footprint xe. Không đổi `nb_lanes` riêng lẻ. |
| Tuyến đi | Mỗi hướng có đi thẳng, trái, phải, quay đầu; rẽ phải và quay đầu đi đường riêng, không chịu đèn. Nhu cầu ghép với 12 nguồn, trong đó 8 nguồn là cầu vượt/hầm. | Ghi rõ chuyển động được phép, vị trí nhập/tách làn, rẽ phải có đèn hay không, vị trí quay đầu và tuyến đường ra. Bỏ những nhánh không tồn tại, thêm tuyến thiếu. |
| Pha đèn/action | Action 0–3 tương ứng NS thẳng, NS trái, EW thẳng, EW trái. Đổi pha qua vàng 3 s và toàn đỏ ít nhất 2 s; giữ pha thêm 10 s. | Ghi chương trình pha thực tế, các pha bảo vệ/hỗn hợp, vàng, toàn đỏ, xanh tối thiểu, thứ tự xung đột. Nếu số pha hoặc nhóm chuyển động khác, phải sửa cả GAMA, action mask, đầu ra mạng và benchmark. |
| State | GAMA xuất 3×8×20 theo khoảng cách Euclid tới tâm nút; nhóm xe theo hướng và thẳng/trái, không có loại xe hay vận tốc ngang. | Xây state đề xuất 4×6×H×W cùng mặt nạ hình học; tính vị trí theo **quãng đường dọc tuyến từ vạch dừng**, đặc biệt nếu đường cong/lệch. Đồng bộ encoder GAMA–Python–CNN. |
| Nhu cầu xe | `demand.py` dùng chu kỳ cố định 15/45/120, tỷ lệ xe 55/38/7, rẽ 60/20/15/5 và nguồn cố định; không thay đổi theo giờ. | Tạo lịch vào từ đếm xe theo thời đoạn, hướng, loại xe và hướng rẽ; giữ cùng lịch/seed cho mọi phương pháp benchmark. |
| Hiển thị | `doan_scenery.gaml` vẽ làn/vạch dừng, cầu vượt, hầm và nhãn Nguyễn Trãi – Khuất Duy Tiến/Nguyễn Xiển bằng tọa độ cố định. | Dựng hình từ cùng dữ liệu hình học với mạng vật lý, hoặc tạm tắt scene cũ để không tạo ấn tượng sai về vị trí xe/vạch dừng. |

Nguồn chính: `Traffic/includes/collision_avoidance.gaml` (mạng đường, làn, xe), `Traffic/includes/doan_scenery.gaml` (cảnh), `Traffic/models/intersection-dqn-python.gaml` (state/action), `dqn_py/demand.py` (lịch xe).

## Rủi ro mô phỏng và train còn mở

1. Chuyển động ngang hiện dựa trên đổi `lowest_lane` rời rạc; `current_lateral_shift` là nội suy phục vụ hiển thị. Chưa thể coi đạo hàm của nó là vận tốc lách ngang thực được kiểm chứng từ video.
2. Reward `reference` chia tốc độ mọi xe cho 50 km/h dù tốc độ mong muốn được sinh theo loại xe thấp hơn. Một xe chạy tự do vẫn có thể bị tính là chậm. Reward này cũng lấy ở cuối bước quyết định, trong khi độ dài bước thay đổi khi đổi pha; xem review source trước đó.
3. Khi đổi pha, toàn đỏ chờ `signal_junction_clear()` mà không có giới hạn kết thúc trong GAMA. Chưa có audit riêng cho tình huống xe đứng trong nút hoặc đường ra bị chặn; Python có giới hạn chờ 1.200 cycle. Không thể khẳng định liveness trong spillback.
4. `dqn_service_guard` mặc định tắt; không nên coi giới hạn chờ pha là bảo đảm trong lượt train mặc định.
5. Bộ test Python tổng hợp còn lỗi import script benchmark đã xóa; state sáu kênh, Rainbow và 3DQN + Max Pressure chưa có trong pipeline train.

## Cần ghi nhận trong buổi khảo sát

1. **Bản đồ chuyển động:** ảnh/video từ trên cao hoặc từng góc; số làn và bề rộng từng hướng, chiều dài làn rẽ, vạch dừng, dải phân cách, lối rẽ phải, chỗ quay đầu, điểm nhập làn, vị trí đường ra tắc và các nhánh khác mức nếu có. Đo theo từng hướng, không chỉ một tổng số sublane.
2. **Đèn:** video trọn các chu kỳ tại từng khung giờ; thứ tự pha và nhóm xe được đi, xanh/vàng/đỏ toàn phần, rẽ trái bảo vệ hay đi chung, rẽ phải được phép khi đỏ hay không.
3. **Nhu cầu:** đếm xe vào theo hướng, loại và hướng rẽ trong các cửa sổ thời gian ngắn (gợi ý 5 hoặc 15 phút), gồm giờ cao điểm và giờ thường; ghi xe bị dồn ngoài vùng camera, hàng chờ cực đại và lưu lượng thoát.
4. **Hành vi xe:** một số quỹ đạo xe máy/ô tô có tọa độ và thời gian để đo tốc độ dọc/ngang, chen hàng, khoảng cách khi nhập khe, khoảng cách dừng và vận tốc qua nút. Ghi vị trí và tầm nhìn camera để hiệu chỉnh tọa độ ảnh sang mét.

## Điều kiện để gọi là sẵn sàng train trên nút này

- Mạng GAMA dựng từ số liệu khảo sát; mọi làn/đường rẽ tồn tại hợp lệ và hình vẽ khớp mạng vật lý.
- Cấu hình pha và action khớp chuyển động được phép; audit qua nhiều seed, tải thấp/cao, đổi pha, đường ra tắc: không có vượt đèn đỏ, chồng thân xe, mất xe, làn sai, kẹt vĩnh viễn.
- State sáu kênh của đề xuất được xuất đúng, có kiểm thử đối chiếu snapshot GAMA với tensor Python và quan sát lách ngang.
- Demand theo giờ được đối chiếu với video; cùng lịch demand được dùng cho các đối chứng; reward/discount/metric chọn checkpoint được chốt trước khi train dài.
- Một bài train ngắn với GAMA và checkpoint trên đúng môi trường dự định dùng (Colab CPU cho GAMA, GPU cho mạng) chạy qua reset, step, lưu và nạp lại checkpoint.

## Kiểm tra đã chạy

- Lượt review trước: 31/31 controller test đạt; GAMA–Python 3DQN chạy 4.000 cycle; train smoke 4 quyết định có cập nhật trọng số; audit fixed-time 6.000 cycle ở tải thấp không ghi nhận lỗi an toàn được theo dõi.
- Audit tải cao trước khảo sát: bản sao tạm của `test_doan_integration.gaml` với NS/EW mỗi 30 cycle, bypass mỗi 60 cycle, horizon 3.000 cycle, seed 5001 hoàn tất. Tại cycle 2999: `audit_errors=0`, `failed_route_count=0`, `audit_red_entries=0`, `audit_overlaps=0`, `audit_lane_errors=0`, `audit_phase_errors=0`, `audit_wrong_routes=0`; 101 xe mặt đất được sinh, 13 xe đã hoàn thành; 268 xe bypass được sinh, 32 xe đã hoàn thành. Mẫu này vẫn chủ yếu kiểm tra mạng hiện tại trong 300 giây mô phỏng, chưa bao phủ mọi điều kiện tắc đường ra.
- Audit bộ điều khiển 3DQN bằng chế độ heuristic fallback (`python_controlled=false`, không phải trọng số 3DQN đã train) với seed 5001, NS/EW mỗi 100 cycle, bypass mỗi 200 cycle, horizon 3.000 cycle: tại cycle 2999, `audit_errors=0`, `failed_route_count=0`, `audit_red_entries=0`, `audit_overlaps=0`, `audit_lane_errors=0`, `audit_phase_errors=0`, `audit_wrong_routes=0`; 77 xe mặt đất được sinh, 15 xe đã hoàn thành; 83 xe bypass được sinh, 22 xe đã hoàn thành. Lượt này kiểm tra nhánh đổi pha của controller và chuyển động xe, không kiểm định chất lượng policy học máy.

**Phạm vi của các audit:** đây là mạng hiện tại và lịch sinh xe nhân tạo; chúng không chứng minh mô hình phù hợp với nút Lê Văn Lương – Vành Đai 2.5 hoặc không còn mọi lỗi ở mọi điều kiện.
