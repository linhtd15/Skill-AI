---
name: kham-suc-khoe-thu-muc
description: Khám sức khỏe một thư mục ở chế độ CHỈ ĐỌC và tạo báo cáo HTML trực quan - thống kê file theo loại (biểu đồ vòng), năm chỉnh sửa (cột chồng theo loại), thư mục, 10 file nặng nhất (làm nổi bật kèm nhãn đề xuất), nhóm file trùng nội dung giải thích theo nguyên nhân kèm đường dẫn và dung lượng tiết kiệm, đề xuất dọn dẹp và ước tính dung lượng giải phóng. Dùng khi người dùng muốn "khám sức khỏe", phân tích, kiểm kê, tìm file trùng, file nặng hoặc dọn dẹp một thư mục/ổ đĩa (folder health check, disk usage, duplicate files report). Không bao giờ xóa hay sửa file gốc.
argument-hint: "[đường dẫn thư mục]"
---

# Khám sức khỏe thư mục

Phân tích một thư mục và tạo báo cáo HTML tự chứa (mở offline được, có giao diện sáng/tối).
Mọi bước đều **chỉ đọc**: không xóa, di chuyển, đổi tên, đổi ngày hay ghi bất cứ thứ gì vào thư mục được khám.

Các file của skill (đường dẫn tương đối với thư mục chứa SKILL.md này):
- `scripts/scan.ps1` — quét chỉ đọc → JSON. Từ chối nếu `-Out` nằm trong `-Root`.
- `scripts/build-report.ps1` — nhúng JSON vào `assets/template.html` → báo cáo HTML. Từ chối ghi vào thư mục đã quét. `-Open` để mở bằng trình duyệt mặc định.
- `tests/run-tests.ps1` — bộ kiểm thử trên dữ liệu mẫu tự sinh trong %TEMP%.

## Quy trình

1. **Xác định thư mục.** Lấy từ đối số (`$ARGUMENTS`); nếu trống thì hỏi người dùng. Kiểm tra thư mục tồn tại.
2. **Quét** (PowerShell; có thể mất vài phút với thư mục lớn — dùng timeout dài):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\scan.ps1" -Root "<thư mục>" -Out "<scratchpad>\scan.json"
   ```
   `-Out` phải ở ngoài thư mục được quét (scratchpad hoặc %TEMP%).
3. **Dựng và mở báo cáo** — đặt trong thư mục làm việc của phiên (hoặc nơi người dùng chỉ định), **không** đặt trong thư mục được quét. Tên mặc định: `bao-cao-suc-khoe-<tên thư mục>.html`.
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\build-report.ps1" -Data "<scratchpad>\scan.json" -Out "<cwd>\bao-cao-suc-khoe-<tên>.html" -Open
   ```
4. **Kiểm tra hiển thị.** Biểu đồ được vẽ bằng JavaScript nội tuyến. Khung trình duyệt tích hợp của app mở `file://` dạng ảnh tĩnh, không chạy script — nếu cần tự kiểm tra, phục vụ file qua một server localhost tạm (ví dụ Node `http.createServer` trả về file) rồi xem bằng trình duyệt tích hợp; dọn server/cấu hình tạm sau khi xong. Trình duyệt mặc định của người dùng chạy bình thường.
5. **Tóm tắt trong chat** (ngắn gọn, tiếng Việt): tổng file/dung lượng; nhóm loại và năm nổi bật; 10 file nặng nhất; số nhóm trùng và phần dư; bảng đề xuất (an toàn / tùy chọn) với tổng ước tính giải phóng; lưu ý bảo mật (chỉ xét theo tên file, không mở nội dung). Đọc số liệu từ `scan.json` bằng PowerShell để trích dẫn chính xác, không ước đoán.

## Nội dung báo cáo

- KPI: tổng dung lượng, phần dư do trùng, giải phóng an toàn, thêm nếu lưu trữ ngoài; thanh chồng các hạng mục dọn dẹp.
- **Theo loại file**: biểu đồ vòng theo nhóm công dụng (Video, Bản ghi màn hình, Log, Cache/tạm, Âm thanh, Ảnh, Tài liệu, Khác — màu cố định theo nhóm) + bảng; thanh chi tiết theo đuôi file, đổi qua lại dung lượng/số file.
- **Theo năm chỉnh sửa**: cột chồng theo nhóm loại, tooltip phân rã, nhận xét năm chiếm ưu thế và file cũ.
- **10 file nặng nhất** (khung nổi bật): hạng, tên, đường dẫn, thanh tỷ lệ tô màu theo nhóm, % tổng, ngày sửa, nhãn đề xuất (xóa / bản trùng / lưu trữ ngoài) và nhóm trùng liên quan.
- **Nhóm file trùng** (SHA-256 trên các file cùng kích thước) giải thích **theo nguyên nhân**, mỗi nhóm có số #, đường dẫn mọi bản với nhãn GIỮ/BỎ/TÙY và dung lượng tiết kiệm nếu chỉ giữ một bản:
  1. Bản sao ngoài thư mục dự án (`*.tscproj`/`*.cmproj`) — an toàn cao, giữ bản trong dự án.
  2. Thư mục bị lồng trùng tên (`X\X\`) — an toàn cao, giữ bản cấp ngoài.
  3. Bản sao rải rác — kiểm tra trước.
  4. Cùng tài nguyên trong nhiều dự án — rủi ro, xóa làm dự án thiếu media.
  5. Cache trùng — xử lý bằng xóa cache.
  6. Bản tự lưu/sao lưu — nên giữ.
  7. File hệ thống (`desktop.ini`…) — giữ nguyên.
- **Đề xuất dọn dẹp** (mỗi file chỉ tính một lần): log khóa TLS, log lớn, cache ứng dụng, file tạm, bản trùng (an toàn); lưu trữ bản ghi màn hình gốc và video ≥ 300 MB (tùy chọn); lưu ý file nhạy cảm theo tên.
- Thư mục rỗng và file 0 byte.

Khi người dùng hỏi giải thích chi tiết từng nhóm trùng, trả lời trong chat theo đúng 7 nguyên nhân trên: bảng tóm tắt (nguyên nhân, số nhóm, tiết kiệm, mức an toàn), rồi mỗi nguyên nhân một bảng `# | Giữ | Bỏ | Tiết kiệm`, kèm tổng bỏ được an toàn.

## Quy tắc bắt buộc

- **Chỉ đọc.** Không chạy lệnh ghi/xóa/di chuyển/đổi tên/đổi thuộc tính nào trên thư mục được khám. Mọi file trung gian và báo cáo đặt ngoài thư mục đó.
- Không mở/đọc nội dung file nhạy cảm (mật khẩu, khóa) — chỉ nêu theo tên.
- Nếu sau đó người dùng **yêu cầu rõ ràng** xóa file cụ thể: đây là bước riêng, ngoài skill. Kiểm tra file tồn tại và kích thước, tìm bản sao khác trên ổ (báo nếu là bản duy nhất), kiểm tra Thùng rác của ổ đủ chỗ và không bật xóa thẳng, rồi **chuyển vào Thùng rác** (`[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(path,'OnlyErrorDialogs','SendToRecycleBin')`), xác minh và báo cách khôi phục. Không xóa vĩnh viễn trừ khi người dùng xác nhận riêng.
- Báo cáo là ảnh chụp tại thời điểm quét; nếu file thay đổi sau đó, đề nghị quét lại thay vì sửa tay số liệu.

## Kiểm thử

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\tests\run-tests.ps1"
```
Sinh dữ liệu mẫu có đủ 7 kiểu trùng, file nặng, log TLS, file tạm, thư mục rỗng; kiểm tra số liệu quét, phân loại trùng, việc từ chối ghi vào thư mục quét, quét tĩnh mã nguồn không có lệnh ghi/xóa, và so ảnh chụp trước/sau (đường dẫn, kích thước, ngày sửa, thuộc tính, SHA-256) để chứng minh dữ liệu không đổi. `-Keep` để giữ lại dữ liệu mẫu.
