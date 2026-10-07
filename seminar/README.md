# Seminar: điều khiển đèn giao thông

## Tài liệu trình bày

- `seminar.pdf`: 20 slide chính theo theme [Metropolis](https://github.com/matze/mtheme). Dùng để trình chiếu.
- `speaker_notes.pdf`: lời dẫn của bản nháp 24 slide; cần cập nhật nếu dùng cùng bản trình chiếu hiện tại.
- `appendix.pdf`: 13 slide hỏi đáp, gồm lịch 8 pha, đặc trưng đầu vào, đồ thị validation, công thức chi tiết và nguồn.
- `sources.md`: liên kết tới tài liệu GAMA và các nguồn nghiên cứu.

Mạch nói của phần chính: bài toán → mạng đường và xe → thời điểm quyết định → Fixed-Time, Max-Pressure, Q-Learning, DQN → hàm thưởng và huấn luyện → seed dùng chung → benchmark sáu chỉ số → đo rủi ro và giới hạn. Slide 8 chỉ nêu tên bốn phương pháp; slide 9 giải thích Fixed-Time. Q-Learning được trình bày trên hai slide: bảng key–value lưu trong checkpoint `.pt` và sáu thành phần của key (tối đa 216 tình huống). TTC, TIT, PET, DRAC và phanh gấp đã có trong mô phỏng, nhưng chưa có bảng so sánh an toàn ghép cặp cho cả bốn phương pháp.

## Chỉnh sửa

`seminar.tex` là nguồn của slide chính. Dùng `format_tex.py` để định dạng lại mà không thay nội dung. `speaker_notes.md` là nguồn lời dẫn của bản nháp cũ; có thể xuất lại PDF bằng Pandoc và XeLaTeX sau khi đồng bộ với 20 slide hiện tại. `build_content.py` là generator của bản cũ: nó ghi bản nháp slide và lời dẫn ra các file mang hậu tố `_generated`, nên không ghi đè bản đã chỉnh tay. Nó vẫn có thể sinh lại `appendix.tex`.

Từ thư mục gốc dự án:

```sh
python3 seminar/format_tex.py seminar/seminar.tex
```

Từ thư mục `seminar/`:

```sh
xelatex -interaction=nonstopmode -halt-on-error seminar.tex
xelatex -interaction=nonstopmode -halt-on-error seminar.tex
xelatex -interaction=nonstopmode -halt-on-error appendix.tex
pandoc speaker_notes.md -f markdown -s -t latex -o speaker_notes.tex -H notes_header.tex -V documentclass=article -V fontsize=11pt -V geometry:margin=2cm -V mainfont='Helvetica Neue'
xelatex -interaction=nonstopmode -halt-on-error speaker_notes.tex
```

Các file `.sty` ở thư mục seminar được sinh từ mã theme chính thức lưu trong `vendor/mtheme/`. Font Fira Sans và giấy phép ở `fonts/`; `pgfopts.sty` được sinh từ mã CTAN trong `vendor/pgfopts/`. Hình vector và biểu đồ được sinh bằng `make_figures.py` từ dữ liệu benchmark ở `../comparison_results/fair_benchmark_20261005_final/`.

Nguồn mã và nguồn nghiên cứu được ghi trong lời dẫn, `sources.md` và PDF phụ lục; phần chân slide trình chiếu chỉ còn số trang.
