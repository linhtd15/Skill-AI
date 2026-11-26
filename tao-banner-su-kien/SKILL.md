---
name: tao-banner-su-kien
description: Tạo TRÌNH TẠO BANNER SỰ KIỆN tương tác (HTML/CSS/JS, hiển thị trong claude.ai Artifact) cỡ chuẩn Facebook 1200×628 — 1 đến 3 diễn giả tự chia bố cục, tải ảnh chân dung/logo/ảnh nền, sửa chữ trực tiếp, 4 phong cách (Ma trận Cyber, Mạch Neon, Tối giản, Sáng hiện đại), bảng màu + chọn màu tự do, mã QR đăng ký (tạo từ link hoặc tải ảnh) và nút xuất PNG bằng html2canvas (1x/2x). Dùng khi người dùng muốn "tạo banner sự kiện", "banner hội thảo/seminar/webinar", "banner diễn giả", "banner Facebook cho sự kiện", "event banner generator".
---

# Tạo banner sự kiện

Mẫu hoàn chỉnh đã được duyệt nằm ở `assets/banner-template.dc.html`. **Luôn đi từ mẫu này**, chỉ thay nội dung/màu mặc định theo yêu cầu mới — không viết lại từ đầu.

Thư mục `assets/` còn có hai thư viện đã kiểm tra (không tải lại từ mạng):
- `html2canvas.min.js` — html2canvas 1.4.1 (MIT), để xuất PNG.
- `qrcode.min.js` — qrcode-generator 1.4.4 (MIT), để tạo mã QR từ link.

## Mẫu gồm những gì (giữ nguyên khi tạo bản mới)

**Banner 1200×628** (chuẩn Facebook), font Google `Be Vietnam Pro`:
- Cột trái (~55%): logo (khung giữ chỗ "LOGO" khi chưa tải), nhãn `https://` có ổ khóa, tagline 2 phần, tiêu đề + cụm từ nhấn mạnh màu nhấn (cỡ chữ tự giảm khi tiêu đề dài), thời gian | địa điểm có icon, nút CTA chuyển màu, mã QR + chú thích cạnh CTA.
- Cột phải (~40%): diễn giả —
  1 người: ảnh tròn lớn giữa + thẻ tên kính mờ;
  2 người: 2 ảnh so le;
  3 người: tam giác (1 trên, 2 dưới), chữ thẻ tên nhỏ dần.
  Ảnh có viền phát sáng màu nhấn 1 + vòng tròn công nghệ phía sau; ảnh căn giữa kiểu cover (dùng `background-size: cover` thay `object-fit` vì html2canvas 1.4.1 không hỗ trợ object-fit).
- Họa tiết theo phong cách: lưới ma trận, cột mã 0/1, mạch điện, ổ khóa phát sáng, vầng sáng radial, vạch màu chân banner.

**Bảng điều khiển phía dưới:**
1. Diễn giả: nút `1 / 2 / 3 Diễn giả`; mỗi người có tải ảnh, xóa ảnh, Tên, Chức vụ.
2. Giao diện: 4 phong cách; 5 bảng màu (Cyan & Xanh ngọc mặc định, Xanh dương & Tím, Hổ phách & Đỏ, Hồng & Tím, Lục & Vàng chanh); 4 ô chọn màu (Màu nhấn 1, Màu nhấn 2, Nền 1, Nền 2); tải ảnh nền + thanh trượt độ phủ màu (mặc định 70%).
3. Mã QR: bật/tắt; tạo từ link hoặc tải ảnh QR; chú thích sửa được; QR luôn đen trên trắng.
4. Logo & thông tin sự kiện: tải logo; sửa tagline, tiêu đề, cụm nhấn mạnh, CTA, thời gian, địa điểm.
5. Xuất file: chọn 1x (1200×628) hoặc 2x (2400×1256), nút "Tải xuống Banner (PNG)"; ảnh vừa xuất hiện bên dưới để lưu bằng chuột phải nếu trình duyệt chặn tải.

Màu chữ tự tính: chữ trên nút CTA/nhãn chọn đen hoặc trắng theo độ tương phản; phong cách Sáng làm sẫm màu nhấn cho chữ.

## Quy trình

### Bước 1 – Lấy nội dung (không hỏi lại nếu người dùng đã nêu)
Tagline, tiêu đề (tách phần cụm nhấn mạnh), thời gian, địa điểm, chữ nút CTA, số diễn giả mặc định, tên/chức vụ diễn giả, link đăng ký (nếu có), phong cách/màu mong muốn. Thiếu gì thì để chữ giữ chỗ dạng `[Điền …]` — không bịa tên người, ngày giờ hay số liệu. Nêu giả định trong một dòng rồi làm.

### Bước 2 – Tạo Artifact
- Nếu phiên có Artifact type **Design** (canvas): tạo canvas từ type với tiêu đề sự kiện, rồi
  1. Upload `assets/html2canvas.min.js` và `assets/qrcode.min.js` làm asset của canvas (`publish`, `asset: true`) → nhận hai url `/_blob/<id>`.
  2. Sao mẫu thành `project/Main.dc.html`, **thay hai dòng `<script src="/_blob/…">` trong `<head>` bằng hai url mới** (id trong mẫu là của canvas cũ, không dùng lại được).
  3. `project/canvas.json`: một artboard `Main.dc.html` 1280×2150, `"is_interactive": true`, `launch` focused vào `Main.dc.html`.
  4. Gửi canvas.json + Main.dc.html trong một lần publish.
- Nếu không có type Design: chuyển mẫu thành trang HTML thường (React 18 + logic tương đương), nhúng hai thư viện bằng `<script>` từ cdnjs đúng phiên bản trên (`html2canvas/1.4.1`, `qrcode-generator/1.4.4`).

### Bước 3 – Chỉnh mặc định theo yêu cầu
Chỉ sửa giá trị trong `this.state` của constructor (chữ, `count`, `style`, `a1`/`a2`/`bg1`/`bg2`, `qrLink`, `qrCaption`, `scale`). Nếu có `qrLink` mặc định, sinh sẵn QR trong `componentDidMount` bằng `this.setState(this.makeQr(this.state.qrLink))`. Thêm phong cách/bảng màu mới bằng cách bổ sung vào `STYLES` / `PALETTES` ở đầu script.

### Bước 4 – Bàn giao
Đưa link Artifact, tóm tắt những gì đã đặt mặc định và giả định, nhắc: ảnh/logo chỉ lưu trong trình duyệt (tải lại trang là mất); kính mờ thẻ tên xuất PNG thành nền bán trong suốt (html2canvas không hỗ trợ `backdrop-filter`); quét thử QR trước khi đăng; Artifact riêng tư cho đến khi chia sẻ qua menu Share.

## Lưu ý kỹ thuật (đừng phá)
- Ảnh do người dùng tải lên là data URL trong state; gán vào `style` qua **object** (`style="{{ s.photoStyle }}"`), không nối chuỗi style — data URL chứa `;` sẽ làm hỏng chuỗi style.
Đã kiểm thử với html2canvas 1.4.1 — các lỗi sau làm ảnh xuất "xô lệch" so với preview, đừng tái phạm:
- **Chụp bản sao cô lập** (`onclone`): xóa mọi node khác trong body bản sao, reset `transform`/`zoom`, đặt banner một mình ở 0,0; tùy chọn `x:0, y:0, scrollX:0, scrollY:0, windowWidth:1200, windowHeight:628, width:1200, height:628`. Artboard trên canvas bị thu phóng bằng CSS transform và trang bị cuộn — chụp thẳng phần tử gốc (hoặc dùng `scrollY: -window.scrollY`) cho ra ảnh co nhỏ, chữ đè nhau.
- **SVG đặt `position:absolute` + `left/top` bị cộng vị trí hai lần** → luôn bọc SVG trong một `<div>` định vị, SVG bên trong `display:block` và có thuộc tính `width`/`height`.
- **Không dùng `<filter>` trong SVG** (ổ khóa biến mất) — tạo quầng sáng bằng một nét vẽ rộng, mờ đặt dưới nét chính.
- **`box-shadow` có spread trên khung ảnh tròn sẽ phủ lên ảnh** → đặt quầng sáng ở lớp div riêng nằm dưới ảnh.
- **`backdrop-filter` và `inset` box-shadow vẽ thành khối tối sau chữ** → bỏ inset; tắt `backdrop-filter` trong `onclone`.
- Không dùng `background-clip: text`, `filter` CSS, `object-fit` trên banner.
- Trước khi chụp: `document.fonts.load` các weight 400–800 của Be Vietnam Pro rồi `await document.fonts.ready`.
