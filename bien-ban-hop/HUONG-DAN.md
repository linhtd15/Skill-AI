# Hướng dẫn sử dụng Agent biên bản cuộc họp

Agent đọc bản ghi cuộc họp (transcript, ghi âm hoặc video), viết biên bản có trích dẫn nguyên văn và mốc giờ, rồi xuất:

| Đầu ra | Tên file | Dùng để |
|---|---|---|
| Bản in A4 (≤ 4 trang) | `bien-ban.pdf` | In, trình ký |
| Bản trình đọc web | `bien-ban-doc.html` | Đọc trên điện thoại; đăng lên claude.ai để lấy link chia sẻ |
| Bảng việc cần làm | `viec-can-lam.xlsx` | Theo dõi trạng thái, tô đỏ việc quá hạn, tổng hợp theo người |
| Email giao việc | thư mục `email/` | Mỗi người một thư, kèm phiếu giao việc Excel và lịch nhắc hạn `.ics` |

Tất cả nằm trong `bien-ban/<ngày họp>-<tên file>/` của thư mục dự án.

## 1. Cài đặt (một lần)

1. Mở thư mục `.claude\skills\bien-ban-hop\`.
2. **Nhấp đúp `CAI-DAT.bat`**. Chờ đến khi hiện "CÀI ĐẶT XONG" (lần đầu tải khoảng 2 GB: Python, mô hình phiên âm Whisper, mô hình tách giọng).
3. Mọi thứ chạy trên máy, miễn phí. Ghi âm cuộc họp không gửi lên dịch vụ phiên âm nào.

## 2. Dùng hằng ngày

Tên skill: **`bien-ban-hop`**. Mở Claude Code trong thư mục `D:\Claude Code` (thư mục chứa `.claude\skills\bien-ban-hop`) rồi:

- gõ **`/bien-ban-hop`** kèm yêu cầu, ví dụ `/bien-ban-hop D:\Ghi am\hop.mp4, họp 19/11/2026 lúc 9:00, người tham gia trong nguoi-tham-gia.csv`; hoặc
- nói tự nhiên như "lập biên bản cuộc họp từ file …", Claude tự nhận ra và gọi skill.

Ví dụ:

> Lập biên bản cuộc họp từ file `D:\Ghi am\hop-giao-ban.mp4`. Họp ngày 19/11/2026 lúc 9 giờ. Người tham gia trong `nguoi-tham-gia.csv`.

File danh sách người tham gia (CSV, mở bằng Excel được):

```
ten,email,vai_tro
Trần Minh Hoàng,hoang@congty.vn,Giám đốc (chủ trì)
Nguyễn Thu Hà,ha@congty.vn,Marketing
```

Claude sẽ:
1. Phiên âm (video 1 giờ mất khoảng 15–30 phút trên máy thường), tách giọng, nhận tên người nói. **Ai chưa rõ tên, Claude sẽ hỏi bạn** kèm câu nói mẫu.
2. Viết biên bản, chạy **kiểm chứng tự động**. Kiểm chứng sẽ **chặn** nếu: trích dẫn không có trong bản ghi; người phụ trách không được nêu tên hoặc không tự nhận; thời hạn không được nói trong họp; còn câu "chốt / thống nhất / giao / em sẽ / trước ngày…" chưa được đưa vào.
3. Mở bản PDF và bản đọc web. Nói "cho tôi link" để đăng bản đọc lên claude.ai (riêng tư).
4. Cho bạn xem trước toàn bộ email giao việc và hỏi: **Gửi ngay / Chỉ tạo nháp / Sửa / Chưa gửi**. Không có gì được gửi nếu bạn chưa đồng ý.

## 3. Gửi email qua Gmail

Vào **claude.ai → Settings → Connectors → Gmail → Connect** (hoặc bấm nút Connect Claude hiện ra). Nếu chưa kết nối, mở file `.eml` trong thư mục `email/` bằng Outlook (nhấp đúp) để gửi tay.

- Muốn thử trước: nói "gửi thử về hộp thư của tôi". Mỗi thư được gửi về địa chỉ của bạn, tiêu đề có "[THỬ – cho <tên người nhận>]".
- Thư kèm phiếu giao việc Excel; việc có hạn thì kèm thêm file lịch `.ics` (mở để thêm vào Google Calendar/Outlook, nhắc trước 1 ngày).
- Trạng thái gửi được ghi lại trong `email/danh-sach-email.json`.

## 4. Khoá bản đọc bằng mật khẩu

Nói "khoá bản đọc bằng mật khẩu". Nội dung được mã hoá AES-GCM; người xem phải nhập mật khẩu mới đọc được. Mật khẩu không lưu trong file nào, hãy gửi riêng cho người cần đọc.

## 5. Bản trình đọc web

- Thanh công cụ dưới đáy: **Mục lục** (kèm % đã đọc) · **Tìm** (gõ không dấu, ví dụ "han" ra "hạn") · **Chia sẻ** (sao chép tóm tắt/kế hoạch để dán Zalo) · **Hiển thị** (cỡ chữ, giãn dòng, nền Giấy/Sepia/Tối).
- Màu chỉ dùng khi cần chú ý: **đỏ** = quá hạn, việc chưa có người nhận, rủi ro; **vàng** = còn ≤ 3 ngày.

## 6. Tuỳ chỉnh (`config.json`, mở bằng Notepad)

| Mục | Ý nghĩa |
|---|---|
| `co_quan_mac_dinh`, `dia_danh_mac_dinh` | In ở đầu biên bản (theo NĐ 30/2020). |
| `phien_am.mo_hinh_whisper` | `large-v3-turbo` (chính xác) hoặc `small` (nhanh, máy yếu). |
| `phien_am.cau_ao_giac` | Các câu Whisper hay "bịa" khi có nhạc nền; bị lọc và phiên âm lại. |
| `kiem_chung.tu_khoa_bat_buoc` | Từ khoá bắt buộc phải có trong biên bản hoặc được ghi lý do bỏ qua. |
| `ban_in.so_trang_toi_da` | Mặc định 4 trang. |
| `nguoi_noi.vung_nhan_ten_video` | Vùng ảnh có nhãn tên người nói trên video (mặc định góc dưới trái). |

## 7. Giới hạn cần biết

- Biên bản là **bản nháp do AI lập**. Thư ký và chủ trì cần đọc lại trước khi ký.
- Phiên âm có thể nghe nhầm từ (ví dụ "chúc" thay "chốt"). Trích dẫn giữ nguyên văn bản ghi để đối chiếu; nếu thấy sai, nghe lại đoạn đó theo mốc giờ.
- Tách giọng kém chính xác khi hai người có giọng rất giống nhau hoặc nói chồng lên nhau. Nhãn tên trên video và việc tự giới thiệu giúp nhận diện tốt hơn; khi không chắc, Agent ghi "Chưa xác định" và hỏi bạn.
- Nhận diện nhãn tên trên video dùng OCR có sẵn của Windows (tiếng Anh): tên được so khớp không dấu với danh sách người tham gia.

## 8. Kiểm tra lại sau khi sửa cấu hình

Nói với Claude: "chạy tự kiểm tra skill biên bản". Kết quả ghi ở `tests/ket-qua-kiem-thu.md`.
