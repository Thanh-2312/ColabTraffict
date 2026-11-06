# Review source GAMA–3DQN — 05/11/2026

## Kết luận

Pipeline **3DQN bốn pha với DTSE 3×8×20** chạy được ở mức tích hợp ngắn: GAMA trả state, Python chọn action, CNN cập nhật trọng số và checkpoint được lưu. **Chưa thể kết luận hệ thống không còn bug hoặc đã sẵn sàng train đề tài mới.** State phân bố theo loại xe và vận tốc ngang, Rainbow DQN, bản lai Max Pressure và hình học nút Lê Văn Lương – Vành Đai 2.5 chưa được triển khai trong đường train hiện hành.

Phạm vi review: mã dự án trong `Traffic/`, `dqn_py/`, `scripts/`, README và đặc tả nghiên cứu. Hai repository tham khảo được lưu trong cây làm việc không thuộc phạm vi kiểm toán này.

## Phát hiện theo mức ưu tiên

### P0 — Chặn thí nghiệm nghiên cứu

1. **State đề xuất chưa tồn tại trong pipeline.** GAMA chỉ xuất occupancy, tốc độ dọc và tín hiệu theo `3×8×20` tại [intersection-dqn-python.gaml](../Traffic/models/intersection-dqn-python.gaml#L56); Python kiểm tra đúng 480 số tại [gama_env.py](../dqn_py/gama_env.py#L217), replay nén thành 3 mặt phẳng tại [three_dqn_agent.py](../dqn_py/three_dqn_agent.py#L12), và CNN nhận đúng 3 kênh tại [three_dqn_agent.py](../dqn_py/three_dqn_agent.py#L85). Không có occupancy theo loại, vị trí ngang, vận tốc ngang hay mặt nạ hình học. Không có learner Rainbow hoặc policy 3DQN + Max Pressure trong đường `train.py`. Vì vậy H1–H3 của đề xuất chưa thể kiểm định bằng mã hiện tại.

2. **Nút giao và nhu cầu chưa theo địa điểm nghiên cứu.** Mạng GAMA hiện được dựng bằng tọa độ cố định, cầu vượt và hầm trong [collision_avoidance.gaml](../Traffic/includes/collision_avoidance.gaml#L88). Lịch xe trong [demand.py](../dqn_py/demand.py#L14) dùng khoảng cách cố định 15/45/120 cycle, tỷ lệ loại xe 55/38/7 và tỷ lệ rẽ cố định. Chưa có hình học và lưu lượng theo giờ đo từ video tại Lê Văn Lương – Vành Đai 2.5. Kết quả train hiện tại chỉ mô tả mạng DoAn đang có.

### P1 — Có thể làm sai kết luận hoặc làm train không ổn định

3. **“Lách ngang” hiện là chuyển làn rời rạc cộng nội suy hiển thị.** Quy tắc làn đọc `lowest_lane` để xét khoảng trống tại [collision_avoidance.gaml](../Traffic/includes/collision_avoidance.gaml#L1078); [smooth_lateral_movement](../Traffic/includes/collision_avoidance.gaml#L1133) được ghi rõ là nội suy hiển thị, rồi `current_lateral_shift` đi vào [compute_position](../Traffic/includes/collision_avoidance.gaml#L1665). Nếu lấy đạo hàm `current_lateral_shift` làm C4, cần xác minh đó là vận tốc chuyển làn của hành vi mô phỏng, không chỉ chuyển động hình vẽ. Cần đối chiếu quỹ đạo, footprint và xung đột trong lúc đổi làn.

4. **Reward `reference` bất lợi cho xe có tốc độ mong muốn dưới 50 km/h.** [capture_dtse](../Traffic/models/intersection-dqn-python.gaml#L66) tính `1-(v/50)^2` cho mọi xe; nhưng [configure_vehicle](../Traffic/includes/collision_avoidance.gaml#L997) sinh xe máy khoảng 25–37, ô tô 30–45 và xe buýt 22–32 km/h. Một xe máy chạy tự do ở 30 km/h vẫn chịu mức delay 0,64. Điều này lẫn tốc độ thiết kế của loại xe với ùn tắc. Với nghiên cứu giao thông hỗn hợp, nên so thêm reward theo tốc độ mong muốn riêng từng xe như R4 của đề xuất.

5. **Reward và discount của `reference` chưa xử lý đồng nhất thời lượng action.** [gama_env.py](../dqn_py/gama_env.py#L278) chỉ lấy reward tại state sau quyết định, trong khi đổi pha có vàng/đỏ kéo dài và một action có thể dài hơn giữ xanh. [three_dqn_agent.py](../dqn_py/three_dqn_agent.py#L171) dùng `gamma` cố định cho `reference`; `queue_time` và `total_wait` lại dùng `gamma ** (seconds/5)`. Các action dài ngắn khác nhau vì thế được định giá trên hai thang thời gian khác nhau. Cần tích phân reward qua toàn bộ interval và dùng discount theo thời gian nếu muốn so chính sách công bằng theo thời gian thực.

6. **Chọn checkpoint mặc định chỉ nhìn hàng chờ trong mạng.** [train.py](../dqn_py/train.py#L292) cộng thời gian chờ ngoài mạng vào validation chỉ khi `reward_mode=total_wait`; mặc định `reference` bỏ phần đó. [fair_benchmark.py](../scripts/fair_benchmark.py#L495) cũng chọn checkpoint theo `queue_mean` trong mạng. Trong kịch bản nguồn xe bị chặn, policy có thể trông tốt vì xe còn đứng ngoài mạng. Cần chốt metric chọn checkpoint trên *toàn bộ nhu cầu* và báo cáo cả xe chưa vào hoặc chưa hoàn thành.

7. **Guard pha mặc định tắt, tài liệu nói guard hoạt động.** [intersection-dqn-python.gaml](../Traffic/models/intersection-dqn-python.gaml#L49) đặt `dqn_service_guard=false`; mask chỉ giới hạn tuổi xanh và chống bỏ đói khi guard bật tại [cùng file](../Traffic/models/intersection-dqn-python.gaml#L177). [README](../README.md#L67) lại mô tả giới hạn 60/120 giây như chính sách đang chạy. Đây có thể là lựa chọn để giữ 3DQN thuần theo bài báo, nhưng phải đặt chế độ rõ trong cấu hình thí nghiệm và mô tả đúng; nếu không, kết quả bị hiểu sai.

8. **Kịch bản đường ra tắc có nguy cơ giữ toàn đỏ không giới hạn.** [intersection-dqn-python.gaml](../Traffic/models/intersection-dqn-python.gaml#L193) chỉ mở xanh mới khi `signal_junction_clear()` đúng; [gama_env.py](../dqn_py/gama_env.py#L347) ném lỗi nếu không có quyết định mới trong 1.200 cycle. Chưa có kiểm tra tích hợp cho xe bị kẹt ở đường ra/connector trong kịch bản spillback, nên cần một bài audit liveness riêng. Đây là rủi ro logic cần thử, chưa phải lỗi đã quan sát.

### P2 — Chất lượng vận hành và khả năng tái lập

9. **Bộ unit test tổng hợp bị gãy import.** [test_learning_pipeline.py](../scripts/test_learning_pipeline.py#L13) import `scripts.benchmark_3dqn_vs_4`, nhưng file này đã bị xóa. Lệnh unit test đầy đủ dừng với `ModuleNotFoundError`. [README](../README.md#L98) cũng còn hướng dẫn script benchmark đã xóa và `run_doan_integration_suite.py` đã xóa. Cần khôi phục đường benchmark hợp lệ hoặc bỏ hướng dẫn/test cũ và thay bằng đường hiện hành.

10. **CLI cho phép cấu hình train không học được.** [train.py](../dqn_py/train.py#L73) chỉ yêu cầu horizon `>100`, nhưng quyết định đầu tiên ở cycle 100; horizon 101 cắt action trước state quyết định tiếp theo. [train.py](../dqn_py/train.py#L348) tăng `decisions` nhưng không lưu transition khi `bootstrap_valid=false`, nên có thể kết thúc với weights gần như ngẫu nhiên. `batch_size`, `buffer_size`, `eps_decay_steps`, `tau`, `gamma` cũng thiếu ràng buộc biên; ví dụ `eps_decay_steps=0` gây chia cho 0 khi giảm epsilon.

11. **Checkpoint mốc 1M/5M thiếu ở nhánh nhiều worker.** [train.py](../dqn_py/train.py#L356) chỉ lưu file tên mốc 1M/5M trong nhánh một worker; nhánh nhiều worker tại [cùng file](../dqn_py/train.py#L272) chỉ lưu checkpoint theo episode. README nói một lượt 5M có cả hai mốc, nhưng điều đó không đúng khi chạy 2 worker theo lệnh mẫu.

12. **Benchmark tốc độ GAMA không đo đường train thật.** [benchmark_gama_runtime.py](../scripts/benchmark_gama_runtime.py#L29) `step_cycles(horizon)` mà không gửi action khi GAMA yêu cầu quyết định. Tốc độ đó không phản ánh WebSocket, capture DTSE, chuyển pha và cập nhật mạng trong `train.py`. Dự kiến 1–2 tuần trên Colab chưa có số `decision/s` đo bằng pipeline đầy đủ.

## Những phần đã xác minh được

- 23 unit test Python liên quan tới demand, DQN, replay, mask, lịch GAMA và server manager: **OK, 1 skipped**. Lệnh gồm `dqn_py.test_demand`, `scripts.test_fair_benchmark`, `dqn_py.test_three_dqn_agent`, `dqn_py.test_four_phase_agents`, `dqn_py.test_gama_env_schedule`, `dqn_py.test_server_manager_cleanup`.
- Lệnh unit test đầy đủ thêm `scripts.test_learning_pipeline`: **1 lỗi import** như phát hiện 9.
- `scripts/run_test_suite.py`: **31/31 PASS** trên các trường hợp bộ điều khiển nền.
- `dqn_py/test_doan_server.py --horizon 4000`: giao thức GAMA–Python, seed lặp và bốn pha đều chạy, có 87 xe mặt đất và 65 xe bypass hoàn thành. Script gọi `env.step()` không truyền horizon nên kết thúc tại cycle 4068, cần lưu ý khi đọc kết quả.
- Train smoke `3DQN`, `total_wait`, 4 quyết định, warm-up 2, replay 16, batch 2: **hoàn tất**, có gradient update trên MPS, `best_weights.pt`, `checkpoint.pt` và `training_state.pt` được lưu.
- Audit `test_doan_integration.gaml` với fixed-time tới cycle 5999: `audit_errors=0`, `audit_red_entries=0`, `audit_overlaps=0` trong kịch bản tải của bài audit. Bài này **không** kiểm tra chính sách 3DQN và **không** đại diện cho tải cao hoặc hình học địa điểm nghiên cứu.

## Thứ tự sửa đề nghị

1. Chốt hình học và nhu cầu thực ở nút giao, cùng tiêu chí hiệu chỉnh hành vi xe máy/lách ngang từ video.
2. Xuất snapshot có loại xe, footprint, vị trí và chuyển động ngang; xây encoder 4×6×H×W và kiểm tra tính nhất quán GAMA ↔ Python.
3. Chốt một reward tích lũy theo thời gian và toàn bộ nhu cầu, cùng metric validation/test; giữ cố định khi so state và thuật toán.
4. Bổ sung audit giao thông tắc đường ra, overlap lúc đổi làn, mọi pha, nhiều seed và horizon dài trên chính model 3DQN.
5. Sửa bộ test gãy, kiểm tra tham số CLI, checkpoint nhiều worker; đo `decision/s` của pipeline đầy đủ trước khi cam kết thời lượng Colab.
