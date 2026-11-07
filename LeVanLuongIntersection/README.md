# Ngã tư Lê Văn Lương × Hoàng Đạo Thúy / Hoàng Minh Giám (GAMA)

Ngã tư cạnh Hà Nội Center Point (27 Lê Văn Lương, Thanh Xuân). Model GAMA 2025.06 dùng `advanced_driving`:
mỗi chiều của mỗi nhánh là một `road` với `num_lanes` = số sublane rộng **0,8 m**; xe máy chiếm 1 sublane, ô tô 2 sublane.
Làn BRT được tính vào số sublane (xe máy được dùng).

## Chạy

1. GAMA → *File › Import › Existing Projects into Workspace* → chọn thư mục này.
2. Mở `models/LeVanLuong.gaml` → chạy experiment **main**.
3. Monitor "X vào: sublane / hàng đầu max" = số sublane của nhánh / số sublane bị xe chiếm cùng lúc ở hàng đầu (≤ 1,5 m trước vạch dừng).

## Số đo (ảnh vệ tinh, sai số ước tính ±0,5 m nếu không ghi khác)

| Nhánh | Phương vị | Chiều vào: rộng → sublane | Chiều ra: rộng → sublane | Dải phân cách |
|---|---|---|---|---|
| NE – Lê Văn Lương (về Láng Hạ) | 53,4° | 13,3 m → **16** (±0,7) | 12,7 m → **15** | 7,8 m (lát gạch, BRT) |
| SE – Hoàng Đạo Thúy (về Nhân Hòa) | 128,5° | 13,5 m → **16** | 9,2 m → **11** | 2,5 m (bồn cây) |
| SW – Lê Văn Lương (về Khuất Duy Tiến) | 232,8° | 12,8 m → **16** ⚠ | 12,4 m → **15** | 7,9 m (cỏ) |
| NW – Hoàng Minh Giám (về Trung Hòa) | 316,4° | 11,9 m → **14** | 9,9 m → **12** (±1,0) | 2,6 m (bồn cây) |

- Góc giữa các nhánh kề nhau: NE–SE 75,1°, SE–SW 104,3°, SW–NW 83,6°, NW–NE 97,0°. Lê Văn Lương gần thẳng; trục Hoàng Đạo Thúy–Hoàng Minh Giám gãy ~8° và lệch tâm tại nút.
- Vùng xung đột (giữa các vạch dừng và mép ngoài vạch qua đường): **1919 m²**. Bó vỉa góc bán kính 9 m (góc Đông đã đối chiếu ảnh, 3 góc còn lại giả định).
- ⚠ SW vào = 12,8 m nằm đúng ngưỡng 16 × 0,8: hụt 5 cm là còn 15 sublane — nên đo thực địa nhánh này.
- NW ra 9,9 m bị tán cây che, suy ra từ khoảng cách tim 2 chiều trên OpenStreetMap.

**Nguồn:** Esri World Imagery 11/2025 (0,28 m/px) cho NE, SW, NW; Esri Wayback 06/2023 và 12/2024 cho SE và kiểm tra chéo
(nhà cao tầng che các nhánh khác nhau trên từng ảnh); tim đường và phương vị từ OpenStreetMap. Ảnh đối chiếu: `docs/doi_chieu_ve_tinh_2025.png`
(nền: Esri World Imagery — Esri, Maxar, Earthstar Geographics; viền tím = bó vỉa, xanh lá = dải phân cách, vàng = vạch dừng, đỏ = vùng xung đột).
Ảnh mô phỏng GAMA lúc t = 46 s: `docs/gama_t46s.png`. Ảnh chụp thực tế: `nga_tu.png`.

## Sửa số đo

Mọi số đo nằm trong `ARMS` / `CORNER_R` ở đầu `scripts/build_layout.py`. Sửa xong chạy lại:

```bash
python scripts/build_layout.py
```

Script in bảng sublane và ghi lại `includes/roads.geojson`, `includes/areas.geojson` (UTM 48N, mét).

## Train RL (Rainbow / 3DQN + Max Pressure)

Experiment `dqn_server_experiment` dùng cùng giao thức với `Traffic/models/intersection-dqn-python.gaml`, chỉ có state spatial nên chỉ dùng được `--algorithm rainbow` hoặc `hybrid`:

```bash
python dqn_py/train.py --algorithm hybrid --site lvl --reward-mode r1 --workers 4 --start-server
python dqn_py/evaluate.py --site lvl --weights <run>/best_weights.pt --episodes 5 --start-server
```

- Slot E, N, W, S của state = NE, NW, SW, SE. Action: 0 HĐT/HMG thẳng + phải, 1 HĐT/HMG rẽ trái, 2 LVL thẳng + phải, 3 LVL rẽ trái (rẽ trái được bảo vệ). Giữ pha = xanh thêm 10 s; đổi pha = vàng 3 s, đỏ toàn phần ≥ 2 s tới khi vùng xung đột trống (tối đa 10 s), xanh tối thiểu 10 s.
- Đèn theo từng hướng: mỗi nút vạch dừng có 3 loại `stop` (thẳng / trái / phải), xe chỉ tôn trọng loại của hướng mình. Bước mô phỏng 0,1 s.
- State `4×6×20×16`: ô dọc 8 m từ vạch dừng × 16 sublane (sublane 0 sát bó vỉa phải); mặt nạ C5 theo số sublane và chiều dài thật của từng nhánh vào (NW chỉ 14 sublane). C4 lấy từ việc đổi sublane rời rạc của advanced_driving nên mỗi lần đổi làn cho ±1.
- Lịch xe: `dqn_py/demand.py` site `lvl`, xe đến Poisson theo giả định bên dưới; xe chưa vào được nhánh nằm trong hàng đợi ngoài mạng (tính vào R1, R2, R4).

## Giả định chưa có số liệu

- Đèn 2 pha cố định của experiment `main` (xanh LVL 50 s, xanh HĐT 40 s, đỏ toàn phần 3 s), lưu lượng 2400 xe/h/nhánh, 85% xe máy, rẽ trái/phải 20%/20% — đều là tham số trong experiment; lịch xe train RL dùng cùng các số này.
- Xe trên các connector cắt nhau trong vùng xung đột **không nhìn thấy nhau** (advanced_driving chỉ xử lý xe cùng road); đèn 4 pha của RL không cho hai hướng cắt nhau cùng xanh, đèn 2 pha thì rẽ trái vẫn cắt đi thẳng ngược chiều.
- Không có quay đầu, không có người đi bộ.
