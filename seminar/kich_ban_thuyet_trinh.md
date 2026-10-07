# KỊCH BẢN THUYẾT TRÌNH CHI TIẾT SEMINAR
**Chủ đề:** Điều khiển đèn giao thông từ dữ liệu: Mô phỏng GAMA và bốn phương pháp điều khiển  
**Tập tin trình chiếu:** `seminar.tex` (24 slide chính)  
**Thời lượng dự kiến:** 15 – 20 phút (trung bình 35 – 50 giây / slide)  

---

## Slide 01: Tiêu đề
- **Tiêu đề slide:** Điều khiển đèn giao thông từ dữ liệu — Mô phỏng GAMA và bốn phương pháp điều khiển
- **Thời lượng:** ~30 giây
- **Mục tiêu:** Mở đầu cuốn hút, nêu bật tính thực tế của vấn đề giao thông đô thị và định vị phạm vi nghiên cứu (mô phỏng khoa học).

### Lời thoại (Script):
> *"Kính thưa quý thầy cô và các bạn,*  
> Chắc hẳn ai trong chúng ta cũng từng trải qua cảm giác bực bội khi dừng đèn đỏ ở một ngã tư: một bên đường hoàn toàn vắng tanh nhưng vẫn được bật đèn xanh tới vài chục giây, trong khi chiều của mình xe cộ ùn ứ kéo dài mà vẫn phải đứng chờ.  
> 
> Vấn đề cốt lõi ở đây là: **Làm sao để hệ thống đèn giao thông tự nhận biết lưu lượng thực tế và ra quyết định thông minh theo thời gian thực?**  
> 
> Hôm nay, em xin phép trình bày đề tài: **'Điều khiển đèn giao thông từ dữ liệu: Mô phỏng GAMA và bốn phương pháp điều khiển'**. Trong nghiên cứu này, nhóm em xây dựng một môi trường mô phỏng vi mô đa tác tử trên nền tảng GAMA, kết nối với Python để kiểm chứng và so sánh một cách công bằng bốn thuật toán điều khiển khác nhau — từ phương pháp truyền thống đến Học tăng cường sâu (Deep Reinforcement Learning)."*

- **Gợi ý trình bày & Lưu ý:**
  - Giữ giọng tự tin, mở đầu bằng tình huống thực tế để thu hút sự chú ý.
  - *Lưu ý phản biện:* Nhấn mạnh rõ đây là nghiên cứu đánh giá thực nghiệm **trong môi trường mô phỏng vi mô**, chưa phải hệ thống đã triển khai ngoài hiện trường.

---

## Slide 02: Đèn nên giữ xanh hay nhường hướng khác?
- **Tiêu đề slide:** Đèn nên giữ xanh hay nhường hướng khác?
- **Thời lượng:** ~40 giây
- **Mục tiêu:** Định hình rõ câu hỏi nghiên cứu, phạm vi đóng góp của đề tài và mạch dẫn dắt toàn bài.

### Lời thoại (Script):
> *"Tại một ngã tư, câu hỏi quyết định ở mọi thời điểm chỉ gói gọn trong một lựa chọn nhị phân: **Nên tiếp tục giữ đèn xanh cho trục hiện tại, hay chuyển pha để nhường đường cho trục vuông góc?**  
> 
> Để trả lời câu hỏi này một cách khoa học, nghiên cứu của chúng em triển khai theo ba bước trụ cột:  
> 1. **Dựng môi trường:** Thiết lập mạng giao thông hỗn hợp với ô tô, xe máy, xe buýt cùng các luật di chuyển, lách làn và rẽ trái.  
> 2. **Kết nối điều khiển:** Thiết lập cầu nối trao đổi dữ liệu hai chiều giữa GAMA và Python, từ đó áp dụng bốn chiến lược điều khiển khác nhau.  
> 3. **Kiểm chứng công bằng:** Huấn luyện và đánh giá trên cùng một tập nhu cầu phương tiện (traffic demand seeds) để đảm bảo tính khách quan tuyệt đối.  
> 
> Mạch trình bày hôm nay sẽ đi xuyên suốt qua bốn giai đoạn: **Mô phỏng $\rightarrow$ Ra quyết định $\rightarrow$ Quá trình học $\rightarrow$ và Đánh giá thực nghiệm**."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh vào dòng chữ đỏ/alert ở cuối slide: *"mô phỏng $\rightarrow$ quyết định $\rightarrow$ học $\rightarrow$ đánh giá"*.
  - *Lưu ý phản biện:* Thẳng thắn thừa nhận các mô hình như IDM, MOBIL, Q-Learning hay DQN là các nền tảng kế thừa kinh điển; đóng góp trọng tâm của đề tài là việc tích hợp hệ thống, thiết kế luật bổ sung, xây dựng giao thức điều khiển và khung benchmark công bằng.

---

## Slide 03: Môi trường: một ngã tư trong mạng nhiều tầng
- **Tiêu đề slide:** Môi trường: một ngã tư trong mạng nhiều tầng
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giới thiệu bản đồ không gian mô phỏng, cấu trúc nút giao và phạm vi điều khiển của tác tử.

### Lời thoại (Script):
> *"Đầu tiên, về môi trường mô phỏng. Như quý thầy cô và các bạn nhìn thấy trên sơ đồ bên trái:  
> Đây là một không gian mạng giao thông kích thước $2.000 \times 2.000$ mét gồm bốn nhánh trục chính: Bắc, Nam, Đông và Tây. Mạng lưới được thiết kế nhiều tầng: có hệ thống cầu vượt và hầm chui để phân tách dòng xe xuyên tâm không cắt ngang mặt đất.  
> 
> Trọng tâm điều khiển của chúng em đặt tại **nút giao ngã tư mặt đất ở trung tâm**. Tại đây:  
> - Có **4 cột đèn** tương ứng với 4 hướng tiếp cận, mỗi cột tách làm **2 nhóm tín hiệu riêng biệt**: một cho luồng đi thẳng và một cho luồng rẽ trái. Tổng cộng có 8 nhóm tín hiệu.  
> - Toàn bộ 8 nhóm tín hiệu này được điều khiển đồng bộ bởi **1 bộ điều khiển trung tâm duy nhất**, thay vì để 4 hướng hoạt động rời rạc."*

- **Gợi ý trình bày & Lưu ý:**
  - Tay chỉ vào hình bản đồ `network_map`, chỉ rõ ngã tư trung tâm mặt đất và các tuyến cầu vượt/hầm chui chạy tách biệt.
  - *Lưu ý phản biện:* Bản đồ này được xây dựng mô hình hóa bằng mã nguồn trong GAMA, không phải bản sao số (digital twin) quét GIS từ một ngã tư cụ thể ngoài đời thực. Cầu vượt và hầm chui không tạo giao cắt mặt đất.

---

## Slide 04: Mỗi làn đường có 16 làn con
- **Tiêu đề slide:** Mỗi làn đường có 16 làn con (Sublanes)
- **Thời lượng:** ~40 giây
- **Mục tiêu:** Giải thích cơ chế mô phỏng giao thông hỗn hợp đặc thù của Việt Nam (nhiều xe máy, luồn lách tự nhiên).

### Lời thoại (Script):
> *"Một trong những thách thức lớn nhất của giao thông đô thị Việt Nam là tính chất **hỗn hợp không theo làn cứng**. Để giải quyết bài toán này trong mô phỏng, chúng em chia mỗi chiều đường thành **16 làn con (sublanes)**, mỗi làn con có độ rộng $1,75$ mét — tạo nên tổng bề rộng mặt đường là 28 mét mỗi chiều.  
> 
> Cơ chế này cho phép các phương tiện chiếm dụng không gian theo kích thước vật lý thực tế:  
> - Một chiếc **xe máy** chỉ chiếm đúng **1 làn con**.  
> - Trong khi một chiếc **ô tô con hoặc xe buýt** sẽ chiếm **2 làn con liền kề**.  
> 
> Nhờ cấu trúc sublanes này, xe máy có thể linh hoạt điền vào các khoảng trống giữa các ô tô, tái hiện chân thực hành vi giao thông hỗn hợp thay vì bắt mọi xe xếp hàng đơn điệu như mô hình phương Tây."*

- **Gợi ý trình bày & Lưu ý:**
  - Chỉ vào sơ đồ dải sublane ở phía trên.
  - Giải thích thêm: Các xe đi thẳng thường chiếm nhóm làn giữa, xe rẽ trái dạt sang sát dải phân cách, xe máy có thể lách qua các khe hẹp nếu có khoảng trống an toàn.

---

## Slide 05: Xe chạy theo luật (IDM)
- **Tiêu đề slide:** Xe chạy theo luật
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Trình bày mô hình bám xe vi mô IDM (Intelligent Driver Model) vận hành từng phương tiện.

### Lời thoại (Script):
> *"Vậy các phương tiện trên đường di chuyển dựa trên quy luật nào?  
> Mỗi phương tiện trong mô hình là một tác tử (agent) độc lập. Cứ mỗi chu kỳ mô phỏng $0,1$ giây, mỗi xe sẽ tự tính toán xem: **'Mình nên tăng ga, giữ nguyên vận tốc hay đạp phanh?'**  
> 
> Logic này được điều khiển bởi mô hình bám xe kinh điển **IDM (Intelligent Driver Model)**, được tích hợp qua kỹ năng `driving` của GAMA. Mỗi bước mô phỏng, hàm `do drive` sẽ tính toán gia tốc $a$ theo công thức ở bên dưới:  
> Nhìn vào công thức, gia tốc gồm hai thành phần đối nghịch:  
> - Thành phần thứ nhất: Đẩy xe tăng tốc hướng tới vận tốc mong muốn $v_0$.  
> - Thành phần thứ hai: Tạo lực hãm phanh khi khoảng cách thực tế $s$ tiến sát khoảng cách an toàn mong muốn $s^*$ so với xe phía trước.  
> 
> Nhờ đó, hành vi bám xe, giảm tốc và dừng đèn đỏ diễn ra hoàn toàn tự nhiên và mượt mà."*

- **Gợi ý trình bày & Lưu ý:**
  - Chỉ vào công thức IDM: giải thích nhanh trực giác của 2 số hạng trong ngoặc vuông (tăng tốc vs phanh khoảng cách an toàn).
  - *Lưu ý phản biện:* Nhắc rõ AI/DQN chỉ nằm ở **bộ điều khiển đèn**, các xe di chuyển hoàn toàn theo mô hình vi mô IDM của GAMA, chứ không phải mỗi xe mang một mạng nơ-ron riêng.

---

## Slide 06: Lách và rẽ trái đều có điều kiện
- **Tiêu đề slide:** Lách và rẽ trái đều có điều kiện
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giới thiệu cơ chế đổi làn (MOBIL) và quỹ đạo rẽ trái mượt mà bằng đường cong Bézier bậc 3.

### Lời thoại (Script):
> *"Bên cạnh việc bám đuôi, xe trong thực tế còn lách làn và rẽ hướng. Trong mô hình, các hành vi này đều được kiểm soát bởi các điều kiện an toàn khắt khe:  
> 
> - **Thứ nhất, việc đổi làn:** Chúng em kế thừa cơ chế **MOBIL** kết hợp với bộ lọc kiểm tra khoảng hở an toàn cả phía trước và phía sau. Xe chỉ được phép lách sang làn con lân cận khi việc đổi làn mang lại lợi ích về tốc độ mà không ép xe phía sau phải phanh gấp nguy hiểm.  
> - **Thứ hai, việc rẽ trái:** Để quỹ đạo xe qua nút giao không bị gãy khúc cơ học, chúng em xây dựng quỹ đạo bằng **đường cong Bézier bậc 3 (Cubic Bézier)** với 4 điểm điều khiển $P_0$ đến $P_3$. Công thức $B(t)$ toán học bên dưới giúp tạo ra một đường vòng cung trơn tru tự nhiên.  
> 
> Xe chỉ được phép tiến vào đường rẽ Bézier khi thỏa mãn đồng thời hai điều kiện: **pha đèn rẽ trái đang xanh** và **đoạn lối ra phía trước có đủ khoảng trống tiếp nhận**."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh: Việc rẽ trái và lách làn không phải chuyển động ngẫu nhiên mà tuân theo cả điều kiện hình học (Bézier) lẫn điều kiện an toàn động lực học (khoảng trống).

---

## Slide 07: AI được quyết định khi nào?
- **Tiêu đề slide:** AI được quyết định khi nào?
- **Thời lượng:** ~50 giây
- **Mục tiêu:** Làm rõ giao diện ra quyết định (Action space, Decision epochs, Constraints) giữa AI và bộ mô phỏng.

### Lời thoại (Script):
> *"Bây giờ, chúng ta bước sang phần điều khiển: **AI thực sự can thiệp vào hệ thống đèn vào lúc nào và được làm những gì?**  
> 
> Trong thực tế kỹ thuật giao thông, ta không thể để AI bật/tắt đèn tùy tiện mỗi giây vì sẽ gây hỗn loạn và tai nạn. Do đó, hệ thống đặt ra các ràng buộc pha rất chặt chẽ:  
> 
> - **Quy tắc thời gian:** Khi một trục vừa chuyển sang đèn xanh, nó được bảo đảm thời gian **xanh tối thiểu 10 giây**. Trong 10 giây đầu này, AI hoàn toàn không can thiệp.  
> - **Mốc ra quyết định:** Kể từ giây thứ 10, cứ sau mỗi chu kỳ **5 giây** (tại các mốc 10s, 15s, 20s... cho tới 55s), hệ thống sẽ gửi câu hỏi tới AI.  
> - **Hai lựa chọn hành động:**  
>   + Nếu AI chọn **'Giữ'**: Đèn tiếp tục xanh thêm 5 giây.  
>   + Nếu AI chọn **'Chuyển'**: Hệ thống bắt đầu chu trình chuyển pha an toàn: đèn vàng 3s $\rightarrow$ đèn rẽ trái 12s $\rightarrow$ đèn vàng 3s $\rightarrow$ rồi mới bàn giao quyền ưu tiên xanh cho trục vuông góc.  
> - **Trần an toàn 60 giây:** Nếu AI liên tục chọn 'Giữ' tới mốc 60 giây, hệ thống sẽ tự động cưỡng chế chuyển pha để tránh tình trạng một trục bị bỏ quên quá lâu."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh: Đây là bài toán điều khiển **rời rạc theo mốc thời gian (5 giây/lần)** với **2 hành động: Giữ (0) hoặc Chuyển (1)**, tuân thủ nghiêm ngặt chuẩn an toàn chu kỳ pha.

---

## Slide 08: Bốn phương pháp điều khiển
- **Tiêu đề slide:** Bốn phương pháp điều khiển
- **Thời lượng:** ~20 giây
- **Mục tiêu:** Giới thiệu ngắn gọn 4 thuật toán được đưa vào bàn cân so sánh.

### Lời thoại (Script):
> *"Để kiểm chứng hiệu quả của việc điều khiển dựa trên dữ liệu, chúng em đặt lên bàn cân **bốn phương pháp điều khiển** đại diện cho các trường phái khác nhau:  
> 1. **Fixed-Time:** Phương pháp chu kỳ cố định truyền thống.  
> 2. **Max-Pressure:** Thuật toán điều khiển thích ứng dựa trên lý thuyết dòng điều áp.  
> 3. **Q-Learning dạng bảng (Tabular Q-Learning):** Học tăng cường kinh điển dựa trên trạng thái rời rạc.  
> 4. **Deep Q-Learning (DQN):** Học tăng cường sâu với mạng nơ-ron xấp xỉ hàm giá trị.  
> 
> Chúng ta hãy cùng đi sâu vào nguyên lý hoạt động của từng phương pháp."*

- **Gợi ý trình bày & Lưu ý:**
  - Đọc rõ ràng tên 4 phương pháp, chuyển slide nhanh vì đây là slide bản lề phân nhóm.

---

## Slide 09: Fixed-Time
- **Tiêu đề slide:** Fixed-Time
- **Thời lượng:** ~30 giây
- **Mục tiêu:** Nêu rõ cơ chế mốc cơ sở (Baseline) truyền thống.

### Lời thoại (Script):
> *"Phương pháp đầu tiên là **Fixed-Time** — phương pháp đèn cố định đang được dùng phổ biến nhất trên đường phố hiện nay.  
> 
> - **Đặc điểm:** Phương pháp này hoàn toàn 'mù' thông tin giao thông. Nó không gắn cảm biến, không đếm số lượng xe đang chờ hay dòng xe đang tới.  
> - **Quy tắc:** Thời gian đèn xanh đi thẳng được cố định cứng nhắc là **30 giây** cho mỗi trục. Hết 30 giây, hệ thống chuyển pha theo đúng chu kỳ định sẵn.  
> 
> Đây sẽ là mốc chuẩn cơ sở (baseline) để chúng ta đo lường xem các phương pháp thông minh có thực sự mang lại giá trị vượt trội hay không."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh tính chất: Không phản hồi theo lưu lượng thực tế (Unactuated / Open-loop control).

---

## Slide 10: Max-Pressure
- **Tiêu đề slide:** Max-Pressure
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giải thích nguyên lý tính áp lực dòng xe (áp lực ròng) và thuật toán quyết định tức thời.

### Lời thoại (Script):
> *"Phương pháp thứ hai là **Max-Pressure** — một thuật toán điều khiển thích ứng kinh điển trong kỹ thuật giao thông.  
> 
> Nguyên lý cốt lõi: Coi các dòng xe như áp suất chất lỏng. Tại mỗi trục tiếp cận $j$, 'áp lực' $P_j$ được tính bằng hiệu số:  
> $$P_j = (q_j + a_j) - d_j$$  
> Trong đó:  
> - $q_j$ là số xe đang dừng chờ tại vạch dừng;  
> - $a_j$ là số xe đang trên đường chạy tới nút;  
> - và $d_j$ là số xe ở lối thoát phía sau nút giao.  
> 
> Việc trừ đi $d_j$ là cực kỳ thông minh: nếu đường thoát phía trước đang bị tắc nghẽn, áp lực sẽ bị giảm xuống để ngăn đèn xanh đẩy thêm xe vào bẫy kẹt.  
> 
> **Quy tắc quyết định:** Như ví dụ trên slide, nếu trục Bắc–Nam có áp lực là 11, trong khi trục Đông–Tây đang xanh nhưng áp lực chỉ là 5, thì $11 > 5 + 2$ (vượt ngưỡng biên an toàn). Hệ thống sẽ lập tức quyết định **chuyển pha** sang cho Bắc–Nam."*

- **Gợi ý trình bày & Lưu ý:**
  - Chỉ vào công thức và giải thích nhanh phép tính số học cụ thể trong ví dụ.
  - *Điểm mấu chốt:* Max-Pressure ra quyết định dựa trên công thức toán giải tích trực tiếp, phản ứng tức thời nhưng không có khả năng dự đoán tương lai dài hạn.

---

## Slide 11: Reinforcement Learning - Học tăng cường
- **Tiêu đề slide:** Reinforcement Learning - Học tăng cường
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Trình bày khung lý thuyết tương tác Agent – Environment của Học tăng cường trong bài toán điều khiển tín hiệu đèn.

### Lời thoại (Script):
> *"Khác với hai phương pháp trên, hai phương pháp tiếp theo ứng dụng **Học tăng cường (Reinforcement Learning)** — nơi hệ thống tự học từ chính trải nghiệm tương tác với môi trường.  
> 
> Như sơ đồ khối trên slide:  
> - **Tác tử (Agent):** Chính là bộ điều khiển đèn giao thông.  
> - **Môi trường (Environment):** Là toàn bộ nút giao thông và các phương tiện di chuyển trong mô phỏng GAMA.  
> - **Chu trình lặp:** Tại mốc quyết định, tác tử quan sát trạng thái giao thông $s$, chọn hành động $a$ (giữ hoặc chuyển). Mô phỏng chạy tiếp, sinh ra một phản hồi điểm thưởng (reward) $r$, và tác tử chuyển sang quan sát trạng thái mới $s'$.  
> 
> **Mục tiêu tối thượng của RL:** Tìm ra một chính sách (policy) tối ưu để tối đa hóa tổng điểm thưởng tích lũy trong dài hạn — nghĩa là làm sao cho tổng thời gian chờ và tình trạng ùn ứ của toàn bộ mạng lưới là thấp nhất."*

- **Gợi ý trình bày & Lưu ý:**
  - Dùng cử chỉ chỉ từ trái qua phải theo các mũi tên: Quan sát $s \rightarrow$ Chọn $a \rightarrow$ Nhận reward $r \rightarrow$ Trạng thái mới $s'$.

---

## Slide 12: Q-Learning: kinh nghiệm nằm trong bảng Q
- **Tiêu đề slide:** Q-Learning: kinh nghiệm nằm trong bảng Q
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giới thiệu cấu trúc Q-table, ý nghĩa của giá trị Q-value và quy tắc cập nhật Bellman rời rạc.

### Lời thoại (Script):
> *"Đại diện đầu tiên của họ RL là **Q-Learning dạng bảng**. Trong thuật toán này, toàn bộ kinh nghiệm tích lũy được lưu trữ trong một bảng tra cứu gọi là **Q-table**.  
> 
> - **Cấu trúc một dòng trong bảng:**  
>   + **Key:** Là một bộ 6 số đại diện cho trạng thái giao thông đã được rời rạc hóa.  
>   + **Value:** Là một mảng 2 phần tử chứa điểm giá trị $[Q(\text{giữ}), Q(\text{chuyển})]$.  
> - **Q-value là gì?** Nó ước lượng tổng lợi ích kỳ vọng từ hiện tại cho tới tương lai nếu chọn hành động đó (số càng lớn thì càng tốt, kể cả khi mang giá trị âm).  
> 
> Ví dụ trên slide: tại trạng thái $(2,0,1,0,0,1)$, điểm của giữ là $-3$, điểm của chuyển là $-8$. Vì $-3 > -8$, hệ thống sẽ chọn **giữ xanh**.  
> 
> Sau mỗi bước trải nghiệm, công thức cập nhật Bellman với tốc độ học $\alpha = 0,1$ sẽ điều chỉnh điểm $Q$ tiệm cận dần về giá trị thực tế."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh: Điểm $Q$ mang dấu âm vì hàm thưởng là phạt thời gian chờ xe; giá trị $-3$ tốt hơn $-8$.
  - Checkpoint được lưu ở file nhị phân PyTorch `.pt` chứa cấu trúc dictionary.

---

## Slide 13: Sáu thành phần tạo nên một key của bảng Q
- **Tiêu đề slide:** Sáu thành phần tạo nên một key của bảng Q
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Chi tiết hóa không gian trạng thái rời rạc gồm 6 đặc trưng và cách giới hạn số lượng trạng thái trong 216 khóa.

### Lời thoại (Script):
> *"Để bảng Q không bị bùng nổ không gian trạng thái, chúng em chắt lọc tình huống giao thông thành **6 đặc trưng cốt lõi** như trong bảng:  
> 1. **Số xe thẳng trục đang xanh:** Rời rạc thành 3 mức: 0 xe, 1–4 xe, hoặc $\ge 5$ xe.  
> 2. **Số xe thẳng trục đối diện:** Cùng chia 3 mức tương tự.  
> 3. **Xe chờ rẽ trái trục mình:** Cờ nhị phân 0 hoặc 1.  
> 4. **Xe chờ rẽ trái trục kia:** Cờ nhị phân 0 hoặc 1.  
> 5. **Tắc nghẽn lối thoát:** Bằng 1 nếu đường ra của trục xanh có từ 5 xe trở lên.  
> 6. **Tuổi đèn xanh:** Chia 3 mốc: dưới 25s, từ 25–45s, hoặc từ 45s trở lên.  
> 
> Khi nhân các tổ hợp khả dĩ: $3 \times 3 \times 2 \times 2 \times 2 \times 3$, không gian trạng thái được thu gọn chính xác trong **tối đa 216 khóa (keys)**. Bảng Q chỉ khởi tạo dòng khi tình huống đó thực sự xuất hiện trong quá trình huấn luyện."*

- **Gợi ý trình bày & Lưu ý:**
  - Chỉ theo từng dòng của bảng trên slide.
  - Nhấn mạnh tính compact (gọn nhẹ) của biểu diễn: chỉ 216 trạng thái giúp Q-learning hội tụ nhanh trên tập dữ liệu nhỏ.

---

## Slide 14: DQN: nhìn toàn bộ vòng ra quyết định và học
- **Tiêu đề slide:** DQN: nhìn toàn bộ vòng ra quyết định và học
- **Thời lượng:** ~55 giây
- **Mục tiêu:** Phân tích sơ đồ kiến trúc tổng thể của Deep Q-Network: luồng suy luận ra quyết định (inference) phía trên và luồng huấn luyện phản hồi (training loop) phía dưới.

### Lời thoại (Script):
> *"Tuy nhiên, việc làm tròn trạng thái thành 216 ô rời rạc có thể làm mất đi các chi tiết liên tục của dòng xe. Do đó, chúng em nâng cấp lên **Deep Q-Network (DQN)**.  
> 
> Sơ đồ trên slide thể hiện toàn bộ chu trình khép kín giữa GAMA và mạng DQN:  
> - **Nhánh trên — Pha ra quyết định (màu xanh):** Tại mốc hỏi, GAMA trích xuất một vector trạng thái liên tục gồm **11 con số**. Vector này đi qua mạng nơ-ron gồm 2 lớp ẩn (mỗi lớp 64 nơ-ron) để tính toán ra 2 điểm giá trị $Q$. Thuật toán chọn hành động có điểm $Q$ cao nhất và gửi lệnh lại cho GAMA tiếp tục mô phỏng.  
> - **Nhánh dưới — Pha học tập (màu tím):** Sau khi mô phỏng chạy xong khoảng thời gian tương ứng, hệ thống ghi nhận điểm phạt $r$ và trạng thái mới $s'$. Trải nghiệm này được lưu vào bộ nhớ đệm **Replay Buffer**. Định kỳ, thuật toán lấy mẫu ngẫu nhiên, tính hàm mất mát (loss) giữa mạng Online và mạng Target, rồi dùng giải thuật **Adam và Backpropagation** để lan truyền ngược cập nhật trọng số mạng."*

- **Gợi ý trình bày & Lưu ý:**
  - Dùng tay phân tách rõ ràng: nửa trên là **Quyết định (Feedforward / Inference)**, nửa dưới là **Học (Feedback / Backpropagation)**.
  - Đây là một trong những slide trực quan quan trọng nhất của bài, cần trình bày rõ ràng, dứt khoát.

---

## Slide 15: Mỗi nút của DQN tính gì?
- **Tiêu đề slide:** Mỗi nút của DQN tính gì?
- **Thời lượng:** ~40 giây
- **Mục tiêu:** Mở 'hộp đen' mạng nơ-ron, giải thích phép tính tuyến tính và hàm kích hoạt phi tuyến ReLU.

### Lời thoại (Script):
> *"Để quý thầy cô và các bạn hình dung bên trong mạng nơ-ron thực sự tính toán những gì, slide này minh họa phép tính tại **từng nơ-ron riêng lẻ**:  
> 
> - **Bước 1 — Tổng kết hợp tuyến tính:** Mỗi nút nhận các giá trị $x_i$ từ lớp trước, nhân với các trọng số tương ứng $w_i$, cộng dồn lại rồi cộng thêm hệ số chệch $b$:  
>   $$z = w_1x_1 + w_2x_2 + \dots + w_nx_n + b$$  
> - **Bước 2 — Hàm kích hoạt phi tuyến:** Giá trị $z$ sau đó được đưa qua hàm **ReLU**: $\max(0, z)$. Nếu $z$ âm thì ép về 0, nếu dương thì giữ nguyên. ReLU chính là chìa khóa giúp mạng học được các quy luật phi tuyến phức tạp của dòng giao thông.  
> 
> Riêng ở **lớp đầu ra cuối cùng**, chúng em không dùng ReLU mà để tuyến tính tự do, bởi vì điểm $Q$ của chúng ta cần mang giá trị âm để phản ánh mức độ phạt."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhắc thêm: Tổng số tham số của toàn bộ mạng chỉ có **$5.058$ tham số** ($11\times64+64$ + $64\times64+64$ + $64\times2+2$) — mô hình rất gọn nhẹ, có thể tính toán suy luận theo thời gian thực trên CPU trong chưa đầy vài mili-giây.

---

## Slide 16: Từ 11 số đầu vào đến một lệnh đèn
- **Tiêu đề slide:** Từ 11 số đầu vào đến một lệnh đèn
- **Thời lượng:** ~40 giây
- **Mục tiêu:** Minh họa quy trình suy luận 4 bước trong thực tế và phân biệt rạch ròi giữa Inference và Training.

### Lời thoại (Script):
> *"Đây là cận cảnh quá trình từ khi có số liệu đến khi đèn thực sự đổi màu:  
> 1. GAMA chạm tới mốc hỏi (ví dụ giây thứ 15 của pha xanh); Python đọc các cảm biến và chuẩn hóa thành vector 11 số thực.  
> 2. Vector này được đưa qua mạng DQN để tính toán 2 điểm số, chẳng hạn mạng trả về: $Q(\text{giữ}) = -4,2$ và $Q(\text{chuyển}) = -2,7$.  
> 3. Vì $-2,7 > -4,2$, thuật toán quyết định chọn hành động **'Chuyển'** (đây là hành động mang lại ít thiệt hại hơn).  
> 4. Python gửi mã lệnh 1 về GAMA, và GAMA lập tức kích hoạt chu trình chuyển sang đèn vàng.  
> 
> **Điểm cần lưu ý:** Cần phân biệt rõ giữa **Suy luận (Inference)** và **Huấn luyện (Training)**. Khi suy luận để đánh giá, trọng số mạng được đóng băng hoàn toàn, mô hình chỉ thực hiện tính toán xuôi (forward pass) để đưa ra hành động tối ưu nhất mà không cập nhật lại tham số."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhắc rõ 11 số ở đây là các chỉ số đếm xe và thời gian chuẩn hóa, không phải ảnh chụp camera hay dữ liệu đa phương tiện nặng nề.

---

## Slide 17: Hàm thưởng: xe chờ lâu làm điểm giảm
- **Tiêu đề slide:** Hàm thưởng: xe chờ lâu làm điểm giảm
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Trình bày chi tiết toán học của Reward Function (tích phân thời gian xe dừng toàn mạng).

### Lời thoại (Script):
> *"Trọng tâm của mọi thuật toán RL nằm ở **Hàm thưởng (Reward Function)** — kim chỉ nam định hướng hành vi của AI.  
> 
> Trong mô hình này, chúng em định nghĩa hàm thưởng phạt dựa trên sự ùn tắc:  
> - Cứ mỗi $0,1$ giây trong khoảng giữa hai lần ra quyết định, hệ thống quét và đếm số lượng xe $q_k$ có vận tốc dưới $1\text{ km/h}$ (coi như đang dừng chờ) trên toàn bộ mạng lưới.  
> - Sau đó, tính tích phân tổng **số xe $\times$ thời gian dừng**, rồi lấy giá trị âm và chia cho hệ số 50:  
>   $$r = -\frac{1}{50}\sum_k q_k \cdot 0,1\text{ s}$$  
> 
> Ví dụ trực quan:  
> - Nếu có 20 xe dừng trong 5 giây, tích lũy là $100\text{ xe}\cdot\text{giây}$, điểm thưởng nhận về là **$r = -2$**.  
> - Nhưng nếu đèn điều khiển khéo léo để chỉ có 5 xe phải dừng, tích lũy chỉ $25\text{ xe}\cdot\text{giây}$, điểm phạt chỉ là **$r = -0,5$** (tốt hơn rất nhiều).  
> 
> AI muốn tối đa hóa điểm thưởng thì bắt buộc phải tìm cách xả hết các hàng chờ nhanh nhất có thể."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh: Việc tính tích phân từng bước $0,1$ giây qua toàn khoảng thời gian giúp phản ánh chính xác động thái ùn tắc liên tục, thay vì chỉ chụp ảnh một khoảnh khắc tĩnh tại lúc cuối chu kỳ.

---

## Slide 18: Quá trình train diễn ra như thế nào?
- **Tiêu đề slide:** Quá trình train diễn ra như thế nào?
- **Thời lượng:** ~50 giây
- **Mục tiêu:** Trình bày pipeline huấn luyện 5 bước (chuẩn bị dữ liệu demand seed, thu thập dữ liệu luân phiên, gom batch cập nhật và validation).

### Lời thoại (Script):
> *"Quy trình huấn luyện được thiết kế bài bản theo 5 bước khoa học:  
> 1. **Chuẩn bị kịch bản:** Chúng em sinh trước 40 kịch bản nhu cầu xe (tương ứng với 40 seed ngẫu nhiên từ 1001 đến 1040) để tạo sự đa dạng cho dòng giao thông.  
> 2. **Chạy mô phỏng:** Mỗi episode chạy $8.000$ bước ($800$ giây thời gian giao thông). Trong đó, DQN và Q-Learning luân phiên nhau đóng vai trò tác tử điều khiển để cùng khám phá môi trường.  
> 3. **Ghi nhận trải nghiệm:** Mọi bộ chuyển trạng thái $(s, a, r, s', \Delta t)$ đều được lưu trữ cẩn thận.  
> 4. **Cập nhật song song:** Sau mỗi nhóm tối đa 4 episode, dữ liệu được nạp vào bộ học chính để cập nhật đồng thời cả bảng Q và mạng DQN.  
> 5. **Kiểm định và chọn mô hình (Validation):** Cứ sau mỗi 10 episode, hệ thống đóng băng mô hình và chạy kiểm tra độc lập trên 2 seed validation (3001 và 3002). Checkpoint nào đạt số lượng xe dừng trung bình thấp nhất sẽ được lưu lại làm đại diện ưu tú nhất."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh tính độc lập: Validation tách biệt hoàn toàn khỏi tập Train; checkpoint tốt nhất được chọn bằng metric khách quan chứ không lấy hú họa ở episode cuối cùng.

---

## Slide 19: Thử hành động, lưu trải nghiệm, rồi học lại
- **Tiêu đề slide:** Thử hành động, lưu trải nghiệm, rồi học lại
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giải thích cơ chế $\epsilon$-greedy, Replay Buffer và Target Network trong DQN.

### Lời thoại (Script):
> *"Để quá trình học diễn ra ổn định và hiệu quả, chúng em áp dụng hai kỹ thuật mấu chốt của Deep Q-Learning:  
> 
> - **Khám phá và Khai thác ($\epsilon$-greedy):** Trong những episode đầu, tác tử có xác suất $\epsilon$ chọn hành động ngẫu nhiên để thử nghiệm các tình huống mới. Giá trị $\epsilon$ giảm dần theo thời gian, giúp tác tử chuyển dần từ giai đoạn 'mò mẫm' sang khai thác chính sách tối ưu đã học được.  
> - **Bộ nhớ kinh nghiệm (Replay Buffer):** Toàn bộ trải nghiệm được lưu vào bộ nhớ đệm chung. Cả Q-Learning và DQN đều học từ nguồn dữ liệu này để đảm bảo sự công bằng.  
> - **Mạng Target (Target Network):** Khi cập nhật DQN, chúng em lấy ngẫu nhiên từng minibatch 64 mẫu từ buffer. Việc dùng một mạng Target riêng biệt — chỉ cập nhật bản sao sau mỗi 100 bước — giúp triệt tiêu hiện tượng đuổi theo mục tiêu di động, giữ cho quá trình học không bị phân kỳ."*

- **Gợi ý trình bày & Lưu ý:**
  - Giải thích nhanh vì sao cần Replay Buffer: Phá vỡ tính tương quan chuỗi thời gian (break correlation) giữa các trạng thái kế tiếp nhau.

---

## Slide 20: Một lần backpropagation diễn ra thế nào?
- **Tiêu đề slide:** Một lần backpropagation diễn ra thế nào?
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Trình bày chi tiết toán học của 1 bước cập nhật gradient: Huber loss, Bellman target và thuật toán tối ưu Adam.

### Lời thoại (Script):
> *"Đi sâu vào toán học của **một bước lan truyền ngược (Backpropagation)**:  
> 1. Đầu tiên, bốc ngẫu nhiên một minibatch gồm 64 trải nghiệm từ Replay Buffer.  
> 2. Mạng Online dự đoán $Q(s, a)$, trong khi mạng Target tính giá trị đích $y$ theo phương trình Bellman với hệ số chiết khấu $\gamma = 0,97$:  
>    $$y = r + (1-\text{done}) \cdot 0,97^{\Delta t/5} \max_{a'} Q_{\text{target}}(s', a')$$  
> 3. Đo độ sai lệch bằng hàm tổn thất **Huber Loss** — hàm này mượt mà như bình phương sai số khi lỗi nhỏ, nhưng lại tuyến tính khi lỗi lớn, giúp chống lại các điểm ngoại lai đột biến.  
> 4. Autograd tính toán đạo hàm riêng $\partial L/\partial W$ và $\partial L/\partial b$. Gradient được cắt ngưỡng chuẩn (norm clipping) ở mức 10 để chống bùng nổ gradient.  
> 5. Bộ tối ưu **Adam** với learning rate $3 \times 10^{-4}$ cập nhật trọng số cho mạng Online.  
> 
> Trong thực nghiệm của chúng em, cứ mỗi trải nghiệm mới nạp vào sẽ kích hoạt 4 lần cập nhật lặp lại như trên."*

- **Gợi ý trình bày & Lưu ý:**
  - Lưu ý chi tiết: Hệ số chiết khấu $0,97^{\Delta t/5}$ tính đến khoảng thời gian trôi qua linh hoạt giữa hai quyết định ($\Delta t$ có thể là 5s, hoặc 23s nếu vừa chuyển pha).

---

## Slide 21: Đánh giá bằng những lượt chưa dùng để học
- **Tiêu đề slide:** Đánh giá bằng những lượt chưa dùng để học
- **Thời lượng:** ~40 giây
- **Mục tiêu:** Khẳng định tính liêm chính khoa học và nguyên tắc benchmark khách quan (Train / Validation / Test hoàn toàn độc lập).

### Lời thoại (Script):
> *"Để đánh giá công tâm, một mô hình tốt không phải là mô hình học vẹt trên tập dữ liệu cũ, mà phải hoạt động xuất sắc trên những tình huống chưa từng gặp.  
> 
> Chúng em phân chia dữ liệu làm 3 tập rạch ròi:  
> - **Tập Train (40 seed từ 1001 đến 1040):** Dùng duy nhất cho việc học và chỉnh sửa trọng số.  
> - **Tập Validation (2 seed 3001 và 3002):** Dùng để sàng lọc và chọn ra file checkpoint tốt nhất.  
> - **Tập Test (5 seed từ 5001 đến 5005):** Tập dữ liệu 'mù' hoàn toàn, dùng để đánh giá 4 phương pháp.  
> 
> **Nguyên tắc vàng khi chạy Benchmark:**  
> - Cả bốn phương pháp đều được chạy trên **đúng cùng 5 kịch bản xe**, cùng lưu lượng, cùng luật di chuyển.  
> - Khi bước vào tập Test, toàn bộ các mô hình học máy đều bị **đóng băng trọng số (freeze)**, tắt hoàn toàn chế độ khám phá ngẫu nhiên ($\epsilon = 0$) và không cập nhật thêm bất kỳ tham số nào."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh từ: *"Đóng băng chính sách"* (Frozen policy) và *"Benchmark ghép cặp"* (Paired seeds).

---

## Slide 22: Benchmark: bốn phương pháp, sáu chỉ số (1/2)
- **Tiêu đề slide:** Benchmark: bốn phương pháp, sáu chỉ số (1/2)
- **Thời lượng:** ~50 giây
- **Mục tiêu:** Trình bày kết quả thực nghiệm ở 3 chỉ số then chốt: Lưu lượng thông qua, Số xe dừng trung bình và Thời gian chờ.

### Lời thoại (Script):
> *"Và đây là kết quả thực nghiệm trên tập Test, tính trung bình qua 5 seed độc lập:  
> 
> Ở 3 chỉ số đầu tiên:  
> 1. **Số lượng xe thông qua nút (Throughput):** Fixed-Time chỉ đạt $228,6$ xe. Trong khi đó, **DQN dẫn đầu với $243,6$ xe** — tăng $6,6\%$ lưu lượng thoát khỏi giao lộ.  
> 2. **Số lượng xe dừng trung bình (Average Queue):** Đây là chỉ số phản ánh mức độ ùn tắc rõ nét nhất. Fixed-Time để tồn ứ trung bình $24,17$ xe tại ngã tư. Max-Pressure kéo giảm xuống $17,23$ xe. Và **DQN xuất sắc nhất khi hạ xuống chỉ còn $12,65$ xe — giảm gần $48\%$ lượng xe dừng so với Fixed-Time**.  
> 3. **Thời gian xe chờ tích lũy:** DQN cũng đạt mức thấp nhất với $286,97$ giây, cải thiện so với mức $292,79$ giây của Fixed-Time.  
> 
> Cả ba chỉ số này đều chỉ ra rằng: Việc điều khiển đèn thích ứng theo dữ liệu giúp giải phóng nút giao thông hiệu quả hơn rõ rệt."*

- **Gợi ý trình bày & Lưu ý:**
  - Chỉ thẳng vào các con số in đậm của cột DQN trên bảng: $243,6$ xe thông qua, $12,65$ xe dừng.
  - Nhấn mạnh con số ấn tượng: *"giảm gần một nửa (48%) lượng xe dừng ùn tắc"*.

---

## Slide 23: Benchmark: bốn phương pháp, sáu chỉ số (2/2)
- **Tiêu đề slide:** Benchmark: bốn phương pháp, sáu chỉ số (2/2)
- **Thời lượng:** ~50 giây
- **Mục tiêu:** Phân tích 3 chỉ số tiếp theo: Nhu cầu ngoài mạng, Thời gian hành trình hoàn thành và Thời gian chờ lớn nhất (Max Waiting Time).

### Lời thoại (Script):
> *"Sang bảng kết quả thứ hai, chúng ta thấy một góc nhìn đa chiều rất thú vị: **Không có một phương pháp nào áp đảo tuyệt đối ở mọi chỉ số**:  
> 
> - **Nhu cầu còn ngoài mạng:** Cả 4 phương pháp đều còn khoảng hơn $1.040$ xe chưa kịp vào mạng do lưu lượng phát sinh ở nguồn vượt quá sức dung nạp của đường dẫn.  
> - **Hành trình xe đã hoàn thành:** **Max-Pressure lại là phương pháp tốt nhất** với $264,64$ giây (nhanh hơn DQN là $268,23$ giây). Lý do là Max-Pressure phản ứng tức thời với áp lực cục bộ, giúp những xe đã vào giao lộ thoát đi cực nhanh.  
> - **Thời gian chờ lớn nhất trong mạng (Max Waiting Time):** Ở chỉ số này, **DQN lại vượt trội hoàn toàn**. Trong khi Fixed-Time và Max-Pressure có những xe bị 'bỏ quên' chịu cảnh chờ tới hơn $550$ giây, thì DQN đã kéo mức chờ tối đa xuống chỉ còn **$439,62$ giây — giảm hơn 115 giây kẹt xe cực đoạn**.  
> 
> Điều này chứng minh DQN có cái nhìn dài hạn tốt hơn, phân bổ thời gian xanh công bằng hơn giữa các hướng tiếp cận."*

- **Gợi ý trình bày & Lưu ý:**
  - Nhấn mạnh sự công tâm khoa học: Thừa nhận Max-Pressure nhỉnh hơn ở thời gian hoàn thành hành trình, nhưng DQN giải quyết xuất sắc bài toán chống bỏ quên luồng xe (giảm Max Waiting Time từ 555s xuống 439s).

---

## Slide 24: Ngoài ùn tắc, mô phỏng còn đo rủi ro
- **Tiêu đề slide:** Ngoài ùn tắc, mô phỏng còn đo rủi ro
- **Thời lượng:** ~45 giây
- **Mục tiêu:** Giới thiệu các chỉ số an toàn giao thông thay thế (Surrogate Safety Measures) được tích hợp trong mô phỏng GAMA và hướng phát triển tương lai.

### Lời thoại (Script):
> *"Cuối cùng, một hệ thống điều khiển giao thông tốt không chỉ cần thông thoáng mà còn phải **an toàn**. Trong mô phỏng, chúng em không đợi va chạm xảy ra mà tích hợp các **chỉ số an toàn thay thế (Surrogate Safety Measures)** theo chuẩn quốc tế:  
> 
> - **TTC (Time to Collision):** Thời gian dự kiến tới va chạm; hệ thống đếm các mẫu có $\text{TTC} < 1$ giây.  
> - **TIT (Time Integrated TTC):** Tích phân mức độ vi phạm ngưỡng an toàn theo từng bước $0,1$ giây.  
> - **PET (Post-Encroachment Time):** Khoảng thời gian từ khi xe trước vừa rời khu vực xung đột tới khi xe sau lao vào; cảnh báo khi $\text{PET} < 1,5$ giây.  
> - **DRAC:** Gia tốc giảm tốc tối thiểu cần thiết để không đâm va.  
> - **Tần suất phanh gấp:** Thống kê các trường hợp xe phải đạp phanh mạnh với gia tốc $<-3,4\text{ m/s}^2$ hoặc $<-5,0\text{ m/s}^2$.  
> 
> Hiện tại mô hình GAMA đã hoàn thiện bộ thu thập các chỉ số rủi ro này. Đây sẽ là tiền đề vững chắc để trong giai đoạn tiếp theo, nhóm nghiên cứu tích hợp yếu tố an toàn trực tiếp vào hàm thưởng của mạng Deep RL.  
> 
> Em xin chân thành cảm ơn quý thầy cô và các bạn đã chú ý lắng nghe. Rất mong nhận được những câu hỏi và đóng góp quý báu từ hội đồng!"*

- **Gợi ý trình bày & Lưu ý:**
  - Kết thúc với thái độ trang trọng, cầu thị và tự tin.
  - Sẵn sàng chuyển sang các slide phụ lục (Appendix) khi có câu hỏi chuyên sâu từ hội đồng.

---

# TỔNG HỢP BÍ QUYẾT PHÒNG THỦ KHI TRẢ LỜI HỎI ĐÁP (Q&A CHEAT SHEET)

1. **Hỏi: Mô hình này có chạy được ngoài đường phố thực tế không?**
   - *Trả lời:* Đây là nghiên cứu bước đầu trong môi trường mô phỏng vi mô đa tác tử (GAMA) nhằm kiểm chứng thuật toán. Ngoài đời thực cần có hệ thống camera AI đếm xe thời gian thực, xử lý độ trễ mạng và phải có các lớp dự phòng an toàn vật lý cứng (fail-safe logic) để tránh lỗi mạng nơ-ron gây xung đột pha.
2. **Hỏi: Tại sao không dùng YOLO/Camera để nhận diện xe luôn?**
   - *Trả lời:* Phạm vi đề tài tập trung vào thuật toán điều khiển tối ưu hóa tín hiệu đèn (decision-making logic). Dữ liệu đếm xe trong nghiên cứu đóng vai trò là ground-truth chuẩn hóa. Trong tương lai, khi triển khai thực địa, vector 11 đặc trưng này có thể lấy trực tiếp từ đầu ra của các pipeline computer vision như YOLO hoặc camera đếm xe chuyên dụng.
3. **Hỏi: DQN có thực sự tốt hơn hẳn Q-Learning dạng bảng không?**
   - *Trả lời:* Trên tập Test 5 seed, DQN cho hàng đợi trung bình là 12,65 xe so với 13,23 xe của Q-Learning. Mức chênh lệch là khoảng 0,58 xe. Cả hai đều vượt trội so với Fixed-Time (24,17 xe). Tuy nhiên, DQN có ưu thế vượt trội ở chỉ số thời gian chờ lớn nhất (Max Waiting Time: 439s so với 497s của Q-Learning và 555s của Fixed-Time), cho thấy mạng nơ-ron xử lý không gian trạng thái liên tục mượt mà hơn và tránh được hiện tượng bỏ quên các hướng nghẽn phụ.
4. **Hỏi: Tại sao không dùng GPU để train DQN?**
   - *Trả lời:* Vì mạng DQN của đề tài có kiến trúc gọn nhẹ (2 lớp ẩn 64 nút, tổng cộng 5.058 tham số). Tắc nghẽn tính toán (bottleneck) nằm ở thời gian chạy mô phỏng vi mô của GAMA trên JVM, chứ không nằm ở phép nhân ma trận của mạng. Do đó chạy trên CPU với PyTorch đa luồng là tối ưu chi phí và không gặp overhead truyền dữ liệu CPU-GPU.
