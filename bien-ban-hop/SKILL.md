---
name: bien-ban-hop
description: Agent lập BIÊN BẢN CUỘC HỌP từ transcript (.txt .docx .vtt .srt), ghi âm (MP3 WAV M4A) hoặc video (MP4, bản ghi Google Meet/Zoom/Teams). Phiên âm trên máy, tách giọng và nhận diện người nói có căn cứ, kiểm chứng mọi trích dẫn, xuất bản in PDF A4 ≤ 4 trang, bản trình đọc web (claude.ai Artifact), Excel Action Items và email giao việc riêng từng người (chỉ gửi khi được duyệt). Dùng khi người dùng muốn "lập biên bản họp", "tóm tắt cuộc họp", "biên bản từ ghi âm/video", "giao việc sau họp", meeting minutes, action items.
---

# Agent biên bản cuộc họp (PEAS)

| | |
|---|---|
| **P – Kết quả** | Tóm tắt đúng, không bỏ sót quyết định/việc; đúng người phụ trách; mọi ý có trích dẫn nguyên văn + mốc giờ; không bịa. Hai bản: PDF A4 ≤ 4 trang và bản trình đọc web. |
| **E – Môi trường** | Thư mục trên máy, Google Drive, Gmail (connector của Claude), claude.ai Artifact. |
| **A – Hành động** | Đọc → phiên âm → nhận diện người nói → tóm tắt → kiểm chứng → ảnh dẫn chứng → xuất PDF + bản đọc → Excel → email → gửi khi được duyệt. |
| **S – Đầu vào** | Transcript, audio, video, danh sách người tham gia + email. |

**Phân vai:** script làm phần máy móc (phiên âm, tách giọng, OCR nhãn tên, kiểm chứng, chụp ảnh, dàn trang, Excel, email). **Claude** đọc hiểu bản ghi và viết `bien-ban.json`. Script CHẶN xuất bản nếu dữ liệu không kiểm chứng được.

Đọc trước khi viết biên bản: `references/lap-bien-ban.md` (quy tắc số 1: ghi sự thật, không sáng tác), `references/nguyen-tac-chung.md`, `references/mau-bien-ban.md` (Mẫu A), `references/the-thuc-nd30.md`, và `references/schema-bien-ban.md` (cấu trúc dữ liệu).

## Lệnh

```bash
PY="$LOCALAPPDATA/BienBanHop/venv/Scripts/python.exe"      # môi trường cài bởi CAI-DAT.bat
RUN=".claude/skills/bien-ban-hop/scripts/run.py"            # đường dẫn tương đối từ thư mục dự án
"$PY" $RUN chuan-bi <file> --nguoi <ds.csv | "Tên <email>; Tên 2 <email>"> --ngay-hop YYYY-MM-DD --gio-bat-dau HH:MM
"$PY" $RUN nhan-dien-lai <thu_muc_lam_viec> [--nguoi DS]     # nhận diện lại người nói, KHÔNG phiên âm lại
"$PY" $RUN dat-ten <thu_muc_lam_viec> S2 "Họ Tên"            # khi người dùng xác nhận tên người nói
"$PY" $RUN kiem-chung <thu_muc_lam_viec>
"$PY" $RUN xuat <thu_muc_lam_viec> [--mat-khau MK] [--link URL] [--khong-mo]
"$PY" $RUN email <thu_muc_lam_viec> --link <URL artifact>   # tạo lại email kèm link bản đọc
"$PY" $RUN goi-gmail <thu_muc_lam_viec> [--thu-ve EMAIL]     # tạo email/gui-gmail.json (to, subject, body, đính kèm base64)
"$PY" $RUN da-gui <thu_muc_lam_viec> --trang-thai DA_GUI|NHAP|DA_GUI_THU [--ghi-chu ...]
"$PY" $RUN tu-kiem-tra [--day-du]                            # chỉ chạy khi người dùng yêu cầu
```
Nếu `$PY` không tồn tại: bảo người dùng nhấp đúp `CAI-DAT.bat` trong thư mục skill.
Phiên âm video/ghi âm dài mất vài phút → chạy `chuan-bi` ở chế độ nền (`run_in_background`).
Sửa file trong skill bằng công cụ Edit/Write, không dùng heredoc của shell (shell tự đổi `\n`, `\r` làm hỏng mã).

## Quy trình

1. **Thu thập đầu vào** (hỏi tối thiểu): đường dẫn file (máy, hoặc tải từ Google Drive về thư mục dự án), danh sách người tham gia + email, ngày họp và giờ bắt đầu. Thiếu ngày họp vẫn chạy được, nhưng hạn tương đối ("thứ Sáu tuần sau") sẽ không quy đổi → đưa vào mục cần làm rõ.
2. **Chuẩn bị**: chạy `chuan-bi`. Kết quả trong `bien-ban/<ngày>-<tên>/`: `ban-ghi.txt` (từng đoạn `#id [mm:ss] Người nói (S1): lời`), `speakers.json` (tên + căn cứ), `cau-tu-khoa.txt`, `bien-ban.khung.json`.
3. **Người nói**: đọc phần in ra. Cụm nào "Chưa xác định" hoặc độ tin thấp → HỎI người dùng (AskUserQuestion, nêu câu nói mẫu và mốc giờ của cụm đó), rồi chạy `dat-ten`. Không tự đoán tên. Bổ sung danh sách người tham gia sau → `nhan-dien-lai --nguoi ...` (không phiên âm lại).
   - Phiên âm có thể nghe nhầm từ ("chúc" thay "chốt", "hàng chốc" thay "hạn chót"). Trích dẫn vẫn chép nguyên văn bản ghi; nội dung quyết định/việc ghi đúng nghĩa và thêm câu hỏi xác nhận vào `can_lam_ro` kèm mốc giờ. Câu "chốt" bị nghe nhầm sẽ không bị bộ lọc từ khoá bắt → tự rà các câu mang ý chốt/giao việc.
4. **Viết `bien-ban.json`** (copy từ `bien-ban.khung.json`) theo `references/schema-bien-ban.md`:
   - Trích dẫn: chép NGUYÊN VĂN một đoạn liên tục trong `ban-ghi.txt`, kèm `seg` (#id). Không sửa chính tả, không ghép câu.
   - Phân biệt *ý kiến* (ai nêu) và *quyết định* (chủ trì chốt). Không có chốt → `quyet_dinh: []`.
   - Việc: `phu_trach` chỉ khi có người TỰ NHẬN ("em sẽ…", "tôi nhận") hoặc ĐƯỢC NÊU TÊN trong câu trích; không rõ → `null`. `han` chỉ khi thời hạn được nói ra, ghi cụm gốc vào `han_goc`.
   - Mọi câu trong `cau-tu-khoa.txt` phải xuất hiện trong trích dẫn hoặc trong `bo_qua` kèm lý do.
   - Thiếu thông tin (địa điểm, cơ quan, giờ kết thúc…) → để `null`, script in `[CHƯA RÕ]`; thêm câu hỏi vào `can_lam_ro`.
   - PDF tối đa 4 trang: tóm tắt 4–6 ý ≤ 25 từ; diễn biến 5–10 mục, mỗi mục 1–2 câu ≤ 40 từ.
5. **Xuất**: `xuat`. Nếu **BỊ CHẶN**: đọc lỗi, sửa `bien-ban.json` bằng cách bỏ/ghi chưa rõ những gì không có căn cứ (KHÔNG thêm chữ vào trích dẫn cho khớp), chạy lại. Hỏi người dùng có muốn khoá bản đọc bằng mật khẩu không (`--mat-khau`; không lưu mật khẩu vào file nào).
6. **Trình bày kết quả**: PDF và bản đọc được mở tự động; gửi PDF cho người dùng xem (SendUserFile). Khi người dùng cần link: đăng `bien-ban-doc.html` lên claude.ai Artifact (riêng tư, `icon: "note"`, đăng lại cùng đường dẫn file để giữ link), đưa link và nói rõ chỉ họ mở được cho đến khi chia sẻ; sau đó `email --link <URL>` để email có link.
7. **Email giao việc** (KHÔNG BAO GIỜ tự gửi):
   - Đọc `email/danh-sach-email.json`. Thiếu email ai → hỏi bổ sung trước, sửa `nguoi_tham_gia` trong `bien-ban.json`, chạy lại `xuat` (hoặc `kiem-chung` + `email`).
   - Kiểm tra Gmail connector: ToolSearch "gmail" (công cụ `send_message`, `create_draft`). Chưa có → gọi `mcp__mcp-registry__search_mcp_registry` ["gmail"] rồi `suggest_connectors` để hiện nút Connect, và hướng dẫn: claude.ai → Settings → Connectors → Gmail → Connect. Trong lúc chờ, các file `.eml` trong `email/` mở bằng Outlook/Thunderbird để gửi tay.
   - Nếu địa chỉ là mẫu/giả (`@example.com`) hoặc người dùng muốn thử: hỏi có gửi về hộp thư của chính họ không (`goi-gmail --thu-ve <email của họ>`; tiêu đề tự thêm "[THỬ – cho <tên>]").
   - Hiển thị TOÀN BỘ `email/xem-truoc-email.md`, rồi hỏi bằng AskUserQuestion: **Gửi ngay / Chỉ tạo nháp / Sửa / Chưa gửi**. Chọn người nhận KHÔNG phải là đồng ý gửi.
   - Sau câu trả lời rõ ràng: chạy `goi-gmail`, đọc `email/gui-gmail.json`, mỗi phần tử gọi `send_message` (hoặc `create_draft`) với đúng `to`, `subject`, `body` (văn bản thuần) và `attachments` (filename, mimeType, content base64). Rồi chạy `da-gui --trang-thai ...` và báo link `viewUrl` của từng thư.
   - Việc không có hạn thì không có file lịch `.ics`; file `.ics` ghi CRLF chuẩn iCalendar, nhắc trước `viec.nhac_truoc_ngay` ngày.
8. **Kết thúc** bằng bảng **Mục cần làm rõ** (mọi `[CHƯA RÕ]` + câu hỏi cụ thể) và bảng **Việc cần làm** (dán được vào Zalo/Excel).

## Đầu ra trong thư mục làm việc

`bien-ban.pdf` · `bien-ban-doc.html` · `viec-can-lam.xlsx` · `email/` (`.eml`, `phieu-giao-viec-*.xlsx`, `lich-nhac-han-*.ics`, `xem-truoc-email.md`) · `kiem-chung.md` · `ban-ghi.txt` · `anh/`.

## Lỗi thường gặp

| Thông báo | Xử lý |
|---|---|
| File rỗng / hỏng / sai định dạng | Báo người dùng, xin file khác. Không đoán nội dung. |
| `KHÔNG tìm thấy câu trích` | Chép lại nguyên văn từ `ban-ghi.txt` hoặc bỏ ý đó. |
| `không được nêu tên… không tự nhận việc` | Đặt `phu_trach: null` + thêm vào `can_lam_ro`. |
| `thời hạn … không xuất hiện` | Bỏ `han`, ghi vào `can_lam_ro`. |
| `Có thể BỎ SÓT` | Đưa câu đó vào biên bản, hoặc thêm vào `bo_qua` với lý do cụ thể. |
| Bản in vượt 4 trang | Rút gọn tóm tắt/diễn biến trong `bien-ban.json`, chạy lại. |
