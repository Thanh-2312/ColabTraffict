# Nguồn và phạm vi sử dụng

Đối chiếu ngày 06/10/2026. Các bài báo cung cấp mô hình/phương pháp; các con số cấu hình của dự án được lấy từ mã nguồn. Không dùng tên bài báo để chứng thực tham số chưa hiệu chỉnh.

| Thành phần | Nguồn gốc/chính thức | Phạm vi |
|---|---|---|
| Kỹ năng lái GAMA | [Tài liệu Driving Skill](https://gama-platform.org/wiki/UsingDrivingSkill); [Saval et al., PLOS ONE 2023](https://doi.org/10.1371/journal.pone.0281658) | Tích hợp bám xe, đổi làn và xe hỗn hợp; không chứng thực bản đồ hiện tại |
| IDM | [Treiber et al., PRE 2000](https://doi.org/10.1103/PhysRevE.62.1805); [mô tả của tác giả](https://traffic-simulation.de/info/info_IDM.html) | Công thức bám xe; biến thể có `max(0,...)` được kiểm tra thêm trong IDM.class cài tại máy |
| MOBIL | [Kesting et al., TRR 2007](https://doi.org/10.3141/1999-10); [bản tác giả](https://mtreiber.de/publications/MOBIL.pdf) | Điều kiện lợi ích và an toàn của mô hình gốc; GAMA dùng triển khai lấy cảm hứng từ MOBIL |
| Max-Pressure | [Varaiya, TR Part C 2013](https://doi.org/10.1016/j.trc.2013.08.014) | Nền tảng áp lực mạng; policy hai trục của dự án là biến thể có ràng buộc |
| Q-Learning | [Watkins & Dayan 1992](https://doi.org/10.1007/BF00992698); [bản tác giả tại UCL](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf) | Cập nhật giá trị hành động từ reward và giá trị tương lai |
| DQN | [Mnih et al., Nature 2015](https://doi.org/10.1038/nature14236); [PDF do DeepMind lưu](https://storage.googleapis.com/deepmind-media/dqn/DQNNaturePaper.pdf) | Nền tảng Q-network, replay và target; thông số mạng đèn lấy từ code dự án |
| Thời gian quyết định khác nhau | [Bradtke & Duff, NIPS 7](https://proceedings.neurips.cc/paper_files/paper/1994/hash/07871915a8107172b3b5dc15a6574ad3-Abstract.html) | Tư tưởng semi-Markov; gamma 0,97 và reward tích phân là thiết kế cụ thể |
| Adam | [Kingma & Ba](https://arxiv.org/abs/1412.6980); [PyTorch Adam](https://docs.pytorch.org/docs/stable/generated/torch.optim.Adam.html) | Thuật toán và tham số mặc định optimizer |
| Huber / Smooth L1 | [PyTorch SmoothL1Loss](https://docs.pytorch.org/docs/stable/generated/torch.nn.SmoothL1Loss.html) | Trường hợp beta=1 dùng trong triển khai |
| Bézier | [Michigan Tech](https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/Bezier/bezier-construct.html) | Hình học đường cong; điểm điều khiển và lấy 121 điểm do dự án đặt |

Cơ sở động học: [OpenStax — Motion with Constant Acceleration](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration). Các hệ số thêm vào speed cap vẫn là lựa chọn triển khai.

## Các luật do dự án đặt

Nguồn trực tiếp: `Traffic/includes/collision_avoidance.gaml`.

- `choose_safe_lane`: điều kiện mở một lane kề, khoảng hở trước/sau, vùng khóa lane.
- `arbitrate_left_turns`, `left_exit_clear`: cấp xe rẽ trái theo nhánh và kiểm tra chỗ thoát.
- Các cap dừng với hệ số 0,2, 0,5, khoảng thời gian 4 s và các khoảng đệm.
- Tỷ lệ loại xe, hướng rẽ, tốc độ và hình học mạng.
- Nội suy chuyển lane để hiển thị mượt không phải mô hình điều khiển RL.

Không gán các luật này cho Gipps, Gazis hoặc một nghiên cứu hiệu chỉnh nếu chưa có đối chiếu đầy đủ.

## Mã nguồn cho các con số học và kết quả

- `scripts/fair_benchmark.py`: đặc trưng, tabular state, reward, gamma theo thời gian, DQN 64–64, batch, target, checkpoint và chia seed.
- `dqn_py/dqn_agent.py`: lớp `QNetwork` được pipeline tái sử dụng; các giá trị mặc định khác trong file này không tự áp dụng cho benchmark.
- `Traffic/models/intersection-benchmark.gaml`: bộ lọc quan sát.
- `Traffic/models/intersection-dqn-python.gaml`: lịch pha và handshake.
- `comparison_results/fair_benchmark_20261005_final/`: dữ liệu 40 lượt train, 16 lượt validation, 20 lượt test và ảnh chụp mã nguồn.
