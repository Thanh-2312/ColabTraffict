"""Rebuild the archived Metropolis draft without overwriting the edited talk."""
from pathlib import Path
import json, re
from copy import deepcopy
from slide_content import slides as library, cols, items, box, fig
D=Path(__file__).resolve().parent
main=[]
def take(n,title=None,body=None,extra_note=''):
 s=deepcopy(library[n-1]); s['appendix']=False
 if title:s['title']=title
 if body:s['body']=body
 if extra_note:s['note']+=' '+extra_note
 main.append(s)
 return s

take(1,'Điều khiển đèn giao thông từ dữ liệu')
take(2,'Đèn nên giữ xanh hay nhường hướng khác?',
 box('Bài toán',r'Một hướng đang vắng vẫn được xanh, trong khi hướng kia có xe chờ. Khi nào nên chuyển?')+
 items(r'\textbf{Dựng môi trường:} đường, xe hỗn hợp, luật rẽ và nhập dòng.',r'\textbf{Kết nối điều khiển:} GAMA trao đổi với Python; thử bốn phương pháp.',r'\textbf{Kiểm chứng:} huấn luyện và so sánh trên cùng nhu cầu xe.')+
 r'\vspace{.3cm}\alert{Mạch trình bày:} mô phỏng → quyết định → học → đánh giá.')
take(3,'Môi trường: một ngã tư trong mạng nhiều tầng',cols(fig('network_map','4.65cm'),items(
 r'Không gian $2.000\times2.000$ m; bốn nhánh Bắc, Nam, Đông, Tây.',
 'Mỗi nhánh có chiều vào và chiều ra; cầu vượt và hầm tách khỏi nút mặt đất.',
 r'\textbf{4 cột đèn × 2 nhóm} (thẳng/trái) = 8 nhóm tín hiệu.',
 r'\textbf{1 bộ điều khiển trung tâm} phối hợp các hướng.')),
 library[4]['note'])
take(4,'Mỗi chiều mặt đất có 16 làn con')
main[-1]['body']=main[-1]['body'].replace(
 box('Cách diễn giải','Đây là đơn vị chia nhỏ để mô phỏng xe hỗn hợp; không tương đương 16 làn ô tô vật lý.'),'')
take(8,'Sinh cùng nhu cầu xe để so sánh công bằng',cols(
 box('Tạo một lịch xe',items('Chọn seed, ví dụ 5001; tạo bộ số ngẫu nhiên từ seed đó.','Lấy mẫu loại xe, tốc độ, hướng rẽ và lane.',r'Ghi từng yêu cầu vào \texttt{demand/5001.csv}.')),
 box('Lưu và dùng lại',items('Manifest lưu danh sách seed; kết quả từng lượt lưu SHA-256 của CSV.','Cả bốn cách đèn đọc cùng file CSV cho seed 5001.','Reset GAMA bằng seed tương ứng; kiểm tra seed đã nhận.')))+r'\vspace{.25cm}Nhịp yêu cầu: Bắc/Nam 1,5 s; Đông/Tây 4,5 s. Cửa vào đầy thì yêu cầu chờ FIFO.',library[8]['note']+' '+library[6]['note']+' Script dùng random.Random(seed), sinh CSV một lần cho từng seed trong thư mục demand. Manifest lưu danh sách train/validation/test seed; metrics từng lượt lưu demand_sha256; lúc reset kiểm tra world.seed. Seed khởi tạo bộ học là 42, tách khỏi seed nhu cầu xe.')
take(10,'Xe chạy theo luật; AI chỉ điều khiển đèn',cols(
 box('IDM làm gì?',r'Cứ mỗi 0,1 giây, mỗi xe tự hỏi: \emph{“Mình nên tăng ga, giữ nguyên hay đạp phanh?”}'+items('Đường trống: tiến tới tốc độ mong muốn.','Gần xe trước: giảm tốc để giữ khoảng hở.')),
 box('GAMA hỗ trợ sẵn',items(r'Khai báo \texttt{skills: [driving]} cho loài xe.',r'Mỗi bước, reflex gọi \texttt{do drive}; driving skill tính bám xe bằng IDM.','Dự án đặt thông số từng loại xe và các luật bổ sung.')))+r'\vspace{.3cm}\[a=a_{\max}\left[1-\left(\frac{v}{v_0}\right)^\delta-\left(\frac{s^*}{s}\right)^2\right]\]\small Nguồn mô hình: Treiber, Hennecke \& Helbing (2000); tài liệu GAMA Driving Skill.',library[6]['note']+' Cần nói chính xác: skills: [driving] cung cấp kỹ năng, còn reflex move của dự án gọi do drive mỗi bước; không phải chỉ khai báo skill là xe tự chạy.')
take(11,'Lách và rẽ trái đều có điều kiện',cols(
 box('Đổi lane',items('Bộ lọc dự án kiểm tra khoảng trống trước/sau.','GAMA áp dụng cơ chế MOBIL để xét đổi lane.')),
 box('Đường rẽ trái Bézier',items(r'\textbf{Bậc 3 (cubic Bézier):} 4 điểm điều khiển $P_0,P_1,P_2,P_3$.','Pha trái xanh và lối ra trống mới được vào.')))+r'''
\vspace{.1cm}\[B(t)=(1-t)^3P_0+3(1-t)^2tP_1+3(1-t)t^2P_2+t^3P_3,\quad t\in[0,1]\]
\small Công thức Bézier chuẩn: \href{https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/Bezier/bezier-construct.html}{Michigan Technological University, CS3621}. Luật cấp vào và ngưỡng lách là của dự án.
''',library[11]['note']+' Công thức đa thức Bézier chuẩn theo bài giảng CS3621 của Michigan Technological University. Trong mã, doan_turn lấy 121 điểm t=0..1. Bốn điểm P0, P3 là đầu/cuối, P1/P2 định hình độ cong. Đây không phải công thức trích từ nghiên cứu RL.')['source']='MOBIL [3]; Michigan Tech CS3621 [9]; luật dự án'
take(14,'AI được quyết định khi nào?',cols(
 box('Giới hạn của pha xanh',items(r'\textbf{Xanh tối thiểu 10 s} (\texttt{min\_green\_cycles} = 100): trong 10 s đầu AI chưa được quyết định.','Tại 10, 15, 20, …, 55 s: hỏi lại sau mỗi 5 s.')),
 box('Hai câu trả lời',items(r'\textbf{Giữ}: xanh thêm khoảng 5 s.',r'\textbf{Chuyển}: vàng 3 s → trái 12 s → vàng 3 s → xanh trục kia.',r'\textbf{Trần 60 s}: hệ thống ép chuyển nếu AI cứ giữ xanh.')))+r'\vspace{.3cm}AI chỉ kéo dài hoặc kết thúc xanh đi thẳng; GAMA giữ thứ tự các pha còn lại.',library[14]['note'])
take(15,'Bốn phương pháp điều khiển',r'''
\vspace{1cm}
\begin{columns}[T,onlytextwidth]
\begin{column}{.48\textwidth}\centering\Large Fixed-Time\par\vspace{1cm}Q-Learning\end{column}
\begin{column}{.48\textwidth}\centering\Large Max-Pressure\par\vspace{1cm}Deep Q-Learning\end{column}
\end{columns}
''')
main[-1]['note']='Chỉ đọc tên bốn phương pháp rồi chuyển sang slide Fixed-Time. Các slide tiếp theo mới giải thích cách mỗi phương pháp ra quyết định.'
take(15,'Fixed-Time: chuyển đèn theo đồng hồ',cols(
 box('Quy tắc',items('Không đếm xe để quyết định.','Xanh đi thẳng Bắc–Nam: khoảng 30 s.','Chạy các pha vàng và rẽ trái cố định; rồi xanh Đông–Tây khoảng 30 s.','Lặp lại theo cùng lịch.')),
 box('Ví dụ',r'Bắc–Nam đã xanh 30 s.\\Dù Đông–Tây có 2 xe hay 20 xe, bộ điều khiển vẫn ra lệnh chuyển.'))+r'\vspace{.25cm}Trong benchmark, pha xanh thẳng dài \textbf{30,1 s} do bước giao tiếp chung 0,1 s.',
 'Fixed-Time là mốc cơ sở: cùng thứ tự tám pha, xanh thẳng 30,1 giây; vàng 3 giây và trái 12 giây. Không có huấn luyện và không dùng số xe để chọn thời điểm. Đây là một cấu hình fixed-time cụ thể, không chứng minh mọi lịch cố định đều kém. Mốc 30,1 giây là 30 giây cộng bước handshake 0,1 giây của giao diện chung.')
take(16,'Max-Pressure: giải tỏa phía đang dồn xe')
take(17,'Học tăng cường: học từ hậu quả của quyết định')
take(18,'Q-Learning ghi kinh nghiệm vào một bảng')
take(19,'DQN dùng mạng nơ-ron để tính hai điểm Q')
main[-1]['body']+=r'\par\vspace{.2cm}{\small\textbf{11 số đầu vào:} xe thẳng chờ, đang tới, chờ rẽ trái, phía thoát (mỗi nhóm theo hai trục); tuổi xanh và hai cờ pha. Không nhập danh tính từng xe.}'
main[-1]['note']+=' Slide quan sát riêng đã bỏ. Nhấn mạnh mô phỏng biết từng xe nhưng DQN chỉ nhận vector 11 số đếm đã chuẩn hóa trong vùng cảm biến 190,5 m, cùng pha và tuổi xanh. Reward dùng xe dừng toàn mạng.'
take(22,'Từ 11 số đầu vào đến một lệnh đèn',extra_note=library[19]['note'])
take(21,'CPU tính, RAM giữ dữ liệu, ổ đĩa lưu mô hình',cols(
 box('Khi đang chạy',items(r'\textbf{GAMA:} mô phỏng xe và gom quan sát.',r'\textbf{Python/PyTorch trên CPU:} tính điểm Q và cập nhật mạng.',r'\textbf{RAM:} giữ trạng thái xe, mạng và kinh nghiệm.')),
 box('Khi lưu và nạp',items(r'\textbf{WebSocket:} trao đổi quan sát/lệnh giữa GAMA và Python.',r'\textbf{Checkpoint .pt trên đĩa:} lưu trọng số và tiến độ học.','Chạy lại: nạp checkpoint vào RAM rồi dùng CPU tính.'))),library[27]['note'])
take(23,'Hàm thưởng: xe chờ càng lâu, phạt càng nhiều')
take(24,'Một episode là một lượt mô phỏng')
take(25,'Thử hành động, lưu trải nghiệm, rồi học lại',cols(
 box('Thu thập trải nghiệm',items(r'Khi học, xác suất $\varepsilon$ cho phép thử hành động ngẫu nhiên.',r'Lưu $(s,a,r,s^\prime,\mathrm{done},\Delta t)$ trong \textbf{replay buffer} (bộ nhớ kinh nghiệm).','Cả Q và DQN học từ dữ liệu thu chung.')),
 box('Cập nhật DQN',items(r'Lấy \textbf{minibatch}: 64 bản ghi ngẫu nhiên.','Mạng online được sửa; mạng target là bản sao để tính mục tiêu.','Sao sang target mỗi 100 lần cập nhật.')))+r'\vspace{.2cm}\alert{Khi kiểm tra:} tắt khám phá và giữ nguyên bảng Q/trọng số.',library[26]['note'])
take(26,'Mạng học bằng cách sửa dự đoán sai')
take(29,'Đánh giá bằng những lượt chưa dùng để học')
main[-1]['body']=main[-1]['body'].replace('Cùng file nhu cầu, horizon, lịch đèn và luật xe cho từng seed test.','Cùng yêu cầu xe, thời gian mô phỏng, lịch pha và luật di chuyển.').replace('Seed thực tế được đọc lại; JVM mới cho mỗi lượt.','Chọn mô hình bằng validation; giữ test cho đánh giá cuối.').replace('Kiểm tra hash chính sách, số yêu cầu và lưu toàn bộ log.','Khi test: giữ nguyên mô hình, không học thêm hoặc thử ngẫu nhiên.')
take(31,'DQN giảm hàng đợi trong bộ kiểm thử này')
take(32,'Kết quả tốt hơn có giới hạn',cols(
 box('Điều quan sát được',items('DQN: 12,65 xe dừng trung bình; giảm 47,7% so với Fixed-Time.','Xe hoàn thành: DQN 243,6; Fixed-Time 228,6.','DQN thấp hơn Q khoảng 0,58 xe.')),
 box('Điều cần kiểm chứng thêm',items('DQN tốt nhất ở 3/5 seed; kém nhất ở seed 5003.','Khoảng 1.044–1.045 yêu cầu còn ngoài mạng cuối lượt.','Một lần huấn luyện, năm seed test chưa đủ kết luận phổ quát.'))),library[32]['note'])
take(34,'Từ mô phỏng xe đến bộ đèn biết học')
assert len(main)==24
# Detail belongs in a separate PDF, available during Q&A.
appendix=[deepcopy(library[i-1]) for i in [6,20,30,32,35,36,37,38,39,40,41,42,43]]
for i,s in enumerate(appendix,1):
 s['appendix']=True
 s['title']=f'A{i:02d} · '+re.sub(r'^A\d+ · ','',s['title'])

preamble=r'''% !TEX program = xelatex
% Generated by build_content.py. Actual upstream Metropolis theme, vendored locally.
\documentclass[aspectratio=169,10pt]{beamer}
\usepackage{fontspec,amsmath,amssymb,booktabs,array,tikz,graphicx}
\usetheme[progressbar=frametitle,numbering=fraction,sectionpage=none,block=transparent]{metropolis}
\usetikzlibrary{positioning,arrows.meta}
\setsansfont{FiraSans}[Path=fonts/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Italic]
\setmainfont{FiraSans}[Path=fonts/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Italic]
\setmonofont{Menlo}[Scale=.8]
\definecolor{navy}{HTML}{23373B}
\definecolor{teal}{HTML}{168A85}
\definecolor{blue}{HTML}{2879B8}
\definecolor{purple}{HTML}{8154B8}
\definecolor{muted}{HTML}{68798B}
\definecolor{wash}{HTML}{EFF5F7}
\setbeamerfont{frametitle}{size=\large}
\setbeamerfont{block title}{size=\normalsize,series=\bfseries}
\setbeamerfont{block body}{size=\normalsize}
\setbeamersize{text margin left=.65cm,text margin right=.65cm}
\setlength{\parskip}{.1cm}
\makeatletter
\expandafter\patchcmd\csname beamer@@tmpl@title page\endcsname{\paperheight}{\dimexpr\paperheight-1cm\relax}{}{}
\makeatother
\renewcommand{\arraystretch}{1.12}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\title{Điều khiển đèn giao thông\\từ dữ liệu}
\subtitle{Mô phỏng GAMA và bốn phương pháp điều khiển}
\date{}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=teal,pdftitle={Điều khiển đèn giao thông — Seminar}}
\begin{document}
'''
def esc(s):
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 return s.replace('←',r'$\leftarrow$')
def document(ss,title=False):
 parts=[preamble]
 for i,s in enumerate(ss):
  if title and i==0:
   parts += [r'\begin{frame}[plain]\titlepage\end{frame}'];continue
  parts += [r'\begin{frame}{'+s['title']+'}',r'\relax',re.sub(r'(?<!\\)%',r'\\%',s['body']).replace('p{','P{').replace('→',r'$\rightarrow$').replace(r'\end{tabular}',r'\end{tabular}\par'),r'\end{frame}']
 parts.append(r'\end{document}')
 return '\n'.join(parts)+'\n'
(D/'seminar_generated.tex').write_text(document(main,True))
(D/'appendix.tex').write_text(document(appendix))
notes=['# Lời dẫn seminar — Metropolis','', '24 slide chính, khoảng 25 phút. PDF phụ lục riêng chỉ mở khi hỏi đáp.','']
bridges={2:'Trước hết cần có một thế giới mô phỏng để thử quyết định này.',4:'Trên hạ tầng đó, xe được đưa vào và di chuyển như thế nào?',7:'Xe đã có luật di chuyển. Bây giờ chuyển sang phần bộ đèn được biết và được làm.',9:'Cùng hai lựa chọn ấy, bốn phương pháp sẽ quyết định khác nhau.',11:'Max-Pressure dùng một luật viết sẵn. Hai phương pháp tiếp theo học từ trải nghiệm.',13:'Nếu không muốn tra bảng cho từng tình huống, có thể dùng một hàm tính điểm.',16:'Máy đã tính được điểm Q; câu hỏi tiếp theo là lấy tiêu chí nào để dạy nó?',17:'Có điểm phạt rồi, ta tổ chức các lượt luyện tập như thế nào?',20:'Sau khi học, cần đo trên các lượt mới để xem cách chọn đèn có thực sự tốt hơn.',23:'Kết lại, đóng góp của dự án nằm ở chuỗi triển khai và kiểm chứng này.'}
for i,s in enumerate(main,1):
 if i in bridges:s['note']+=' Chuyển ý: '+bridges[i]
for label,ss in [('Phần trình chiếu chính',main),('Phụ lục hỏi đáp',appendix)]:
 notes += ['# '+label,'']
 for i,s in enumerate(ss,1):notes += [f"## {'Slide' if ss is main else 'Phụ lục'} {i:02d} — {s['title']}",'',s['note'],'',f"**Đối chiếu:** {s['source']}",'']
(D/'speaker_notes_generated.md').write_text('\n'.join(notes)+'\n')
(D/'slide_manifest_generated.json').write_text(json.dumps({'main':[{k:v for k,v in s.items() if k!='body'} for s in main],'appendix':[{k:v for k,v in s.items() if k!='body'} for s in appendix]},ensure_ascii=False,indent=2)+'\n')
article=r'''\documentclass[11pt,a4paper]{article}
\usepackage{fontspec,geometry,hyperref,parskip}
\geometry{margin=2cm}\emergencystretch=2em
\setmainfont{Helvetica Neue}\setmonofont{Menlo}
\hypersetup{colorlinks=true,urlcolor=blue}
\title{Lời dẫn seminar — Metropolis\\Điều khiển đèn giao thông từ dữ liệu}
\date{06/10/2026}
\begin{document}\maketitle
24 slide chính, khoảng 25 phút. Phụ lục nằm trong PDF riêng để mở khi hỏi đáp. Lời dẫn giải thích sâu hơn chữ trên slide; các câu chuyển ý giúp giữ mạch kể.
'''
for label,ss in [('Phần trình chiếu chính',main),('Phụ lục hỏi đáp',appendix)]:
 article+='\n'+r'\section*{'+label+'}\n'
 for i,s in enumerate(ss,1):article+='\n'+r'\subsection*{'+esc(f"{i:02d} — {s['title']}")+'}\n'+esc(s['note'])+'\n\n'+r'{\small\textbf{Đối chiếu:} '+esc(s['source'])+'}\n'
article+=r'\end{document}'
(D/'speaker_notes_generated.tex').write_text(article+'\n')
print(f'{len(main)} main slides; {len(appendix)} separate appendix slides')
