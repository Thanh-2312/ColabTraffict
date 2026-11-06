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

## Giả định chưa có số liệu

- Đèn 2 pha cố định (xanh LVL 50 s, xanh HĐT 40 s, đỏ toàn phần 3 s), lưu lượng 2400 xe/h/nhánh, 85% xe máy, rẽ trái/phải 20%/20% — đều là tham số trong experiment.
- Xe trên các connector cắt nhau trong vùng xung đột **không nhìn thấy nhau** (advanced_driving chỉ xử lý xe cùng road); đèn 2 pha tránh phần lớn xung đột, riêng rẽ trái với đi thẳng ngược chiều thì chưa.
- Không có quay đầu, không có người đi bộ.
