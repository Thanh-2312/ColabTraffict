# Traffic-Light-ABM: Intelligent Traffic Signal Control

Hệ thống mô phỏng vi mô đa tác tử (Agent-Based Modeling) và điều khiển tín hiệu đèn giao thông thông minh trên nền tảng **GAMA Platform** kết hợp **PyTorch Deep Q-Network (DQN)**.

Dự án triển khai và đối sánh 4 thuật toán điều khiển đèn tín hiệu tại nút giao đô thị 4 nhánh:
1. **Fixed-Time**: Chu kỳ đèn cố định truyền thống.
2. **MaxPressure**: Thuật toán thích ứng dựa trên lý thuyết dòng xe & áp lực hàng đợi (Varaiya, 2013).
3. **Q-Learning**: Học tăng cường dạng bảng (Tabular Reinforcement Learning) nhúng trực tiếp trong GAML.
4. **Deep Q-Network (DQN)**: Học tăng cường sâu (Deep Reinforcement Learning) với PyTorch kết nối qua GAMA Server WebSocket.

---

## Cấu trúc thư mục

```
.
├── Traffic/                             # Mô hình mô phỏng GAMA
│   ├── .project                         # Cấu hình dự án GAMA / Eclipse
│   ├── includes/
│   │   ├── doan_scenery.gaml           # Cầu, hầm, metro và mặt đường
│   │   ├── surrogate_safety_measures.gaml # Chỉ số an toàn
│   │   └── collision_avoidance.gaml    # Đồ thị đường, xe và điều khiển di chuyển
│   ├── data/                           # Số liệu đếm xe gốc để hiệu chỉnh sau này
│   └── models/
│       ├── intersection-fixed-time.gaml # Mô hình Fixed-Time
│       ├── intersection-maxpressure.gaml# Mô hình MaxPressure
│       ├── intersection-qlearning.gaml  # Mô hình Q-Learning
│       ├── intersection-dqn-python.gaml # Mô hình DQN (kết nối GAMA Server)
│       ├── intersection-benchmark.gaml  # Lịch đèn và demand chung để đánh giá công bằng
│       ├── test_traffic_controllers.gaml# Kiểm thử bộ điều khiển
│       └── test_doan_integration.gaml # Kiểm thử mạng DoAn và hành vi xe
│
├── dqn_py/                              # Mã nguồn Python DQN & GAMA Server Client
│   ├── dqn_agent.py                     # Cài đặt mạng neural DQN (PyTorch)
│   ├── gama_env.py                      # Môi trường Gym-like giao tiếp qua WebSocket
│   ├── server_manager.py                # Quản lý tiến trình GAMA Headless/Server
│   ├── train.py                         # Huấn luyện DQN Agent
│   ├── evaluate.py                      # Đánh giá mô hình đã huấn luyện
│   ├── smoke_test.py                    # Kiểm tra kết nối nhanh
│   ├── requirements.txt                 # Thư viện Python yêu cầu
│   ├── setup_env.sh                     # Script khởi tạo môi trường venv
│   └── run/                             # Sinh khi huấn luyện, không lưu trong Git
│
├── seminar/                             # Slide seminar, phụ lục và mã nguồn LaTeX
└── scripts/                             # Scripts tự động hóa & Benchmark
    ├── fair_benchmark.py                # Train/validation/test với cùng demand và lịch pha
    ├── compare_4_models.py              # Chạy benchmark đối sánh cả 4 thuật toán
    ├── compare_traffic_control.py       # Chạy đối sánh Fixed-Time, MaxPressure, Q-Learning
    ├── plot_4_models.py                 # Vẽ đồ thị so sánh 6 tiêu chí hiệu năng
    ├── run_test_suite.py                # Bộ test suite bộ điều khiển
    └── run_doan_integration_suite.py  # Bộ test hành vi và an toàn xe
```

`comparison_results/` được tạo khi chạy kiểm thử hoặc benchmark và không lưu
trong Git. Các checkpoint DQN cũ đã được dọn vì chúng được huấn luyện trước khi
tích hợp mạng DoAn; hãy huấn luyện lại trước khi so sánh bốn bộ điều khiển.

---

## Yêu cầu môi trường

- **GAMA Platform**: 2025.6.4 hoặc mới hơn (yêu cầu Java 17+)
- **Python**: 3.10+
- **PyTorch**: 2.0+ (hỗ trợ CPU hoặc Apple Silicon MPS / CUDA)

Các script mặc định dùng GAMA tại
`/Applications/Gama.app/Contents/headless/gama-headless.sh`. Nếu cài ở vị trí
khác, đặt biến môi trường `GAMA_HEADLESS` thành đường dẫn tới script headless.

---

## Cài đặt

1. **Clone repository:**
   ```bash
   git clone https://github.com/ngocbityta/Traffic-Light-ABM.git
   cd Traffic-Light-ABM
   ```

2. **Cài đặt môi trường Python:**
   ```bash
   bash dqn_py/setup_env.sh
   ```

3. **Mở dự án trên GAMA Studio:**
   - Mở GAMA Platform.
   - Chọn `File` -> `Import` -> `General` -> `Existing Projects into Workspace`.
   - Chọn thư mục `Traffic` để nạp các mô hình GAML.

---

## Hướng dẫn sử dụng

### 1. Chạy mô phỏng trực tiếp trên GAMA
- Mở một trong các file trong `Traffic/models/`:
  - `intersection-fixed-time.gaml`
  - `intersection-maxpressure.gaml`
  - `intersection-qlearning.gaml`
- Nhấn chọn experiment `my_experiment` (GUI) hoặc `my_batch_experiment` (batch) và bấm **Run**.

### 2. Huấn luyện và Đánh giá DQN (Python + GAMA Server)
- **Kiểm tra kết nối GAMA Server:**
  ```bash
  cd dqn_py
  python smoke_test.py
  ```
- **Huấn luyện mô hình:**
  ```bash
  python train.py --episodes 100 --episode-horizon 8000
  ```
- **Đánh giá trọng số đã huấn luyện:**
  ```bash
  python evaluate.py --weights run/train_<timestamp>/best_weights.pt --episodes 5
  ```

### 3. Chạy Benchmark đối sánh 4 mô hình
Pipeline dùng để so sánh chính sách đã huấn luyện:

```bash
dqn_py/venv/bin/python scripts/fair_benchmark.py \
  --output comparison_results/fair_benchmark_RUN \
  --train-episodes 40 --validate-every 10 --runs 5 \
  --horizon 8000 --workers 4 --start-server --port 6876
```

Pipeline này triển khai bốn chính sách trong Python, cùng điều khiển
`intersection-benchmark.gaml`. Fixed-Time giữ xanh đi thẳng 30 giây cộng một
cycle handshake 0,1 giây; ba chính sách còn lại dùng cùng giới hạn xanh, pha
rẽ trái và pha vàng. MaxPressure tách xe đi thẳng khỏi xe rẽ trái và xét xe
trên làn đầu ra tương ứng.

Mỗi seed có một CSV yêu cầu xe cố định, gồm thời điểm đến, nguồn, loại xe,
tốc độ, hướng rẽ và làn ban đầu. Yêu cầu chưa vào được mạng được giữ trong
hàng đợi bên ngoài. Lưu lượng yêu cầu giữ các khoảng cách thời gian cũ:
NS 1,5 giây, EW 4,5 giây, mỗi tuyến cầu/hầm 12 giây. Cần đọc cả hàng đợi
bên ngoài vì lưu lượng yêu cầu có thể vượt khả năng tiếp nhận ở đầu mạng.

Q-Learning và DQN học off-policy trên cùng dữ liệu chuyển trạng thái,
với reward là âm tích phân số xe dừng theo thời gian và hệ số chiết khấu
phụ thuộc độ dài bước. Seed train bắt đầu từ 1001; validation dùng 3001–3002;
test bắt đầu từ 5001. Checkpoint được chọn theo hàng đợi trung bình trên
validation. Test dùng greedy và kiểm tra Q-table/trọng số không bị thay đổi.

Các worker giữ nguyên chính sách trong lúc thu thập mỗi nhóm episode;
transition được ghép theo thứ tự seed trước khi cập nhật cả hai phương pháp.
Mỗi episode dùng một tiến trình GAMA mới để tránh lỗi worker cũ khi reload.
`--workers 4` sử dụng các cổng 6876–6879; có thể chọn `--workers 1` nếu cần
giảm tài nguyên. Trên máy 16 GB RAM, có thể thêm biến môi trường cho lệnh:
`_JAVA_OPTIONS='-Xms256m -Xmx2g -XX:-AlwaysPreTouch'` để giới hạn heap mỗi JVM.

Kết quả gồm `report.md`, `comparison.png`, `summary.csv`,
`per_run_metrics.csv`, `manifest.json`, checkpoint và log hành động từng lượt.
Các file `progress_<port>.json` cập nhật tiến độ mỗi 1.000 cycle.
Thêm `--resume` với đúng cấu hình để tiếp tục một lượt bị gián đoạn.
Thêm `--smoke --horizon 1000` với thư mục output mới để kiểm tra seed và tính lặp lại.

`compare_4_models.py` vẫn chạy các model GAML riêng để kiểm tra bản demo.
Q-Learning trong đường chạy cũ học từ bảng rỗng trong mỗi episode, nên không
dùng bảng đó để kết luận thứ hạng của bốn chính sách đã huấn luyện.

---

## Sáu chỉ số của benchmark ghép cặp

1. **Xe mặt đất hoàn thành**: số xe đã tới đích trong lượt mô phỏng.
2. **Hàng đợi trong mạng trung bình**: số xe gần như dừng ở mỗi bước.
3. **Chờ đã tích lũy trên mỗi yêu cầu xe**: gồm cả thời gian chờ ngoài mạng.
4. **Yêu cầu còn đợi ngoài mạng**: số xe chưa vào được mạng khi hết lượt.
5. **Hành trình của xe đã hoàn thành**: thời gian từ khi vào mạng tới đích.
6. **Chờ trong mạng lớn nhất**: giá trị lớn nhất ghi nhận trong lượt.

Biểu đồ và báo cáo trong `seminar/` dùng kết quả từ
`comparison_results/fair_benchmark_20261005_final/`. Thư mục kết quả này là
dữ liệu chạy thử tại máy và được Git bỏ qua; có thể tái tạo bằng lệnh benchmark
ở trên.


## Cấu trúc đường DoAn trong Traffic

Bốn model `Traffic/models/intersection-*.gaml` dùng mạng đường Thanh Xuân
đã tích hợp từ DoAn vào `Traffic/includes/`. Source DoAn riêng đã được gỡ sau
khi đối chiếu đủ mặt đường, cầu vượt, trụ cầu, hầm, metro và đèn; bảng đếm xe
gốc còn trong `Traffic/data/` để phục vụ hiệu chỉnh sau này. Mở experiment GUI của model cần chạy, chọn màn
hình `doan_3d` để xem cầu vượt, hầm, metro và xe. **Xe cầu vượt và hầm** bật/tắt
nhu cầu trên các nhánh này. Bật **Xem mặt cắt hầm** để quan sát xe dưới mặt đất. Metro là phần minh họa, không tham gia điều khiển giao thông đường bộ.
Đồ thị đường và các species `road`/`intersection` được khai báo trong cùng
`collision_avoidance.gaml` để GAMA kiểm tra model mà không thiếu kiểu dữ liệu.
Camera mặc định của `doan_3d` dùng góc xiên gần nút giao; xe và cột đèn có aspect
3D riêng. Sau khi sửa model, dừng experiment đang chạy rồi Run lại để GAMA nạp
camera mới. `intersection_view` vẫn là bản đồ 2D để theo dõi điều khiển đèn.
Trong `doan_3d`, mỗi cột có hai đầu đèn ba bóng xếp ngang và bảng số đếm ngược
đặt cao ngay phía trên đầu đèn để camera mặc định thấy rõ. GUI giới hạn chu kỳ
tối thiểu 0,05 giây thật cho mỗi bước mô phỏng 0,1 giây (tối đa 2× tốc độ thời
gian thực); thanh chỉnh tốc độ của GAMA có thể thay đổi tốc độ quan sát. Với
Fixed-Time, cả đầu đèn xanh, vàng và đỏ đều đếm ngược theo lịch pha. Hết
3 giây vàng, pha chuyển ngay dù vẫn còn xe trong nút giao. Bộ điều khiển thích
ứng hiện `-` ở đầu đèn đỏ vì chưa thể biết chính xác thời điểm xanh tiếp theo.
Monitor **Đếm ngược pha** luôn hiện thời gian hoặc giới hạn thời gian của pha.
Với bộ điều khiển thích ứng, `≤` là thời gian xanh tối đa còn lại vì bộ điều khiển
có thể đổi pha sớm. Thời gian vàng luôn là 3 giây mô phỏng.

- Mạng mới có 64 đoạn đường có hướng và 56 nút, gồm đường mặt đất, rẽ trái,
  rẽ phải, quay đầu, cầu Bắc–Nam, bốn ramp và hai làn hầm Đông–Tây riêng khỏi
  đường mặt đất. Làn quay đầu tách khỏi hàng xe rẽ trái trước vạch đèn.
- Giữ Fixed-Time, MaxPressure, Q-Learning, giao tiếp DQN Python và chu kỳ tám pha
  có đèn rẽ trái riêng. Bộ điều khiển chỉ quan sát xe chịu điều khiển đèn ở mặt
  đất trong vùng phát hiện gần giao lộ.
- Xe vẫn dùng `driving`/IDM/MOBIL, ba loại xe và kỹ thuật chuyển làn của Traffic.
  Điểm nhập/tách nhánh bổ sung quyền đi qua vùng xung đột để tránh hai xe trên
  hai cạnh đồ thị cùng chiếm chỗ trước khi chúng đến nút chung.
- Do giới hạn DrivingSkill, đồ thị lái xe nằm trên mặt phẳng; cao độ vật lý dùng
  cho hiển thị và lọc xung đột được nội suy riêng (hầm −60 m, cầu +50 m).
  Đây không phải mô phỏng động lực học xe theo độ dốc.
- 16 chỉ số làn con giữ liên tục qua các cạnh để kỹ thuật bám xe nhận đúng làn;
  số này không phải số làn vật lý của cầu/hầm. Xe bị giới hạn vào các làn con
  hợp lệ theo tuyến và loại xe.
- Throughput, thời gian chờ và hàng đợi dùng cho reward là của xe mặt đất.
  Xe cầu/hầm có bộ đếm hoàn thành riêng; cảm biến an toàn loại các cặp khác tầng.
- Batch và DQN mặc định chạy 8.000 cycle = 800 giây. Cần huấn luyện lại DQN trên
  cấu trúc mới trước khi đối sánh; các checkpoint và báo cáo cũ không chứng minh
  chất lượng điều khiển trên DoAn.

Kiểm thử tích hợp và hồi quy:

```bash
python3 scripts/run_doan_integration_suite.py
python3 scripts/run_test_suite.py
dqn_py/venv/bin/python -m unittest dqn_py.test_gama_env_schedule
```

Bộ DoAn lưu log và `results.json` vào thư mục kết quả riêng theo thời điểm chạy.
Ca `dqn` của bộ này kiểm tra bộ điều khiển dự phòng trong GAMA. Với GAMA Server
vừa khởi động trên cổng 6871, kiểm tra giao thức và vòng quyết định thực tế:

```bash
dqn_py/venv/bin/python dqn_py/smoke_test.py --port 6871
dqn_py/venv/bin/python dqn_py/test_doan_server.py --start-server --port 6871
```

Bài kiểm tra server còn xác nhận reset seed, 18 trường trạng thái, 8 đầu vào
mạng DQN, hai hành động EXTEND/SWITCH và xe hoàn thành hành trình trên cả hai
nhóm tuyến. Khởi động lại server sau khi sửa GAML để tránh dùng model đã cache.
