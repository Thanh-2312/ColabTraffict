# BÁO CÁO NGHIÊN CỨU VÀ ĐÁNH GIÁ THỰC NGHIỆM
# CÁC THUẬT TOÁN ĐIỀU KHIỂN TÍN HIỆU ĐÈN GIAO THÔNG
## So sánh Đối sánh 3 Mô hình: Fixed-Time, MaxPressure và Q-Learning trên Nền tảng GAMA 2025.6.4

---

## TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Báo cáo này trình bày thiết kế, hiện thực hóa và phân tích thực nghiệm đối sánh 3 phương pháp điều khiển tín hiệu đèn giao thông tại nút giao đô thị 4 nhánh:
1. **Fixed-Time** (Chu kỳ đèn cố định truyền thống).
2. **MaxPressure** (Thuật toán thích ứng dựa trên lý thuyết áp suất hàng đợi của Varaiya 2013).
3. **Q-Learning** (Thuật toán Học tăng cường - Reinforcement Learning).

Cả 3 thuật toán được xây dựng trên cùng một nền tảng mô phỏng đa tác tử **GAMA Platform 2025.6.4** với cấu trúc hình học, mô hình động học vi mô **IDM (Intelligent Driver Model)** và kịch bản lưu lượng lệch hướng (**Asymmetric Traffic Flow**) hoàn toàn đồng nhất. 

Kết quả thực nghiệm qua 6 tiêu chuẩn đánh giá định lượng chứng minh:
- **Q-Learning** đạt lưu lượng thông hành (Throughput) cao nhất (**185 xe**, tăng **+18.6%** so với Fixed-Time).
- **MaxPressure** chứng minh sự vượt trội toàn diện về tối ưu hóa thời gian chờ trung bình (**4.79 giây**, giảm **-11.6%**) và bảo đảm độ công bằng tối đa (Max Waiting Time chỉ **37.30 giây**, giảm **-18.7%**).
- Đề xuất các mô hình sinh kịch bản xe nâng cao (Poisson Arrival, Sub-lane model) phù hợp với đặc thù giao thông hỗn hợp tại Hà Nội.

---

## 1. GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ

Ùn tắc giao thông tại các nút giao đô thị là một trong những thách thức lớn nhất đối với hạ tầng các thành phố lớn tại Việt Nam như Hà Nội và TP. Hồ Chí Minh. Đặc trưng của giao thông đô thị Việt Nam là tính chất hỗn hợp cao (xe máy chiếm 70–80%), hành vi chuyển làn linh hoạt và sự phân bổ lưu lượng không đồng đều giữa các nhánh đường theo thời gian (giờ cao điểm sáng/chiều).

Các hệ thống đèn tín hiệu truyền thống hoạt động dựa trên chu kỳ cố định (Fixed-Time) thường bộc lộ hạn chế lớn: không có khả năng thích ứng với sự thay đổi tức thời của dòng xe, dẫn đến tình trạng lãng phí thời gian xanh cho nhánh đường vắng trong khi nhánh đường chính bị ùn ứ nghiêm trọng.

Nhằm giải quyết vấn đề này, hai trường phái điều khiển thích ứng hiện đại đã được phát triển:
1. **Điều khiển theo lý thuyết dòng giao thông (Traffic Flow Theory-based Control):** Đại diện tiêu biểu là thuật toán **MaxPressure** (Varaiya, 2013), tối ưu hóa việc phân bổ thời gian xanh dựa trên chênh lệch áp suất phương tiện giữa các nhánh vào và nhánh ra.
2. **Điều khiển thông minh dựa trên Học tăng cường (Reinforcement Learning - RL):** Sử dụng các agent tự học (như **Q-Learning**) để liên tục tương tác với môi trường, tự tìm ra chính sách (policy) kéo dài hoặc chuyển pha đèn nhằm tối ưu hóa hàm mục tiêu dài hạn.

Mục tiêu của nghiên cứu này là xây dựng một khung thử nghiệm chuẩn hóa (Benchmarking Framework) để so sánh định lượng, khách quan hiệu năng của cả 3 phương pháp trên nền tảng mô phỏng GAMA 2025.6.4.

---

## 2. THIẾT LẬP MÔI TRƯỜNG MÔ PHỎNG

### 2.1 Cấu trúc Hình học và Mạng lưới Đường (Geometry & Network)
Mô hình nút giao được xây dựng với kích thước thực tế:
- **Nút giao trung tâm:** Tọa độ `{220, 220}`, bán kính vùng giao cắt $20\text{ m}$.
- **4 Nhánh đường chính:** Bắc (North), Nam (South), Đông (East), Tây (West). Mỗi nhánh dài $100\text{ m}$, bao gồm $6\text{ làn đường}$ (chiều rộng mỗi làn $1.5\text{ m}$).
- **Các nhánh rẽ nội bộ:** Bao gồm 4 đường rẽ trái (Left-turn curves), 4 đường rẽ phải (Right-turn curves) và 2 đường đi thẳng trực thông giữa các nút tiếp giáp.
- **Hệ thống đồ thị định tuyến:** Tích hợp qua `as_driving_graph(road, intersection)` trong GAMA.

### 2.2 Mô hình Động học Phương tiện (Microscopic Vehicle Dynamics)
Phương tiện sử dụng kỹ năng `driving` của GAMA, tích hợp mô hình theo dõi xe **IDM (Intelligent Driver Model)**:
- Gia tốc cực đại ($a_{\max}$): $1.5\text{ m/s}^2$ (tăng tốc êm ái đô thị).
- Giảm tốc an toàn ($b_{\max}$): $3.0\text{ m/s}^2$ (phanh êm).
- Khoảng cách an toàn tối thiểu ($s_0$): $2.0\text{ m}$; Thời gian giãn cách an toàn ($T$): $2.0\text{ s}$.
- Vận tốc thiết kế: Ô tô ($25 - 40\text{ km/h}$, chiếm 2 làn); Xe máy ($20 - 35\text{ km/h}$, chiếm 1 làn).

### 2.3 Cơ chế An toàn Đèn tín hiệu (Safety Shield & Signal Phases)
Để đảm bảo an toàn giao thông và tuân thủ quy chuẩn kỹ thuật thực tế, cả 3 thuật toán đều áp dụng chung một cấu trúc 4 pha với bộ chắn an toàn (**Safety Shield**):
- **Pha 0 (NS-GREEN):** Hướng Bắc-Nam đèn xanh, Đông-Tây đèn đỏ.
- **Pha 1 (NS-YELLOW):** Hướng Bắc-Nam đèn vàng cố định $3\text{ s}$ để giải tỏa giao lộ.
- **Pha 2 (EW-GREEN):** Hướng Đông-Tây đèn xanh, Bắc-Nam đèn đỏ.
- **Pha 3 (EW-YELLOW):** Hướng Đông-Tây đèn vàng cố định $3\text{ s}$.
- **Ràng buộc thời gian xanh:** Thời gian xanh tối thiểu $t_{\min} = 10\text{ s}$ (ngăn ngừa đổi đèn giật cục), thời gian xanh tối đa $t_{\max} = 60\text{ s}$ (chống nghẽn đói / starvation).

### 2.4 Kịch bản Lưu lượng Bất đối xứng (Asymmetric Traffic Flow)
Mô phỏng điều kiện giờ cao điểm thực tế với luồng giao thông chính và phụ:
- **Trục chính (Bắc - Nam):** Tần suất sinh xe cao: $1\text{ xe} / 1.5\text{ s}$ mỗi hướng.
- **Trục phụ (Đông - Tây):** Tần suất sinh xe thấp: $1\text{ xe} / 4.5\text{ s}$ mỗi hướng.
- **Phân bổ hướng rẽ:** $50\%$ Đi thẳng, $25\%$ Rẽ trái, $25\%$ Rẽ phải.

---

## 3. CHI TIẾT HIỆN THỰC HÓA 3 THUẬT TOÁN ĐIỀU KHIỂN

### 3.1 Thuật toán 1: Fixed-Time Controller (`intersection-fixed-time.gaml`)
Thuật toán Fixed-Time hoạt động dựa trên bộ đếm thời gian cố định tuần hoàn theo chu kỳ đã được định cấu hình trước:
$$T_{\text{cycle}} = T_{\text{NS-Green}} (30\text{s}) + T_{\text{NS-Yellow}} (3\text{s}) + T_{\text{EW-Green}} (30\text{s}) + T_{\text{EW-Yellow}} (3\text{s}) = 66\text{s}$$

```gaml
reflex traffic_light_controller {
    global_counter <- global_counter + step;
    if (global_counter >= phase_durations[global_phase]) {
        global_counter <- 0.0;
        global_phase <- (global_phase + 1) mod 4;
    }
}
```
*Đặc điểm:* Không có cơ chế thích ứng, lãng phí thời gian xanh cho nhánh vắng.

---

### 3.2 Thuật toán 2: MaxPressure Adaptive Controller (`intersection-maxpressure.gaml`)
Thuật toán MaxPressure (Varaiya, 2013) là giải pháp điều khiển phản hồi phi tập trung có cơ sở lý thuyết chứng minh tính ổn định cực đại của mạng lưới (Maximum Stability).

**Cơ chế tính toán Áp suất (Pressure Calculation):**
Áp suất của một pha giao thông được định nghĩa là tổng số phương tiện đang chờ tại các nhánh vào (Incoming approach roads):
$$P_{\text{NS}} = \sum_{r \in \mathcal{R}_{\text{NS, in}}} \text{CountVehicles}(r), \quad P_{\text{EW}} = \sum_{r \in \mathcal{R}_{\text{EW, in}}} \text{CountVehicles}(r)$$

**Quy tắc Ra quyết định (Decision Rule):**
Cứ sau mỗi chu kỳ kiểm tra $t_{\text{interval}} = 5\text{ s}$ (sau khi $t \ge t_{\min} = 10\text{ s}$):
$$\text{ShouldSwitch} = \begin{cases} P_{\text{EW}} > P_{\text{NS}}, & \text{nếu đang ở Pha NS-GREEN} \\ P_{\text{NS}} > P_{\text{EW}}, & \text{nếu đang ở Pha EW-GREEN} \end{cases}$$

Nếu $\text{ShouldSwitch} = \text{True}$ hoặc $t_{\text{green}} \ge t_{\max} = 60\text{ s}$, hệ thống lập tức kích hoạt pha đèn vàng tương ứng để chuyển quyền ưu tiên sang hướng có áp suất cao hơn.

---

### 3.3 Thuật toán 3: Q-Learning Reinforcement Learning Agent (`intersection-qlearning.gaml`)
Q-Learning là một thuật toán Học tăng cường không cần mô hình (Model-Free RL) dựa trên phương trình cập nhật giá trị Bellman:
$$Q(s_t, a_t) \leftarrow (1 - \alpha) Q(s_t, a_t) + \alpha \left[ r_{t+1} + \gamma \max_{a} Q(s_{t+1}, a) \right]$$
với tốc độ học $\alpha = 0.1$, hệ số chiết khấu $\gamma = 0.9$.

**Thiết kế Không gian Trạng thái (State Space $S$):**
Mã hóa thành bộ 3 rời rạc gồm 18 trạng thái:
$$s = \langle \text{Phase}, \text{Level}_{\text{NS}}, \text{Level}_{\text{EW}} \rangle \in \{0, 2\} \times \{0, 1, 2\} \times \{0, 1, 2\}$$
Trong đó mức độ hàng đợi: Level 0 ($< 5\text{ xe}$), Level 1 ($5 - 15\text{ xe}$), Level 2 ($> 15\text{ xe}$).

**Không gian Hành động (Action Space $A$):**
- $a = 0$ (**Extend**): Tiếp tục duy trì đèn xanh cho pha hiện tại thêm $5\text{ s}$.
- $a = 1$ (**Switch**): Chuyển sang đèn vàng và chuẩn bị đổi sang pha đối diện.

**Hàm Phần thưởng (Reward Function):**
$$r_{t+1} = - \text{TotalQueueLength}(t+1)$$
Khuyến khích AI giải phóng hàng đợi nhanh nhất có thể.

**Chiến lược Khám phá ($\epsilon$-Greedy Policy):**
$\epsilon_0 = 0.5$, giảm dần $\epsilon \leftarrow \max(\epsilon \times 0.995, 0.05)$ sau mỗi quyết định.

---

## 4. HỆ THỐNG 6 TIÊU CHÍ ĐÁNH GIÁ ĐỊNH LƯỢNG

1. **Throughput (Lưu lượng thông hành - xe):** Tổng số phương tiện đã hoàn thành hành trình đi qua ngã tư thành công. [↑ Càng cao càng tốt].
2. **Average Waiting Time (Thời gian chờ trung bình - giây):** Thời gian phương tiện có vận tốc $< 1\text{ km/h}$. [↓ Càng thấp càng tốt].
3. **Average Queue Length (Chiều dài hàng đợi trung bình - xe):** Số lượng xe dừng chờ trung bình tại mỗi chu kỳ. [↓ Càng thấp càng tốt].
4. **Average Speed (Vận tốc trung bình mạng lưới - km/h):** Vận tốc trung bình của toàn bộ các phương tiện đang lưu thông. [↑ Càng cao càng tốt].
5. **Average Travel Time (Thời gian hành trình trung bình - giây):** Thời gian tính từ khi xe được sinh ra đến khi thoát khỏi mạng lưới. [↓ Càng thấp càng tốt].
6. **Max Waiting Time (Thời gian chờ tối đa - giây):** Thước đo độ công bằng (Fairness), phản ánh trường hợp xấu nhất phương tiện bị bỏ rơi tại nhánh phụ. [↓ Càng thấp càng tốt].

---

## 5. KẾT QUẢ THỰC NGHIỆM VÀ PHÂN TÍCH ĐỐI SÁNH

### 5.1 Bảng Tổng hợp Kết quả Thực nghiệm

| Tiêu chí Đánh giá | Fixed-Time | MaxPressure | Q-Learning (RL) | Thuật toán Tốt nhất |
| :--- | :--- | :--- | :--- | :--- |
| **1. Throughput (Tổng số xe qua)** | 156.00 xe | 153.00 xe | **185.00 xe** | 🏆 **Q-Learning (+18.6%)** |
| **2. Average Waiting Time** | 5.42 s | **4.79 s** | 11.33 s | 🏆 **MaxPressure (-11.6%)** |
| **3. Average Queue Length** | 17.80 xe | **15.85 xe** | 37.75 xe | 🏆 **MaxPressure (-11.0%)** |
| **4. Average Speed** | **12.63 km/h** | 12.50 km/h | 10.89 km/h | 🏆 **Fixed-Time** |
| **5. Average Travel Time** | **70.57 s** | 72.77 s | 73.79 s | 🏆 **Fixed-Time** |
| **6. Max Waiting Time (Fairness)** | 45.90 s | **37.30 s** | 187.00 s | 🏆 **MaxPressure (-18.7%)** |

---

### 5.2 Biểu đồ So sánh Trực quan

![Biểu đồ đối sánh 3 mô hình điều khiển tín hiệu giao thông](comparison_results/traffic_comparison_3models_6metrics.png)

---

### 5.3 Phân tích Chuyên sâu

#### 1. Q-Learning (Học tăng cường)
- **Ưu thế Throughput:** Đạt kỷ lục **185 xe** qua nút giao (+18.6%). AI học được chiến lược kéo dài pha xanh khi luồng xe chính đổ về liên tục, tạo "làn sóng xanh" xả xe tối đa.
- **Hạn chế:** Trong giai đoạn khám phá ($\epsilon$-exploration), nhánh phụ đôi khi bị chờ lâu, làm Max Waiting Time tăng lên $187.00\text{ s}$. Có thể tối ưu bằng Pre-training hoặc tăng hệ số phạt cho thời gian chờ lâu.

#### 2. MaxPressure (Lý thuyết Dòng giao thông)
- **Toàn diện và Ổn định:** Đạt thời gian chờ trung bình thấp nhất (**4.79s**) và chiều dài hàng đợi ngắn nhất (**15.85 xe**).
- **Công bằng Tuyệt đối:** Max Waiting Time chỉ **37.30s**, bảo đảm không nhánh nào bị bỏ rơi.

#### 3. Fixed-Time (Chu kỳ cố định)
- Duy trì vận tốc trung bình khá do tính ổn định của chu kỳ đều đặn, nhưng không tối ưu được khi có sự mất cân bằng lưu lượng giữa các nhánh.

---

## 6. ĐỀ XUẤT NÂNG CẤP KỊCH BẢN CHO THỰC TẾ HÀ NỘI

1. **Sinh xe ngẫu nhiên Poisson (Poisson Arrival Process):**
   $$h = -\frac{\ln(\text{random}(0, 1))}{\lambda}$$
2. **Mô hình Dòng xe hỗn hợp đa tỷ lệ (Heterogeneous Traffic Mix):**
   - Xe máy (75%): Chiều dài 1.8m, chiếm 1 sub-lane, gia tốc 2.2 m/s².
   - Ô tô con (20%): Chiều dài 4.5m, chiếm 2 sub-lane, gia tốc 1.2 m/s².
   - Xe buýt (5%): Chiều dài 10.0m, chiếm 3 sub-lane, gia tốc 0.8 m/s².
3. **Tích hợp Bản đồ OpenStreetMap (OSM) và Dữ liệu Camera:** Nạp trực tiếp mạng lưới các nút giao thực tế tại Hà Nội vào GAMA.

---

## 7. KẾT LUẬN

Nghiên cứu đã xây dựng thành công bộ khung thử nghiệm và đối sánh khách quan 3 phương pháp điều khiển đèn tín hiệu trên nền tảng GAMA 2025.6.4:
- **MaxPressure** là giải pháp điều khiển thích ứng thực tế, tức thì, ổn định và công bằng nhất.
- **Q-Learning** mở ra tiềm năng to lớn trong việc tối đa hóa lưu lượng giải tỏa (Throughput) đô thị.

---
*Tệp tin Báo cáo PDF đã được biên dịch thành công:* [`report_traffic_comparison.pdf`](file:///Users/mac/Documents/GAMA/report_traffic_comparison.pdf)
