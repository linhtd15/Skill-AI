# Kết quả tự kiểm thử (22/22 đạt) – 24/11/2026 20:59

| PEAS | Tình huống | Kết quả | Chi tiết | Giây |
|---|---|---|---|---|
| S | Transcript .txt có mốc giờ + tên | ĐẠT | 23 đoạn, 4 người nói (căn cứ: nhãn trong transcript) | 0.4 |
| S | Transcript .vtt (nhãn <v Tên>) | ĐẠT | 23 cue, mốc #15 = 99.0s | 0.0 |
| S | Transcript .docx | ĐẠT | 23 đoạn | 0.3 |
| P | Xuất đủ PDF + bản đọc + Excel + email | ĐẠT | PDF 2 trang; Excel có danh sách chọn + tô đỏ + sheet theo người; 2 .eml, 2 .ics đúng chuẩn CRLF | 1.8 |
| P | Trích dẫn bịa → chặn | ĐẠT | Chặn: Quyết định QĐ1: KHÔNG tìm thấy câu trích “chốt ngân sách sáu trăm triệu đồng” trong bản ghi (đoạn #11). | 0.0 |
| P | Trích dẫn bịa không có seg → chặn | ĐẠT | Chặn: Chủ đề T2: KHÔNG tìm thấy câu trích “doanh số tăng gấp đôi” trong bản ghi. | 0.0 |
| P | Gán người phụ trách sai → chặn | ĐẠT | Chặn: Việc V3: “Nguyễn Thu Hà” không được nêu tên trong dẫn chứng và cũng không tự nhận việc. | 0.0 |
| P | Thời hạn không được nói → chặn | ĐẠT | Chặn: Việc V3: thời hạn “cuối tháng” không xuất hiện trong câu trích dẫn → không được nói trong cuộc họp. | 0.0 |
| P | Quy đổi hạn sai → chặn | ĐẠT | Chặn: Việc V1: “thứ Sáu tuần sau” (họp ngày 2026-11-19) = 2026-11-27, khác 'han' = 2026-11-20. | 0.0 |
| P | Hạn tương đối khi chưa biết ngày họp → chặn | ĐẠT | Chặn: Việc V1: “thứ Sáu tuần sau” là ngày tương đối/thiếu năm nhưng chưa biết ngày họp (meta.ngay_hop). | 0.0 |
| P | Bỏ sót câu chứa từ khoá → chặn | ĐẠT | Chặn: Có thể BỎ SÓT – câu chứa từ khoá chưa đưa vào biên bản và chưa ghi lý do bỏ qua: #3 [00:22] Phạm Ngọc Lan: “Dạ | 0.0 |
| P | Bỏ qua không ghi lý do → chặn | ĐẠT | Chặn: bo_qua đoạn #3: thiếu lý do bỏ qua. | 0.0 |
| P | Sửa biên bản sau kiểm chứng → chặn | ĐẠT | bien-ban.json đã bị sửa sau khi kiểm chứng. Hãy chạy kiểm chứng lại. | 0.0 |
| A | Lọc câu ảo giác Whisper | ĐẠT | Nhận diện 3/3 câu ảo giác; trích câu ảo giác → chặn | 0.0 |
| S | File rỗng | ĐẠT | File rỗng (0 byte): rong.mp3 | 0.0 |
| S | File video hỏng | ĐẠT | File hỏng hoặc không phải media hợp lệ: hong.mp4. ffmpeg không đọc được. | 0.1 |
| S | Sai định dạng (.pdf) | ĐẠT | Định dạng '.pdf' không được hỗ trợ. Hãy dùng transcript (.txt .docx .vtt .srt), âm thanh (.mp3 .wav .m4a) hoặc video (.mp4). | 0.0 |
| S | Transcript rỗng nội dung | ĐẠT | File transcript không có nội dung: trong.txt | 0.0 |
| E | Thiếu email → không tạo thư, yêu cầu bổ sung | ĐẠT | Không tạo .eml cho người thiếu email; xem trước ghi ⚠ THIẾU EMAIL; trạng thái CHUA_GUI | 0.0 |
| E | Khoá bản đọc bằng mật khẩu | ĐẠT | Không lộ nội dung/mật khẩu; giải mã AES-GCM/PBKDF2 đúng | 0.9 |
| E | Gói gửi Gmail + ghi trạng thái gửi | ĐẠT | Gói gửi thật: 2 thư (bỏ qua người thiếu email); gửi thử: 3 thư có tiền tố [THỬ]; đính kèm base64 khớp file; ghi lịch sử gửi | 0.0 |
| A | MP3: phiên âm, minh hoạ, sóng âm, xuất | ĐẠT | Phiên âm + 4 cụm giọng; hình minh hoạ + sóng âm; PDF 3 trang | 73.8 |