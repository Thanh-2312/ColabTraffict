"""Editable slide content; emits Beamer source and companion presenter notes."""
from pathlib import Path
import json
import re
D=Path(__file__).resolve().parent
slides=[]
def add(section,title,body,note,source='Mã nguồn dự án',appendix=False):
 slides.append(dict(section=section,title=title,body=body,note=note,source=source,appendix=appendix))
def cols(left,right):
 return r'\begin{columns}[T,onlytextwidth]\begin{column}{.48\textwidth}'+left+r'\end{column}\begin{column}{.48\textwidth}'+right+r'\end{column}\end{columns}'
def items(*xs):return r'\begin{itemize}'+''.join(r'\item '+x for x in xs)+r'\end{itemize}'
def box(title,body):return r'\begin{block}{'+title+'}'+body+r'\end{block}'
def fig(name,height='4.8cm'):return r'{\centering\includegraphics[width=\linewidth,height='+height+r',keepaspectratio]{figures/'+name+r'}\par}'

add('Tổng quan','Điều khiển đèn từ dữ liệu giao thông',r'''
{\Large\bfseries Một ngã tư. Bốn cách ra quyết định.}\par\vspace{.45cm}
{\large Mô phỏng đa tác tử trên GAMA\\và học tăng cường bằng Python/PyTorch}\par\vspace{.55cm}
\begin{tabular}{@{}llll@{}}
\textcolor{muted}{Fixed-Time} & \textcolor{teal}{Max-Pressure} & \textcolor{blue}{Q-Learning} & \textcolor{purple}{Deep Q-Learning}
\end{tabular}\par\vspace{.7cm}
\textbf{Từ cách xe di chuyển đến cách đèn học từ trải nghiệm.}\par
\vspace{.5cm}\small Seminar dự án · Bản đối chiếu mã nguồn và kết quả ngày 06/10/2026
''','Mở đầu bằng vấn đề gần gũi: một hướng đang vắng vẫn được xanh, trong khi hướng kia có xe chờ. Dự án tạo môi trường mô phỏng để thử bốn bộ điều khiển trong cùng điều kiện. Học tăng cường sẽ được giải thích qua chính quyết định giữ xanh hoặc chuyển pha. Đây là nghiên cứu trong mô phỏng, chưa phải hệ thống đã triển khai ngoài đường.','Kho mã GAMA · benchmark đã hoàn tất')

add('Tổng quan','Các phần việc đã triển khai',cols(
box('01 · Môi trường',items('Dựng mạng đường, cầu vượt, hầm và tuyến xe.','Tích hợp kỹ năng lái xe GAMA; thêm luật rẽ, nhập dòng và chống cản nhầm lane.')),
box('02 · Điều khiển và đánh giá',items('Kết nối mô phỏng với Python qua WebSocket.','Cài bốn chính sách; huấn luyện, lưu mô hình.','Ghép cùng nhu cầu xe để so sánh công bằng.')))+r'\vspace{.35cm}\textbf{Mạch trình bày:} hạ tầng → xe → quan sát → quyết định → học → kiểm chứng.',
'Nêu đúng phần đóng góp của dự án. GAMA, IDM, MOBIL, Q-Learning và DQN là nền tảng kế thừa, không phải thuật toán do dự án phát minh. Phần triển khai là cấu hình và tích hợp mạng giao thông, luật bổ sung, điều khiển, kết nối Python và quy trình benchmark. Lỗi xe đứng vô cớ đã được xử lý bằng kiểm tra cùng làn con và tuyến đường thay cho chỉ kiểm tra khoảng cách hình học.','collision_avoidance.gaml; gama_env.py; fair_benchmark.py')

add('Hạ tầng','Một ngã tư mặt đất trong mạng nhiều tầng',cols(fig('network_map','4.5cm'),r'''
\begin{tabular}{@{}p{2.5cm}p{3.7cm}@{}}\toprule
Không gian & $2.000\times2.000$ m\\
Nhánh mặt đất & Bắc, Nam, Đông, Tây\\
Mỗi nhánh & Một chiều vào + một chiều ra\\
Từ nguồn tới nút & Khoảng 949,5 m\\
Vạch dừng & Cách tâm 45 m\\\bottomrule\end{tabular}
\vspace{.3cm}
\begin{itemize}\item Cầu vượt Bắc–Nam; 4 tuyến lên/xuống.
\item Hầm Đông–Tây; 8 tuyến bypass tổng cộng.
\end{itemize}
'''),
'Giải thích đây là mạng dựng bằng mã, không phải bản sao địa lý đã hiệu chỉnh của một nút giao thực. Mỗi nhánh mặt đất có đường vào và đường ra riêng. Các đường có thể cắt nhau trên hình chiếu nhưng cầu vượt và hầm không tạo giao lộ với mặt đất. Cao độ hiển thị cầu là +50 m và đáy hầm là −60 m theo cấu hình mô hình, không nên trình bày như số đo công trình thật. Chuyển động dùng topology phẳng và profile cao độ riêng.','collision_avoidance.gaml: init_doan_network; doan_scenery.gaml')

add('Hạ tầng','16 làn con cho mỗi chiều mặt đất',fig('sublanes','2.0cm')+cols(
items(r'Mỗi làn con rộng \textbf{1,75 m}; bề rộng mô hình là 28 m/chiều.',r'Xe máy chiếm 1 làn con; ô tô và buýt chiếm 2.'),
items('Rẽ trái bắt đầu ở chỉ số 12; quay đầu ở 14.','Các ô 13 và 15 có thể là phần thân xe rộng chiếm thêm.'))+box('Cách diễn giải','Đây là đơn vị chia nhỏ để mô phỏng xe hỗn hợp; không tương đương 16 làn ô tô vật lý.'),
'Chỉ vào dãy từ dải phân cách tới lề phải. Chỉ số giảm từ 15 tới 0 do quy ước hiển thị của mô hình. Xe đi thẳng dùng vùng 4–11; ô tô chỉ được đặt chỉ số thấp nhất 4–10 để thân xe không vượt vùng. Buýt giữ chỉ số 8. Xe trái đặt ở 12, xe quay đầu ở 14; xe rộng chiếm cả ô kế bên. Các tuyến bypass giữ 16 slot logic để nối làn qua merge, nhưng phương tiện của từng tuyến bị khóa lane; không có nghĩa cầu vượt có 16 làn vật lý.','collision_avoidance.gaml: nb_lanes; spawn_vehicle_at; choose_lane')

add('Hạ tầng','4 cột đèn, 8 nhóm tín hiệu, 1 bộ điều khiển',cols(
box('Nhóm tín hiệu',items('Mỗi nhánh vào có một cột.','Mỗi cột: nhóm đi thẳng và nhóm rẽ trái.','Hai hướng đối diện cùng trục được phối hợp.')),
box('Phạm vi điều khiển',items('Bộ điều khiển trung tâm chọn thời điểm kết thúc xanh đi thẳng.','Rẽ phải, quay đầu và bypass không dùng các pha này.')))+r'\vspace{.35cm}\textbf{8 pha thời gian} là 8 trạng thái của lịch đèn; khác với \textbf{8 nhóm tín hiệu} trên 4 cột.',
'Đây là một tác tử điều khiển một nút giao, dù có bốn cột đèn. Trong phần hình ảnh, mỗi cột thể hiện thẳng và mũi tên trái. Không có bốn DQN độc lập. Xe rẽ phải và quay đầu tuân thủ tuyến và luật nhường/nhập dòng của mô hình; không nên suy ra mọi xe được tự do đi qua mọi xung đột.','collision_avoidance.gaml: phase_names; signal drawing; uses_signal')

add('Hạ tầng','Thứ tự 8 pha được giữ cố định',r'''
\begin{tabular}{@{}cllc@{}}\toprule
Pha & Trục Bắc–Nam & Trục Đông–Tây & Thời gian\\\midrule
0 & \textcolor{teal}{Xanh đi thẳng} & Đỏ & Thích ứng / 30,1 s cố định\\
1 & Vàng đi thẳng & Đỏ & 3 s\\
2 & \textcolor{blue}{Xanh rẽ trái} & Đỏ & 12 s\\
3 & Vàng rẽ trái & Đỏ & 3 s\\
4 & Đỏ & \textcolor{teal}{Xanh đi thẳng} & Thích ứng / 30,1 s cố định\\
5 & Đỏ & Vàng đi thẳng & 3 s\\
6 & Đỏ & \textcolor{blue}{Xanh rẽ trái} & 12 s\\
7 & Đỏ & Vàng rẽ trái & 3 s\\\bottomrule
\end{tabular}
\vspace{.25cm}
\textbf{AI chỉ điều chỉnh pha 0 và 4.} Lịch hiện tại không có pha tất cả đỏ riêng.
''',
'Đọc theo trật tự: thẳng Bắc–Nam, vàng, trái Bắc–Nam, vàng, rồi lặp tương tự Đông–Tây. Bộ học không chọn tùy ý tám pha mà chỉ giữ hay kết thúc xanh thẳng. Lưu ý quan trọng từ mã nguồn: vàng kết thúc sau 3 giây, không chờ junction_clear; hiện không có pha all-red riêng. Vì vậy chỉ gọi đây là ràng buộc lịch đèn của mô hình, không tuyên bố đã chứng minh an toàn vận hành thực tế.','intersection-dqn-python.gaml: dqn_controller')

add('Mô phỏng','Mỗi xe là một tác tử có trạng thái riêng',cols(
box('Trạng thái xe',items('Vị trí, tốc độ, kích thước và lane đang chiếm.','Tuyến đường, hướng rẽ, xe phía trước.','Tín hiệu đèn và điều kiện nhường đường.')),
box('Một bước mô phỏng',items(r'GAMA cập nhật các luật với $\Delta t=0,1$ giây.','Tính tốc độ/đổi lane, di chuyển, ghi chỉ số.','Lặp lại 8.000 bước cho một lượt 800 giây.')))+r'\vspace{.3cm}\textbf{Thời gian mô phỏng khác thời gian chạy trên máy.}',
'Tác tử là một đối tượng có dữ liệu và luật hành động riêng; không phải mỗi xe có một mạng AI. Xe hiện chạy theo quy tắc giao thông và mô hình lái của GAMA. DQN chỉ học ở bộ điều khiển đèn. Hành vi ùn tắc xuất hiện từ tương tác nhiều xe. Nhịp 0,1 giây là thời gian trong thế giới mô phỏng; 800 giây giao thông có thể mất nhiều phút máy tính. Sơ đồ trình bày mô tả vòng lặp khái niệm, không cam kết thứ tự từng reflex nội bộ.','GAMA Driving Skill [1]; collision_avoidance.gaml: step, base_vehicle_species')

add('Mô phỏng','Sinh xe theo yêu cầu đã lấy mẫu trước',cols(r'''
\begin{tabular}{@{}p{2.8cm}p{3.2cm}@{}}\toprule
Nguồn & Nhịp yêu cầu\\\midrule
Mỗi nhánh Bắc/Nam & 1,5 s\\
Mỗi nhánh Đông/Tây & 4,5 s\\
Mỗi tuyến bypass & 12 s\\\bottomrule\end{tabular}
\vspace{.35cm}\textbf{Một dòng CSV:} thời điểm, nguồn, loại xe, tốc độ, hướng rẽ, lane.
''',items('Xe mặt đất: 55% máy, 38% ô tô, 7% buýt.','Xe máy/ô tô: 60% thẳng, 20% trái, 15% phải, 5% quay đầu.','Buýt chỉ đi thẳng; bypass dùng ô tô.'))+r'\vspace{.15cm}\textbf{So sánh ghép cặp:} cùng seed → cùng file yêu cầu xe cho cả 4 chính sách.',
'Thời điểm yêu cầu trong benchmark là định kỳ, không phải Poisson. Seed là khóa khởi tạo bộ sinh số giả ngẫu nhiên, dùng để tái tạo loại xe, tốc độ, hướng rẽ và lane. Tỷ lệ 55/38/7 và 60/20/15/5 là cấu hình dự án; chưa có bước hiệu chỉnh từ dữ liệu thật trong pipeline benchmark. Repository có dữ liệu đếm xe nhưng script này không đọc nó. Cùng yêu cầu không có nghĩa xe luôn vào mạng tại cùng thời điểm: đèn có thể gây tắc khác nhau, làm thay đổi thời điểm được nhận vào.','fair_benchmark.py: generate_demand')

add('Mô phỏng','Yêu cầu xe và xe đã vào mạng là hai số khác nhau',cols(
box('Khi cửa vào bị chiếm',items('Có xe gần nguồn trong 15 m → chờ.','Giữ yêu cầu trong hàng FIFO theo nguồn.','FIFO: ai yêu cầu trước được thử vào trước.')),
box('Trong mỗi lượt benchmark',items(r'\textbf{1.424} yêu cầu xe mặt đất.',r'Khoảng \textbf{1.044–1.045} yêu cầu còn ở ngoài mạng cuối lượt (trung bình).','Báo cáo riêng xe hoàn thành và chờ ngoài mạng.')))+r'\vspace{.3cm}\textbf{Phạm vi:} cơ chế FIFO này thuộc chế độ replay của benchmark.',
'Trong chế độ mô phỏng cũ, một lần spawn bị chặn không tự động trở thành hàng FIFO. Benchmark mới dùng demand replay để không bỏ mất nhu cầu. Cần phân biệt yêu cầu, đã tạo trong mạng, đã hoàn thành và còn trong mạng. Các số bên phải là trung bình theo phương pháp của bộ test. Không gọi đây là điều kiện khó nhất có thể; chỉ nói kịch bản hiện tại gây hàng chờ ngoài mạng rất lớn. Điều kiện chặn 15 m tại nguồn cũng giới hạn tốc độ nhận xe nên không quy tất cả hàng chờ cho riêng đèn.','collision_avoidance.gaml: admit_replay_demand; test_results.json')

add('Mô phỏng','Bám xe: tăng tốc khi trống, phanh khi gần',cols(
box('Mô hình IDM',r'\[a=a_{\max}\!\left[1-\left(\frac{v}{v_0}\right)^\delta-\left(\frac{s^*}{s}\right)^2\right]\]'+items('$v$: tốc độ; $v_0$: tốc độ mong muốn.','$s$: khoảng hở; $s^*$: khoảng hở mong muốn.')),
box('Áp dụng trong dự án',items('GAMA driving skill cung cấp IDM.','Loại xe có kích thước, gia tốc và khoảng cách tối thiểu khác nhau.','Luật dự án bổ sung giới hạn tốc độ trước cua, đèn và merge.'))),
'Giải thích ba phần: có xu hướng tăng tốc, giảm xu hướng đó khi gần tốc độ mong muốn, và trừ thêm phần phanh khi tiến sát xe trước. Không cần người nghe tính công thức ngay. Công thức khoảng cách đầy đủ và đơn vị nằm ở phụ lục. Đã kiểm tra lớp IDM trong plugin GAMA cài trên máy: s sao dùng max(0, vT+vΔv/(2√ab)). Bộ quy tắc tổng thể trong dự án không phải IDM thuần túy vì còn các speed cap.','Treiber et al. (2000) [2]; GAMA [1]; IDM.class 2025.6.4')

add('Mô phỏng','Lách xe: mở lane an toàn rồi mới xét đổi lane',cols(
box('1 · Bộ lọc do dự án viết',items('Chỉ xem lane kề khi bị xe chậm phía trước cản.','Kiểm tra khoảng trống trước và sau.','Không mở lane sát vạch dừng hoặc gần merge.')),
box('2 · GAMA xét MOBIL',items('Đổi lane có giúp tăng gia tốc không?','Có làm xe sau phải phanh quá mạnh không?','Ngưỡng lợi ích 0,5 m/s²; nghỉ giữa lần đổi 3 s.')))+r'\vspace{.3cm}\textbf{MOBIL có nguồn nghiên cứu.} Các ngưỡng lọc khoảng trống là lựa chọn của dự án.',
'Lách không phải dịch ngang ngẫu nhiên. Code chỉ mở tối đa một lane kề bên trong allowed_lanes; GAMA sau đó áp dụng cơ chế đổi lane lấy cảm hứng từ MOBIL. Cần nói rõ hai tầng để không gán các ngưỡng 12 m, 1,5 giây hoặc 2,5 giây cho bài báo. Độ mượt nhìn thấy trên màn hình còn có nội suy hiển thị; nó không phải công thức học RL. Công thức cụ thể ở phụ lục.','Kesting et al. (2007) [3]; choose_safe_lane; GAMA [1]')

add('Mô phỏng','Rẽ trái gồm đường đi, quyền vào và tốc độ',cols(
box('Hình học và quyền vào',items('Đi theo đường cong Bézier bậc 3 đã dựng.','Chỉ cấp vào khi pha trái xanh và lối ra đủ trống.','Giãn lượt theo nhánh: đợi xe trước rời vùng đầu cung.')),
box('Giảm tốc trước cua',r'\[v_{\mathrm{cap}}=\sqrt{v_{\mathrm{rẽ}}^2+2bd}\]'+items('$d$: quãng đường còn lại; $b$: mức giảm tốc.','Giới hạn rẽ trái trong cung: 18 km/h.')))+r'\vspace{.3cm}Đây là hình học + động học + luật cấp vào; \textbf{DQN không lái xe rẽ trái}.',
'Công thức cap suy ra từ quan hệ động học v²=u²+2as, không phải nguyên văn mô hình Gipps. Luật cấp vào do dự án thiết kế: lối ra không có xe trong khoảng dài xe rẽ cộng 8 m. Busy approach được giữ khi xe vừa cam kết vào hoặc còn gần đầu connector trong khoảng dài xe cộng 12 m; vì vậy không nói cứng chỉ một xe trong toàn cung mọi lúc. Một xe khác có thể được cấp vào khi xe trước đã đi đủ xa. Các con số chưa hiệu chỉnh thực nghiệm.','collision_avoidance.gaml: doan_turn; arbitrate_left_turns; động học [11]')

add('Quan sát và hành động','Mô phỏng biết từng xe; chính sách nhận bản tóm tắt',cols(
box('Quan sát cục bộ',items(r'Bán kính đếm xe \textbf{190,5 m} từ tâm.','8 số đếm: thẳng chờ, thẳng đang tới, trái chờ, phía thoát; mỗi loại theo 2 trục.','Pha hiện tại và thời gian đã xanh.')),
box('Thông tin không đưa vào DQN',items('Danh tính, tọa độ và thời gian chờ của từng xe.','Xe ngoài vùng đếm và hàng FIFO ngoài mạng.','Lịch xe sẽ tới trong tương lai.')))+r'\vspace{.25cm}\textbf{Số liệu toàn mạng để chấm reward} khác với \textbf{đặc trưng để chọn hành động}.',
'Tránh trả lời đơn giản “đèn không biết gì ngoài camera” vì thực tế simulator có toàn bộ trạng thái. Module quan sát lọc và gom xe thành vector trước khi policy nhận. DQN không nhận hình camera thật. Detector đếm xe đi thẳng và trái trên đường vào có dùng tín hiệu. Phía thoát đếm xe trên road mặt đất ra ở lane thấp nhất 4–11; bộ lọc không loại mọi bypass đã nhập vào road mặt đất. Do đó không khẳng định tuyệt đối rằng mọi xe bypass bị loại khỏi tất cả đặc trưng. Reward trong huấn luyện dùng tổng số xe mặt đất dừng toàn mạng.','intersection-benchmark.gaml: observe_benchmark_movements; fair_benchmark.py: features')

add('Quan sát và hành động','Bộ điều khiển chỉ chọn giữ xanh hoặc chuyển pha',cols(
box('0 · Giữ xanh',items('Đến lần hỏi kế tiếp sau khoảng 5 giây.','Tiếp tục phục vụ trục đang xanh.')),
box('1 · Chuyển pha',items('Vàng 3 s → trái 12 s → vàng 3 s.','Chuyển sang xanh thẳng trục kia.')))+r'''
\vspace{.35cm}
\textbf{Mốc hỏi:} 10, 15, 20, …, 55 giây của pha xanh.\\[.15cm]
\textbf{Giới hạn:} tự chuyển ở 60 giây; lệnh Python có bước áp dụng 0,1 giây.
''',
'Bộ điều khiển không trực tiếp bật màu tùy ý cho từng bóng. GAMA giữ thứ tự và thời lượng các pha vàng/trái; Python trả về 0 hoặc 1. Sau chuyển pha phải qua 18 giây pha trung gian và 10 giây xanh tối thiểu hướng kia mới hỏi lại, cộng bước handshake. Vì vậy khoảng giữa quyết định thay đổi theo hành động. Lần chuyển sớm nhất thực tế khoảng 10,1 giây; Fixed-Time chuyển ở 30,1 giây với cùng giao diện.','intersection-dqn-python.gaml: dqn_controller, update_schedule')

add('Bốn phương pháp','Từ lịch cố định đến học từ trải nghiệm',r'''
\begin{tabular}{@{}p{2.7cm}p{4.6cm}p{5.4cm}@{}}\toprule
Phương pháp & Căn cứ quyết định & Có huấn luyện?\\\midrule
Fixed-Time & Đồng hồ pha xanh & Không; chuyển ở 30,1 s\\
Max-Pressure & Chênh nhu cầu vào và xe phía thoát & Không; dùng công thức/luật\\
Q-Learning & Giá trị từng hành động trong bảng & Có; cập nhật bảng kinh nghiệm\\
Deep Q-Learning & Giá trị do mạng nơ-ron tính & Có; cập nhật trọng số\\\bottomrule
\end{tabular}
\vspace{.6cm}
\textbf{Cùng môi trường, cùng hai hành động và lịch pha.}\\[.2cm]
Cách biểu diễn và sử dụng quan sát khác nhau giữa các thuật toán.
''',
'Fixed-Time là mốc cơ sở đã chọn với xanh bằng nhau cho hai trục, không phải chu kỳ đã tối ưu cho mọi nhu cầu. Không nên nói mọi đèn ngoài đường đều fixed. Max-Pressure phản ứng ngay theo công thức. Q-Learning và DQN học cách ước lượng lợi ích dài hạn. Độ phức tạp tăng không đảm bảo thứ hạng tốt hơn. Q rời rạc và DQN có biểu diễn khác nhau, nên “công bằng” ở đây là cùng demand, lịch đèn, reward và dữ liệu huấn luyện, không phải đầu vào được biến đổi hoàn toàn giống nhau.','fair_benchmark.py: Learners.act; tabular_key; features')

add('Bốn phương pháp','Max-Pressure: ưu tiên phía cần được giải tỏa',r'''
\[P_j=(q_j+a_j)-d_j\]
\begin{center}\small $q$: xe thẳng chờ · $a$: xe thẳng đang tới · $d$: xe phía thoát\end{center}
'''+cols(
box('Ví dụ minh họa',r'Bắc–Nam: $(12+3)-4=11$.\\[.2cm]Đông–Tây: $(4+2)-1=5$.\\[.2cm]Nếu Đông–Tây đang xanh: $11>5+2$ → chọn chuyển.'),
box('Biến thể trong dự án',items('Chuyển nếu áp lực trục kia lớn hơn trục hiện tại + 2.','Cũng nhường khi hướng hiện tại hết xe thẳng nhưng hướng khác/làn trái còn nhu cầu.'))),
'Áp lực là độ dồn ứ ròng, không phải lực vật lý. Trừ xe phía thoát để tránh dồn thêm vào đầu ra đã đông. Dự án dùng biến thể hai trục với ngưỡng 2 và lịch pha ràng buộc. Max-pressure gốc xét các chuyển động, tỷ lệ rẽ và lưu lượng bão hòa; không bê nguyên định lý ổn định hay tối ưu của bài báo sang triển khai giản lược này. Ví dụ trên chỉ minh họa số học, không phải một dòng log đo được.','Varaiya (2013) [4]; fair_benchmark.py: Learners.act')

add('Học tăng cường','Học từ hậu quả của quyết định',r'''
\begin{center}
\begin{tikzpicture}[node distance=.6cm, every node/.style={font=\normalsize}, b/.style={draw=teal,fill=wash,rounded corners,text width=2.5cm,align=center,minimum height=1.1cm}]
\node[b] (s) {Quan sát\\\textbf{trạng thái $s$}};
\node[b,right=of s] (a) {Chọn\\\textbf{hành động $a$}};
\node[b,right=of a] (r) {Mô phỏng chạy\\\textbf{reward $r$}};
\node[b,right=of r] (n) {Quan sát mới\\\textbf{trạng thái $s'$}};
\draw[->,thick] (s)--(a);\draw[->,thick] (a)--(r);\draw[->,thick] (r)--(n);
\end{tikzpicture}
\end{center}
\vspace{.4cm}
\textbf{Tác tử học:} bộ điều khiển đèn. \quad \textbf{Môi trường:} ngã tư và các xe.\\[.3cm]
\textbf{Policy (chính sách):} quy tắc ánh xạ quan sát thành hành động.\\[.3cm]
\textbf{Mục tiêu:} tăng tổng reward hiện tại và tương lai.
''',
'Không cần ẩn dụ huấn luyện động vật. Dùng chính ngã tư để giải thích: bộ điều khiển thử giữ xanh, môi trường chạy thêm, hàng đợi tạo điểm phạt; từ đó điều chỉnh đánh giá của hành động. Không có nhãn sẵn “đây là hành động đúng” cho mọi trạng thái. Reward do người thiết kế đặt, còn cách chọn hành động được học. Vì quan sát bị gom và cắt phạm vi, state ở đây là vector quan sát, không phải trạng thái đầy đủ Markov đã được chứng minh.','Watkins & Dayan (1992) [5]; triển khai dự án')

add('Học tăng cường','Q-Learning: tra một bảng điểm cho hai lựa chọn',cols(r'''
\begin{tabular}{@{}lrr@{}}\toprule
Tình huống & Giữ xanh & Chuyển\\\midrule
Trục mình đông & $-3$ & $-8$\\
Trục kia đông & $-7$ & $-2$\\\bottomrule\end{tabular}
\vspace{.25cm}\small Bảng minh họa; số lớn hơn là tốt hơn, kể cả khi đều âm.
''',items('Mỗi tình huống rời rạc là một hàng.','Hai cột là giá trị $Q(s,a)$ của hai hành động.','Q là ước lượng tổng reward tương lai; không phải xác suất.'))+r'''
\vspace{.25cm}
\[Q(s,a)\leftarrow Q(s,a)+\alpha\,[\,r+\gamma\max_{a'}Q(s',a')-Q(s,a)\,]\]
\small $\alpha=0,1$: mức sửa mỗi lần; $\gamma$: mức coi trọng tương lai. Cuối lượt: bỏ phần tương lai.
''',
'Nếu bảng cho −3 và −8 thì chọn −3 vì ít phạt hơn. Dự án gom queue thành ba mức: 0, 1–4 và từ 5 trở lên, cùng các cờ lane trái, đầu ra và tuổi pha. Bảng có tối đa 216 khóa trạng thái cấu hình, mỗi khóa hai số Q; chỉ tạo khóa khi học gặp nó. Không cần nhớ toàn bộ bảng để hiểu thuật toán: một kinh nghiệm làm sửa đánh giá ở ô tương ứng. Replay bảng dùng một mẫu mới và 31 mẫu cũ.','Watkins & Dayan [5]; fair_benchmark.py: tabular_key, learn')

add('Deep Q-Learning','DQN thay bảng bằng một hàm tính điểm',r'''
\begin{center}
\begin{tikzpicture}[node distance=.7cm,b/.style={draw=teal,fill=wash,rounded corners,text width=2.25cm,align=center,minimum height=1.3cm}]
\node[b] (x) {\textbf{11 số}\ Đầu vào};
\node[b,right=of x] (h1) {\textbf{64 nút}\ Lớp ẩn 1};
\node[b,right=of h1] (h2) {\textbf{64 nút}\ Lớp ẩn 2};
\node[b,right=of h2] (y) {\textbf{2 điểm Q}\ Giữ / chuyển};
\draw[->,thick](x)--(h1);\draw[->,thick](h1)--(h2);\draw[->,thick](h2)--(y);
\end{tikzpicture}\end{center}
\vspace{.25cm}
\[h=\operatorname{ReLU}(Wx+b),\qquad \operatorname{ReLU}(z)=\max(0,z)\]
\textbf{Trọng số $W$ và độ lệch $b$} là các con số được điều chỉnh khi học.\\[.2cm]
Mạng có \textbf{5.058 tham số}; đầu ra là điểm hành động, không phải màu đèn.
''',
'Mỗi lớp thực hiện nhân cộng rồi qua ReLU: giá trị âm thành 0, giá trị dương được giữ. Lớp đầu ra chỉ tuyến tính, vì Q có thể âm. “Deep” chỉ mạng có nhiều lớp biến đổi; không đồng nghĩa hiểu bản đồ như con người. 5.058 = 11×64+64 + 64×64+64 +64×2+2. Mạng có thể chia sẻ thông tin giữa các tình huống gần nhau nhưng cũng có thể tổng quát hóa sai. Không đảm bảo luôn tốt hơn bảng.','Mnih et al. (2015) [6]; dqn_agent.py: QNetwork; fair_benchmark.py: Learners')

add('Deep Q-Learning','11 đầu vào của mạng được tạo như thế nào?',r'''
\begin{tabular}{@{}p{7.2cm}cl@{}}\toprule
Nhóm thông tin & Số chiều & Cách chuẩn hóa\\\midrule
Xe thẳng chờ: B–N, Đ–T & 2 & $\min(n/20,3)$\\
Xe thẳng đang tới: B–N, Đ–T & 2 & $\min(n/20,3)$\\
Xe trái chờ: B–N, Đ–T & 2 & $\min(n/20,3)$\\
Xe phía thoát: B–N, Đ–T & 2 & $\min(n/20,3)$\\
Số bước pha xanh đã qua & 1 & Chia 600\\
Đang pha 0? Đang pha 4? & 2 & Mỗi cờ bằng 0 hoặc 1\\\bottomrule
\end{tabular}
\vspace{.3cm}
Ví dụ: 10 xe → 0,5; từ 60 xe trở lên → 3.\\[.15cm]
\textbf{Chuẩn hóa} giúp đưa các đại lượng về thang số thuận tiện cho mạng.
''',
'Không dùng 11 ảnh, 11 xe hay 11 cảm biến vật lý; đây là 11 số trong một vector. Hai cờ pha chỉ dùng để báo trục nào đang xanh ở lúc cần quyết định. Clipping có mất thông tin: 60 và 100 xe cùng thành 3. Q-table và DQN có cách biểu diễn khác nhau; bảng dùng mức rời rạc còn DQN nhận số đếm đã chuẩn hóa và chặn ngưỡng.','fair_benchmark.py: EXTRA_FIELDS, features')

add('Deep Q-Learning','CPU tính toán; RAM giữ trạng thái đang sử dụng',r'''
\begin{tabular}{@{}p{2.3cm}p{10cm}@{}}\toprule
Thành phần & Vai trò trong lần chạy hiện tại\\\midrule
\textbf{CPU} & Chạy GAMA và phép tính PyTorch; bộ học đặt 2 luồng CPU.\\
\textbf{RAM} & Giữ tác tử xe, trọng số, gradient, replay và optimizer.\\
\textbf{Ổ đĩa} & Lưu CSV, log và checkpoint \texttt{.pt} qua các lần chạy.\\
\textbf{WebSocket} & Truyền quan sát và hành động giữa GAMA và Python.\\\bottomrule
\end{tabular}
\vspace{.2cm}
4 tiến trình GAMA (JVM); mỗi máy ảo Java được giới hạn heap \textbf{2 GiB}.\\[.2cm]
Một mạng: \textbf{20,2 kB} tham số float32. Tổng RAM chương trình lớn hơn nhiều.
''',
'Trả lời trực tiếp “xử lý ở RAM hay gì”: CPU thực thi phép tính, RAM cung cấp chỗ chứa dữ liệu cho CPU, ổ đĩa lưu lâu dài. Pipeline này không chuyển tensor sang CUDA/GPU. 5.058 số float32 ×4 byte =20.232 byte cho tham số một mạng; còn target, actor snapshots, gradients, Adam, Python và JVM nên không được gọi 20 kB là toàn bộ bộ nhớ sử dụng. Lệnh chạy đặt _JAVA_OPTIONS Xmx2g, ghi đè giá trị 16G trong launcher; bản thô ghi 16 GB mỗi JVM là sai cho lần benchmark này.','fair_benchmark.py: torch.set_num_threads, Learners; lifecycle/run configuration')

add('Deep Q-Learning','Một lần suy luận: từ quan sát tới lệnh đèn',r'''
\begin{enumerate}
\item GAMA tới mốc hỏi; Python đọc quan sát và tạo vector 11 số.
\item Mạng tính hai giá trị, ví dụ: $Q(\text{giữ})=-4,2$ và $Q(\text{chuyển})=-2,7$.
\item Khi không khám phá: chọn \textbf{chuyển} vì $-2,7>-4,2$.
\item Python gửi lệnh 1; GAMA áp dụng theo lịch pha đã ràng buộc.
\end{enumerate}
\vspace{.35cm}
\begin{block}{Suy luận khác huấn luyện}
Suy luận sử dụng trọng số đã có để chọn hành động. Huấn luyện dùng kinh nghiệm để sửa trọng số.
\end{block}
''',
'Hai giá trị chỉ minh họa, không phải xác suất 4,2% hay 2,7%. Python gọi forward của mạng rồi argmax để lấy chỉ số điểm lớn nhất. Suy luận sử dụng torch.no_grad để không lưu đồ thị gradient. Với test, epsilon=0 và hoàn toàn không gọi learn. Trong train, actor có thể chọn ngẫu nhiên theo epsilon nên không luôn chọn Q lớn nhất.','fair_benchmark.py: act, run_episode; gama_env.py: set_action')

add('Deep Q-Learning','Reward: mỗi xe chờ đều tạo điểm phạt',r'''
\[r_t=-\frac{1}{50}\sum_{k\;\text{giữa hai quyết định}}q_k\,\Delta t,
\qquad \Delta t=0,1\ \mathrm{s}\]
\begin{center}$q_k$: số xe mặt đất có tốc độ dưới 1 km/h trong toàn mạng.\end{center}
'''+cols(
box('Ví dụ',r'20 xe dừng trung bình trong 5 s\\$\Rightarrow 100$ xe·giây\\$\Rightarrow r=-100/50=\mathbf{-2}$.'),
box('Ý nghĩa và phạm vi',items('Tối đa reward = chịu ít phạt hơn.','Chia 50 là hệ số thang đo.','Chưa đưa chờ ngoài mạng hoặc chỉ số an toàn vào reward.'))),
'Điểm phạt được cộng trong toàn khoảng sau hành động, không chỉ chụp queue ở cuối khoảng. Xe máy, ô tô, buýt mỗi xe có trọng số một; đây không phải số hành khách hay quy đổi PCU. Reward có thể bằng 0 nếu không có xe dừng. Vì không chứa hàng ngoài mạng, bộ học không trực tiếp tối ưu tất cả yêu cầu đã phát sinh. Các chỉ số ngoài mạng vẫn được báo cáo để thấy giới hạn này.','fair_benchmark.py: run_episode; collision_avoidance.gaml: queue_time_integral')

add('Deep Q-Learning','Bước mô phỏng, quyết định và episode',r'''
\begin{tabular}{@{}p{3.1cm}p{9.3cm}@{}}\toprule
Thuật ngữ & Nghĩa trong dự án\\\midrule
Cycle / step & Một bước giao thông dài 0,1 s.\\
Decision & Một lần chọn giữ xanh hoặc chuyển; không diễn ra ở mọi step.\\
Transition & Bản ghi $(s,a,r,s',\mathrm{done},\Delta t)$ giữa hai quyết định.\\
Episode & Một lần reset và chạy hết 8.000 step = 800 s giao thông.\\
Update & Một lần sửa bảng Q hoặc trọng số mạng từ dữ liệu.\\\bottomrule
\end{tabular}
\vspace{.4cm}
\textbf{40 episode} không phải 40 lần cập nhật.\\[.15cm]
Lần huấn luyện này có \textbf{2.381 transition} và \textbf{9.272 cập nhật DQN}.
''',
'State là quan sát lúc quyết định. Action là 0 hoặc 1. Reward tóm chi phí xảy ra tới lần quyết định kế. Next state là quan sát mới. Done đánh dấu kết thúc horizon; Δt ghi thời gian thực trong mô phỏng giữa hai quyết định. Reset xóa lượt giao thông rồi tạo lượt mới theo seed, nhưng bộ học giữ trọng số qua các episode. Phần terminal sau quyết định cuối vẫn được ghi. Không cần gọi số vòng lặp dữ liệu này là epoch; pipeline báo episode, transition và update.','training_log.json; fair_benchmark.py: run_episode, learn')

add('Deep Q-Learning','Lưu trải nghiệm rồi lấy mẫu để học',cols(
box('Replay buffer',items('Bộ nhớ kinh nghiệm trong RAM, tối đa 20.000 transition.','Minibatch = 64 bản ghi lấy ngẫu nhiên.','Bắt đầu học mạng khi có ít nhất 64 bản ghi.')),
box('Hai mạng cùng cấu trúc',items('Online: được cập nhật và dùng để chọn hành động.','Target: bản sao dùng tính mục tiêu học.','Sao online sang target mỗi 100 update.')))+r'\vspace{.3cm}Mỗi transition mới được nhập → \textbf{4 minibatch update} cho DQN.',
'Replay là đọc lại kinh nghiệm, không chạy lại toàn bộ giao thông cho mỗi mẫu. Mẫu ngẫu nhiên giúp giảm việc học chỉ theo chuỗi vừa diễn ra. Target network thay đổi chậm hơn online, giúp mục tiêu học bớt thay đổi liên tục; nó không phải nhãn thật từ một chuyên gia. Buffer của benchmark là deque chứa cả biểu diễn vector và khóa bảng Q. Mỗi transition mới cũng dùng để cập nhật Q-table.','Mnih et al. [6]; fair_benchmark.py: replay, learn')

add('Deep Q-Learning','Học bằng cách giảm sai lệch của điểm Q',r'''
\[y=r+(1-\mathrm{done})\,\gamma_{\Delta t}\max_{a'}Q_{\mathrm{target}}(s',a'),
\qquad \gamma_{\Delta t}=0,97^{\Delta t/5}\]
\[L=\operatorname{Huber}\big(Q_{\mathrm{online}}(s,a)-y\big)\]
'''+cols(
box('Ví dụ một mẫu',r"$Q=-3$; $r=-2$; $\max Q(s')=-2,5$.\\[.15cm]Nếu $\Delta t=5$ s: $y=-4,425$.\\[.15cm]Dự đoán đang lạc quan hơn mục tiêu."),
box('Điều chỉnh tham số',items('Backpropagation tính gradient: độ nhạy của loss với tham số.',r'Adam dùng gradient để sửa tham số; learning rate $3\times10^{-4}$.'))),
'Bellman target ghép phần reward đã quan sát với điểm tương lai ước lượng. Nếu episode kết thúc, done=1 nên chỉ còn reward. Hệ số chiết khấu phụ thuộc thời gian vì giữ và chuyển dẫn tới lần quyết định kế cách nhau khác nhau. Loss là thước đo lệch giữa dự đoán và mục tiêu. Gradient không phải reward; nó mô tả nếu sửa mỗi tham số thì loss thay đổi thế nào. Adam là thuật toán cập nhật dùng trung bình động của gradient và bình phương gradient; công thức chi tiết ở phụ lục.','Q-learning [5]; DQN [6]; Bradtke & Duff [7]; Adam [8]; learn')

add('Deep Q-Learning','Khám phá khi học; đóng băng khi kiểm tra',cols(
box('Epsilon-greedy',items(r'Với xác suất $\varepsilon$: thử hành động ngẫu nhiên.','Còn lại: chọn điểm Q cao nhất.','Giảm từ 1,0 xuống 0,05; chạm mức 0,05 ở episode 33.')),
box('Thu thập chung dữ liệu',items('Episode lẻ do actor DQN điều khiển; chẵn do actor Q.','Cả hai bộ học nhận toàn bộ transition.',r'Test: $\varepsilon=0$, không sửa trọng số/bảng.')))+r'\vspace{.3cm}\textbf{Off-policy:} có thể học từ dữ liệu do một chính sách khác tạo ra.',
'Trong một nhóm tối đa bốn lượt, actor là bản sao đóng băng của bộ học tại đầu nhóm. Thu thập kết thúc rồi master nhập dữ liệu theo thứ tự episode, tránh thứ tự tiến trình xong trước quyết định kết quả học. Actor không phải mạng riêng tự học liên tục từng bước. Epsilon(k)=max(0,05,1−0,95(k−1)/32), nên mức sàn bắt đầu ở episode 33, không phải chính xác trong 32 episode đầu như bản thô. Cùng dữ liệu chưa đồng nghĩa hai thuật toán dùng đúng cùng số phép tính.','fair_benchmark.py: run_jobs, pipeline, Learners.act')

add('Deep Q-Learning','Checkpoint giúp lưu và tiếp tục việc học',r'''
\begin{tabular}{@{}p{4.2cm}p{8cm}@{}}\toprule
Trong file \texttt{.pt} & Dùng để làm gì?\\\midrule
Online + target & Giữ các tham số mạng\\
Optimizer Adam & Giữ bộ nhớ của thuật toán cập nhật\\
Bảng Q + replay & Giữ kinh nghiệm và bộ học dạng bảng\\
RNG + bộ đếm & Khôi phục ngẫu nhiên và mốc tiến độ\\\bottomrule
\end{tabular}
\vspace{.35cm}
\texttt{last\_checkpoint.pt}: tiếp tục huấn luyện.\\[.15cm]
\texttt{best\_q.pt}, \texttt{best\_dqn.pt}: mô hình được chọn bằng validation.\\[.15cm]
Khi chạy lại: đọc file từ ổ đĩa → nạp dữ liệu vào RAM → CPU xử lý.
''',
'File .pt là checkpoint PyTorch, không phải video hoặc ảnh mô phỏng. Huấn luyện cần online, target, optimizer, replay và RNG để resume nhất quán. Đánh giá chỉ cần phần chính sách: online của DQN hoặc bảng Q. Pipeline lưu sau mỗi nhóm episode; nó không lưu toàn bộ trạng thái GAMA đang chạy giữa một episode. Một lần lỗi đóng cổng đã được khắc phục rồi resume từ checkpoint sau episode 4; phần dữ liệu học không bị mất.','fair_benchmark.py: save, load_training, load_policy')

add('Thực nghiệm','Ba tập seed có ba nhiệm vụ khác nhau',r'''
\begin{tabular}{@{}p{2.5cm}p{3.5cm}p{6.2cm}@{}}\toprule
Tập & Quy mô & Vai trò\\\midrule
Train & 40 seed: 1001–1040 & Sửa bảng Q và trọng số DQN\\
Validation & 3001–3002, mỗi 10 episode & Chọn checkpoint có hàng đợi thấp nhất\\
Test & 5001–5005 × 4 phương pháp & Đánh giá chính sách đã đóng băng\\\bottomrule
\end{tabular}
\vspace{.4cm}
\begin{itemize}
\item Cùng file nhu cầu, horizon, lịch đèn và luật xe cho từng seed test.
\item Seed thực tế được đọc lại; JVM mới cho mỗi lượt.
\item Kiểm tra hash chính sách, số yêu cầu và lưu toàn bộ log.
\end{itemize}
''',
'Giải thích như học, chọn cách làm, rồi làm bài kiểm tra cuối. Validation lặp trên hai seed để chọn checkpoint nên không được gộp vào test. Chỉ có một seed khởi tạo bộ học là 42; 40 demand seed không có nghĩa 40 lần huấn luyện độc lập. Cấu hình nguồn và demand được ghi hash để phát hiện mã thay đổi. Bộ test có 20 lượt đã hoàn tất. Các baseline không có bước huấn luyện, nhưng dùng cùng simulator và action interface.','manifest.json; fair_benchmark.py: validate, pipeline; seminar_integrity_check.json')

add('Thực nghiệm','Huấn luyện có cải thiện trên validation',fig('validation','4.35cm')+r'\vspace{.15cm}\small Mỗi điểm: trung bình 2 seed validation. Chọn Q ở episode 40; DQN ở episode 30.',
'Đường này không phải loss train và không phải kết quả test. Nó đo hiệu quả giao thông khi đóng băng mô hình sau mỗi 10 episode. Trình bày rằng hiệu quả có thể lên xuống; số update tăng không buộc hàng đợi giảm đều. Q-Learning chọn checkpoint episode 40 (12,30 xe); DQN chọn episode 30 (9,61 xe), vì DQN episode 40 tăng lên 11,54 xe. Bốn điểm validation chưa chứng minh hội tụ.','validation/ep10…ep40; biểu đồ sinh trực tiếp từ metrics.json')

add('Thực nghiệm','Hàng đợi trung bình trên 5 seed kiểm tra',fig('test_queue','4.25cm')+r'\vspace{.1cm}\small Chấm: từng seed. Thanh sai số: độ lệch chuẩn mẫu, không phải khoảng tin cậy.\\\textbf{DQN: 12,65 xe; Q-Learning: 13,23; Max-Pressure: 17,23; Fixed-Time: 24,17.}',
'Đây là số xe dừng trung bình theo thời gian của toàn mạng mặt đất, không phải độ dài hàng mét và không phải chỉ xe chờ đèn đỏ. Trong tập này thứ tự trung bình phù hợp giả thuyết nhưng không được trình bày như quy luật mọi nơi. DQN giảm khoảng 47,7% so với Fixed-Time. Chênh DQN với Q-Learning chỉ khoảng 0,58 xe; phải nhìn kết quả từng seed và sự biến thiên.','test_results.json: 20 lượt, 8.000 cycle/lượt')

add('Thực nghiệm','Một phương pháp không thắng ở mọi chỉ số',r'''
\begin{tabular}{@{}lrrrr@{}}\toprule
Trung bình 5 seed & Fixed & MP & Q & DQN\\\midrule
Xe hoàn thành $\uparrow$ & 228,6 & 232,4 & 238,8 & \textbf{243,6}\\
Hành trình xe xong (s) $\downarrow$ & 277,27 & \textbf{264,64} & 268,83 & 268,23\\
Chờ tích lũy/yêu cầu (s) $\downarrow$ & 292,79 & 289,85 & 287,82 & \textbf{286,97}\\
Chờ ngoài mạng cuối lượt (xe) & 1.045,0 & 1.043,8 & 1.045,4 & 1.044,4\\\bottomrule
\end{tabular}
\vspace{.45cm}
\begin{itemize}
\item DQN cao nhất về xe hoàn thành trung bình trong tập này.
\item Max-Pressure thấp nhất về thời gian hành trình của xe đã xong.
\item Chờ/yêu cầu là chi phí đã phát sinh tới horizon; nhiều chuyến chưa kết thúc.
\end{itemize}
''',
'Mỗi chỉ số trả lời một câu khác nhau. Hành trình chỉ tính xe đã hoàn thành nên có thiên lệch chọn mẫu nếu một chính sách để xe chậm chưa kịp xong. Chờ/yêu cầu cộng thời gian dừng trong mạng và thời gian FIFO bên ngoài, rồi chia 1.424 yêu cầu; không phải thời gian chờ trọn đời của mọi chuyến. Chênh lệch này nhỏ hơn mức cải thiện chỉ số trong mạng do phần ngoài mạng rất lớn.','summary.csv; per_run_metrics.csv')

add('Thực nghiệm','DQN chưa ổn định trên mọi tình huống',fig('test_seeds','4.2cm')+r'\vspace{.1cm}\small DQN có queue thấp nhất ở 3/5 seed; seed 5003 có queue cao nhất trong 4 phương pháp.\\\textbf{Một seed huấn luyện, năm seed test: chưa đủ kết luận ưu thế phổ quát.}',
'Đây là các seed ghép cặp: cùng cột seed nhận cùng demand. DQN thắng 5001,5002,5004 nhưng kém nhất 5003; Q-Learning có độ lệch chuẩn queue nhỏ nhất trong bộ test. Không lấy việc chênh nhỏ hơn độ lệch chuẩn làm kiểm định thống kê. Nói rằng chưa có bằng chứng thống kê vững về ưu thế DQN so với Q; cần nhiều training seed và nhiều kịch bản.','per_run_metrics.csv; biểu đồ dữ liệu gốc')

add('Kết luận','Đóng góp và bước tiếp theo',cols(
box('Đã có',items('Mô phỏng xe hỗn hợp với luật có thể kiểm tra.','Bốn bộ điều khiển trên cùng giao diện.','Pipeline học, checkpoint và benchmark tái lập.','Dữ liệu từng lượt và giới hạn rõ ràng.')),
box('Cần kiểm chứng thêm',items('Hiệu chỉnh hành vi bằng dữ liệu giao thông thực.','Nhiều mức nhu cầu và nhiều seed huấn luyện.','Bổ sung mục tiêu ngoài mạng và an toàn.','Kiểm tra khoảng giải tỏa nút giao.')))+r'\vspace{.15cm}\textbf{Thông điệp:} kiểm chứng chất lượng điều khiển bằng mô phỏng và cách đo đáng tin cậy.',
'Kết thúc bằng phần việc đã làm và một giới hạn rõ. DQN học cách kéo dài hay kết thúc xanh dựa trên tóm tắt cục bộ, không điều khiển mọi xe và không hiểu toàn bộ tương lai. Các ngưỡng rẽ/lách và lưu lượng là lựa chọn mô hình, chưa đại diện cho mọi nút giao ngoài đời. Mở phần hỏi đáp; phụ lục giữ công thức và nguồn để trả lời sâu.','Mã nguồn, báo cáo benchmark và tài liệu tham khảo')

# Appendix: complete equations, implementation details and source trail.
add('Phụ lục · Xe','A1 · IDM đầy đủ và các đại lượng',r'''
\[a=a_{\max}\left[1-\left(\frac v{v_0}\right)^\delta-\left(\frac{s^*}{s}\right)^2\right],\quad
s^*=s_0+\max\left(0,vT+\frac{v\Delta v}{2\sqrt{a_{\max}b}}\right)\]
\begin{tabular}{@{}lp{9.3cm}@{}}\toprule
$v,\Delta v$ & Tốc độ xe; tốc độ xe mình trừ tốc độ xe trước (m/s)\\
$s,s_0,s^*$ & Khoảng hở thực; tối thiểu; mong muốn (m)\\
$T$ & Khoảng cách theo thời gian mong muốn (s)\\
$a_{\max},b$ & Tham số tăng tốc và giảm tốc (m/s²)\\
$v_0,\delta$ & Tốc độ đích hiệu dụng; số mũ thành phần đường trống\\\bottomrule\end{tabular}
\vspace{.25cm}\small GAMA còn giới hạn tốc độ theo road và \texttt{max\_speed}; dự án có thêm speed cap.
''','Công thức được đối chiếu bytecode IDM.class của GAMA 2025.6.4 cài tại máy, gồm max(0,…) của khoảng cách động. T và delta không được dự án gán riêng trong configure_vehicle nên kế thừa mặc định skill; không tự điền số không kiểm tra. Các thông số xe riêng ở bảng kế tiếp.','[1], [2]; IDM.class; configure_vehicle',True)

add('Phụ lục · Xe','A2 · Cấu hình ba loại xe',r'''
\begin{tabular}{@{}lrrrrr@{}}\toprule
Loại & Dài (m) & Làn con & $a_{\max}$ & $b$ & $s_0$ (m)\\\midrule
Xe máy & 2,0 & 1 & 2,8 & 4,5 & 0,8\\
Ô tô & 4,6 & 2 & 1,8 & 3,8 & 2,0\\
Buýt & 10,0 & 2 & 1,2 & 2,8 & 3,0\\\bottomrule\end{tabular}
\vspace{.4cm}
Tốc độ mong muốn lấy mẫu: xe máy 25–37; ô tô 30–45; buýt 22–32 km/h.\\[.2cm]
Gia tốc/giảm tốc ở bảng dùng m/s².\\[.3cm]
\textbf{Đây là tham số của dự án, chưa phải bảng hiệu chỉnh từ dữ liệu đo.}
''','Phân biệt nguồn mô hình với nguồn tham số. IDM có bài báo nền tảng, nhưng không vì vậy mà các số trong configure_vehicle tự trở thành tham số xác thực tại Việt Nam. max_deceleration trong skill được dùng như b của IDM và ở các cap tự viết; không nên diễn giải đơn giản như giới hạn vật lý tuyệt đối mà mọi phương trình luôn tuân thủ.','collision_avoidance.gaml: configure_vehicle; generate_demand',True)

add('Phụ lục · Xe','A3 · MOBIL và bộ lọc khoảng trống',r'''
\small
MOBIL kinh điển: lợi ích bản thân + lợi ích xe sau có trọng số phải vượt ngưỡng.
\[\tilde a_c-a_c+p\big[(\tilde a_n-a_n)+(\tilde a_o-a_o)\big]>\Delta a_{\mathrm{th}},\qquad
\tilde a_n\ge-b_{\mathrm{safe}}\]
Dấu $\tilde{\ }$: sau đổi lane; $c$: xe mình; $n/o$: xe sau lane mới/cũ; $p$: mức nhường.
\vspace{.2cm}
\begin{tabular}{@{}lp{8.8cm}@{}}\toprule
Bộ lọc dự án & Điều kiện trước khi cho GAMA xét đổi lane\\\midrule
Có xe cản & Gap $<\max(12\mathrm{m},2\mathrm{s}\cdot v)$; xe trước chậm hơn $>1$ m/s\\
Lane mới, phía trước & Gap $\ge\max(4\mathrm{m},1,5\mathrm{s}\cdot v)$\\
Lane mới, phía sau & Gap $\ge\max(5\mathrm{m},2,5\mathrm{s}(v_{\mathrm{sau}}-v)+5\mathrm{m})$\\\bottomrule\end{tabular}
\vspace{.15cm}Các ngưỡng trong bảng là tự đặt; GAMA dùng triển khai lấy cảm hứng từ MOBIL.
''','Công thức đầu là mô hình tham khảo kinh điển; không khẳng định tất cả chi tiết của MOBIL nguyên bản đều có trong plugin. Trong project allowed_lanes thường chỉ chứa lane hiện tại. Bộ lọc mở một lane kề khi vượt điều kiện. Gần nút, điều kiện dùng khoảng cách từ tâm > distance_to_intersection_center+13 =53,5 m; với vạch dừng ở45 m, không nên nói chính xác “13 m trước vạch” như bản thô. Gần merge bị khóa khi distance_to_current_target <120 m.','Kesting et al. [3]; GAMA [1]; choose_safe_lane',True)

add('Phụ lục · Xe','A4 · Hình học và luật tốc độ tự triển khai',r'''
\small
\textbf{Bézier bậc 3:}\quad
$B(t)=(1-t)^3P_0+3(1-t)^2tP_1+3(1-t)t^2P_2+t^3P_3$, $t\in[0,1]$.
\begin{itemize}
\item Dự án lấy 121 điểm để tạo đường; các control point theo hướng vào/ra.
\item Tới cua: $v_{\mathrm{cap}}=\sqrt{v_{\mathrm{cua}}^2+2bd}$ từ động học.
\item Tới vạch dừng: dùng cap bảo thủ với $\sqrt{0,2bg}$ và $g/(4\mathrm{s})$, kèm ramp tốc độ và biên dừng.
\item Theo xe cùng edge: thêm cap dựa trên $\sqrt{v_{\mathrm{trước}}^2+0,5bg}$ và giới hạn thay đổi tốc độ.
\end{itemize}
\begin{block}{Phạm vi nguồn}
Bézier là hình học; quan hệ tốc độ–quãng đường là động học. Hệ số 0,2; 0,5; 4 s và các biên là lựa chọn triển khai, không gán cho IDM/Gipps.
\end{block}
''','Không dùng công thức speed cap như lời hứa không va chạm trong mọi điều kiện. Nó kết hợp với driving skill và phản ứng theo bước. Việc chặn nhầm xe khác làn đã được sửa bằng xét chồng lấn khoảng lane thấp nhất tới thấp nhất+num_lanes_occupied−1. Hình rẽ phải trong bản thô ghi 15 km/h như mức chung là thiếu chính xác: cap 15 chỉ kích hoạt khi xe vào phạm vi tâm hẹp; road_kind right có maxspeed20 km/h. Vì vậy phần chính không dùng một số tuyệt đối cho mọi cung phải.','doan_turn; speed caps; Bézier [9]; động học [11]',True)

add('Phụ lục · Quan sát','A5 · Trạng thái bảng Q và phạm vi đếm xe',r'''
\small
\begin{tabular}{@{}p{6.4cm}p{5.8cm}@{}}\toprule
Khóa bảng Q (6 thành phần) & Giá trị\\\midrule
Queue thẳng trục hiện tại / trục kia & Mỗi queue: 0, 1–4, từ 5 trở lên\\
Có xe trái chờ mỗi trục? & Hai cờ 0/1\\
Xe phía thoát trục hiện tại $\ge5$? & Một cờ 0/1\\
Tuổi xanh & $<25$ s; 25–$<45$ s; từ 45 s\\\bottomrule\end{tabular}
\vspace{.3cm}
Tối đa $3\times3\times2\times2\times2\times3=216$ khóa, mỗi khóa 2 giá trị Q.\\[.2cm]
DQN dùng vector khác: thêm xe thẳng đang tới và đầu ra của cả hai trục.\\[.2cm]
Phía thoát được lọc theo road mặt đất ra và lane thấp nhất 4–11, không theo danh tính tuyến.
''','Công bằng phải được mô tả có phạm vi. Hai bộ học được dùng cùng dữ liệu chuyển tiếp nhưng có hàm đặc trưng khác nhau và update rule khác. Đây là so sánh hai cấu hình cụ thể, không phép thử chỉ thay đúng một yếu tố “có mạng hay không”. Trạng thái chưa có trong bảng được xem là [0,0], tie argmax chọn hành động 0; chưa gặp không có nghĩa chương trình không chạy được.','tabular_key; features; observe_benchmark_movements',True)

add('Phụ lục · DQN','A6 · Loss, gradient và Adam',r'''
\small
Với $e=Q_\theta(s,a)-y$, Huber (Smooth L1, $\beta=1$):
\[L(e)=\begin{cases}\tfrac12e^2,&|e|<1\\|e|-\tfrac12,&|e|\ge1\end{cases}\]
Loss minibatch là trung bình 64 mẫu. Backpropagation tính $g=\nabla_\theta L$; chuẩn gradient được chặn ở 10.
\[m_t=\beta_1m_{t-1}+(1-\beta_1)g_t,\quad
v_t=\beta_2v_{t-1}+(1-\beta_2)g_t^2\]
\[\hat m_t=\frac{m_t}{1-\beta_1^t},\quad \hat v_t=\frac{v_t}{1-\beta_2^t},\quad
\theta_t=\theta_{t-1}-\eta\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon_{\mathrm{Adam}}}\]
$\eta=3\times10^{-4}$; $\beta_1=0,9$, $\beta_2=0,999$, $\epsilon_{\mathrm{Adam}}=10^{-8}$ (mặc định PyTorch).\\[.1cm]
$\epsilon_{\mathrm{Adam}}$ chống chia cho 0; khác $\varepsilon$ khám phá.
''','Phần chính chỉ cần hiểu loss là sai lệch, gradient là hướng sửa và Adam là quy tắc sửa. Huber gần 0 giống bình phương, khi sai số lớn tăng tuyến tính để giảm ảnh hưởng mẫu cực trị. Gradient clipping giới hạn chuẩn vector gradient, không giới hạn mỗi trọng số nằm trong [−10,10]. Không gọi θ←θ−η∇L là công thức Adam chính xác.','Kingma & Ba [8]; fair_benchmark.py: learn; PyTorch Adam/SmoothL1Loss [10]',True)

add('Phụ lục · DQN','A7 · Từ điển thuật ngữ để trả lời hỏi đáp',r'''
\small
\begin{tabular}{@{}p{3.3cm}p{9.1cm}@{}}\toprule
Thuật ngữ & Giải thích\\\midrule
Neuron / lớp ẩn & Phép biến đổi số; không phải xe hay nhánh đường\\
Tensor & Mảng số nhiều chiều PyTorch dùng để tính toán\\
Forward pass & Tính từ đầu vào tới điểm Q bằng trọng số hiện tại\\
Backpropagation & Tính gradient của loss ngược qua các phép biến đổi\\
Learning rate & Mức điều chỉnh tham số trong một update\\
Batch / minibatch & Nhóm mẫu kinh nghiệm dùng chung cho một update\\
Replay buffer & Vùng nhớ lưu transition để lấy mẫu lại\\
Target network & Bản sao thay đổi chậm để tính mục tiêu học\\
Inference & Chọn hành động với mô hình đã có\\
Checkpoint & Gói trạng thái lưu trên đĩa để nạp hoặc tiếp tục học\\\bottomrule\end{tabular}
''','Kết hợp bảng này với slide định nghĩa step, decision, transition, episode, update và slide epsilon. Trong replay, một transition có thể được học nhiều lần. Trong batch rollout, actor là snapshot của chính sách. “Epoch” thường chỉ một lượt qua dataset cố định; ở pipeline này không dùng epoch làm đơn vị ngân sách.','Thuật ngữ theo triển khai fair_benchmark.py; [5], [6], [8]',True)

add('Phụ lục · Nguồn','A8 · Nguồn mô hình giao thông',r'''
\small
\begin{enumerate}
\item[\textbf{[1]}] \href{https://gama-platform.org/wiki/UsingDrivingSkill}{GAMA — Driving Skill}. Saval et al. (2023), \href{https://doi.org/10.1371/journal.pone.0281658}{Dealing with mixed and non-normative traffic}, PLOS ONE.
\item[\textbf{[2]}] Treiber, Hennecke \& Helbing (2000). \href{https://doi.org/10.1103/PhysRevE.62.1805}{Congested traffic states in empirical observations and microscopic simulations}. Physical Review E 62, 1805–1824.
\item[\textbf{[3]}] Kesting, Treiber \& Helbing (2007). \href{https://doi.org/10.3141/1999-10}{General lane-changing model MOBIL for car-following models}. TRR 1999, 86–94.
\item[\textbf{[4]}] Varaiya (2013). \href{https://doi.org/10.1016/j.trc.2013.08.014}{Max pressure control of a network of signalized intersections}. TR Part C 36, 177–195.
\end{enumerate}
\vspace{.25cm}Nguồn thuật toán không tự xác nhận các tỷ lệ xe, ngưỡng lách và hình học riêng của dự án.
''','Các đường liên kết mở tài liệu gốc hoặc tài liệu chính thức. Bài GAMA có ví dụ hiệu chỉnh ở Việt Nam nhưng dự án hiện tại không tự động kế thừa kết quả xác thực của bài báo. Chỉ nói kế thừa framework và cơ chế, không nói đã kiểm định bản đồ này bằng dữ liệu đó.','Nguồn gốc/nhà xuất bản; truy cập 06/10/2026',True)

add('Phụ lục · Nguồn','A9 · Nguồn học tăng cường và triển khai',r'''
\small
\begin{enumerate}
\item[\textbf{[5]}] Watkins \& Dayan (1992). \href{https://doi.org/10.1007/BF00992698}{Q-learning}. Machine Learning 8, 279–292.
\item[\textbf{[6]}] Mnih et al. (2015). \href{https://doi.org/10.1038/nature14236}{Human-level control through deep reinforcement learning}. Nature 518, 529–533.
\item[\textbf{[7]}] Bradtke \& Duff. \href{https://proceedings.neurips.cc/paper_files/paper/1994/hash/07871915a8107172b3b5dc15a6574ad3-Abstract.html}{Reinforcement Learning Methods for Continuous-Time Markov Decision Problems}. NIPS 7 (hội nghị 1994, tập in 1995).
\item[\textbf{[8]}] Kingma \& Ba. \href{https://arxiv.org/abs/1412.6980}{Adam: A Method for Stochastic Optimization}. ICLR 2015.
\item[\textbf{[9]}] \href{https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/Bezier/bezier-construct.html}{Michigan Tech — Bézier curves} (hình học).
\item[\textbf{[10]}] \href{https://docs.pytorch.org/docs/stable/generated/torch.optim.Adam.html}{PyTorch Adam}; \href{https://docs.pytorch.org/docs/stable/generated/torch.nn.SmoothL1Loss.html}{SmoothL1Loss} (triển khai).
\item[\textbf{[11]}] \href{https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration}{OpenStax — Motion with Constant Acceleration}. Cơ sở quan hệ $v^2=u^2+2as$.
\end{enumerate}
''','Các công thức reward, số lớp 64–64, epsilon, gamma theo thời gian và lịch cập nhật là cấu hình của dự án. Mnih giới thiệu cơ chế DQN; không lấy mạng Atari hoặc hàm thưởng Atari để mô tả mô hình đèn. Dữ liệu benchmark là bằng chứng tại kho mã, không phải từ các bài tham khảo này.','Nguồn gốc và tài liệu chính thức; truy cập 06/10/2026',True)

