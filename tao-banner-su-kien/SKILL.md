---
name: tao-banner-su-kien
description: Tạo TRÌNH TẠO BANNER SỰ KIỆN tương tác (HTML/CSS/JS, hiển thị trong claude.ai Artifact) cỡ chuẩn Facebook 1200×628 — 1 đến 3 diễn giả tự chia bố cục, tải ảnh chân dung/logo/ảnh nền, sửa chữ trực tiếp, 11 phong cách (có lưới: Ma trận Cyber, Mạch Neon, Tối giản, Sáng hiện đại; không lưới: Cực quang, Kính mờ, Sóng ánh sáng, Mạng hạt, Tổ ong; nền trong suốt chữ sáng/chữ tối) + bật/tắt lưới nền, bảng màu + chọn màu tự do, tùy chọn khung ảnh diễn giả (hình dạng, viền, hiệu ứng), bật/tắt và đổi các biểu tượng trang trí (nhãn https://, biểu tượng chìm, icon), mã QR đăng ký (tạo từ link hoặc tải ảnh) và nút xuất PNG bằng html2canvas (1x/2x). Dùng khi người dùng muốn "tạo banner sự kiện", "banner hội thảo/seminar/webinar", "banner diễn giả", "banner Facebook cho sự kiện", "event banner generator".
---

# Tạo banner sự kiện

Mẫu hoàn chỉnh đã được duyệt nằm ở `assets/banner-template.dc.html`. **Luôn đi từ mẫu này**, chỉ thay nội dung/màu mặc định theo yêu cầu mới — không viết lại từ đầu.

Thư mục `assets/` còn có hai thư viện đã kiểm tra (không tải lại từ mạng):
- `html2canvas.min.js` — html2canvas 1.4.1 (MIT), để xuất PNG.
- `qrcode.min.js` — qrcode-generator 1.4.4 (MIT), để tạo mã QR từ link.

## Mẫu gồm những gì (giữ nguyên khi tạo bản mới)

**Banner 1200×628** (chuẩn Facebook), font Google `Be Vietnam Pro`:
- Cột trái (~55%): logo (khung giữ chỗ "LOGO" khi chưa tải), nhãn góc trên (mặc định ổ khóa + `https://` + `secure`, tắt/sửa được), tagline 2 phần, tiêu đề + cụm từ nhấn mạnh màu nhấn (cỡ chữ tự giảm khi tiêu đề dài), thời gian | địa điểm có icon, nút CTA chuyển màu, mã QR + chú thích cạnh CTA.
- Cột phải (~40%): diễn giả —
  1 người: ảnh tròn lớn giữa + thẻ tên kính mờ;
  2 người: 2 ảnh so le;
  3 người: tam giác (1 trên, 2 dưới), chữ thẻ tên nhỏ dần.
  Khung ảnh mặc định: tròn, viền phát sáng màu nhấn 1, vòng tròn công nghệ phía sau; ảnh căn giữa kiểu cover (dùng `background-size: cover` thay `object-fit` vì html2canvas 1.4.1 không hỗ trợ object-fit).
- Họa tiết theo phong cách (bảng dưới); lưới nền là lớp riêng bật/tắt được cho mọi phong cách; vạch màu chân banner; biểu tượng chìm phát sáng giữa hai cột (mặc định ổ khóa, đổi/tắt được).

**Bảng điều khiển phía dưới:**
1. Diễn giả: nút `1 / 2 / 3 Diễn giả`; mỗi người có tải ảnh, xóa ảnh, Tên, Chức vụ.
2. Khung ảnh diễn giả (áp dụng cho tất cả): hình dạng `Tròn / Bo góc / Hình lá / Vuông` (ô xem trước trong bảng cũng đổi theo); viền `Phát sáng / Viền mảnh / Viền kép (vòng thứ hai màu nhấn 2) / Không viền`; hiệu ứng quanh ảnh `Vòng công nghệ / Góc HUD / Không`.
   Biểu tượng trên banner: bật/tắt nhãn góc trên, chọn icon nhãn `Ổ khóa / Khiên / Chip / Quả cầu / Không icon`, sửa chữ chính và chữ phụ (để trống = ẩn phần đó); biểu tượng chìm phía sau `Ổ khóa / Khiên / Quả cầu / Chip / Không`; bật/tắt icon lịch & địa điểm; bật/tắt mũi tên trên nút CTA.
3. Giao diện: 11 phong cách (ô xem trước minh họa từng kiểu) + ô tích "Lưới nền" (chọn phong cách sẽ đặt lại lưới theo mặc định của kiểu đó); 5 bảng màu (Cyan & Xanh ngọc mặc định, Xanh dương & Tím, Hổ phách & Đỏ, Hồng & Tím, Lục & Vàng chanh); 4 ô chọn màu (Màu nhấn 1, Màu nhấn 2, Nền 1, Nền 2); tải ảnh nền + thanh trượt độ phủ màu (mặc định 70%).
4. Mã QR: bật/tắt; tạo từ link hoặc tải ảnh QR; chú thích sửa được; QR luôn đen trên trắng.
5. Logo & thông tin sự kiện: tải logo; sửa tagline, tiêu đề, cụm nhấn mạnh, CTA, thời gian, địa điểm.
6. Xuất file: chọn 1x (1200×628) hoặc 2x (2400×1256), nút "Tải xuống Banner (PNG)"; ảnh vừa xuất hiện bên dưới để lưu bằng chuột phải nếu trình duyệt chặn tải.

**Các phong cách** (khóa trong `STYLES`, giá trị `style` trong state):

| Khóa | Tên | Họa tiết | Lưới mặc định |
|---|---|---|---|
| `matrix` | Ma trận Cyber | cột mã 0/1, vầng sáng | có |
| `circuit` | Mạch Neon | đường mạch điện + điểm nút | có |
| `minimal` | Tối giản | chỉ vầng sáng, lưới rất mờ | có |
| `light` | Sáng hiện đại | mạch điện, nền sáng, chữ tối | có |
| `aurora` | Cực quang | 3 đốm màu loang lớn (a1, a2, pha trộn) | không |
| `glass` | Kính mờ | đốm màu + tấm kính sau cột trái + 2 vòng kính | không |
| `waves` | Sóng ánh sáng | các đường cong + 2 lớp sóng đổ màu ở chân | không |
| `network` | Mạng hạt | hạt nối dây (dày bên phải, thưa sau tiêu đề) | không |
| `hex` | Tổ ong | lưới lục giác mờ dần từ phải sang, vài ô sáng màu a2 | không |
| `clearDark` | Trong suốt – chữ sáng | không nền, không họa tiết | không |
| `clearLight` | Trong suốt – chữ tối | không nền, không họa tiết | không |

Trong suốt: preview hiện ô caro (chỉ để xem), PNG xuất ra giữ kênh alpha (`backgroundColor: null` + xóa nền trong `onclone`). Nếu người dùng tải ảnh nền thì ảnh nền được dùng thay cho trong suốt.

Màu chữ tự tính: chữ trên nút CTA/nhãn chọn đen hoặc trắng theo độ tương phản; phong cách Sáng làm sẫm màu nhấn cho chữ.

## Quy trình

### Bước 1 – Lấy nội dung (không hỏi lại nếu người dùng đã nêu)
Tagline, tiêu đề (tách phần cụm nhấn mạnh), thời gian, địa điểm, chữ nút CTA, số diễn giả mặc định, tên/chức vụ diễn giả, link đăng ký (nếu có), phong cách/màu mong muốn. Thiếu gì thì để chữ giữ chỗ dạng `[Điền …]` — không bịa tên người, ngày giờ hay số liệu. Nêu giả định trong một dòng rồi làm.

### Bước 2 – Tạo Artifact
- Nếu phiên có Artifact type **Design** (canvas): tạo canvas từ type với tiêu đề sự kiện, rồi
  1. Upload `assets/html2canvas.min.js` và `assets/qrcode.min.js` làm asset của canvas (`publish`, `asset: true`) → nhận hai url `/_blob/<id>`.
  2. Sao mẫu thành `project/Main.dc.html`, **thay hai dòng `<script src="/_blob/…">` trong `<head>` bằng hai url mới** (id trong mẫu là của canvas cũ, không dùng lại được).
  3. `project/canvas.json`: một artboard `Main.dc.html` 1280×2740, `"is_interactive": true`, `launch` focused vào `Main.dc.html`.
  4. Gửi canvas.json + Main.dc.html trong một lần publish.
- Nếu không có type Design: chuyển mẫu thành trang HTML thường (React 18 + logic tương đương), nhúng hai thư viện bằng `<script>` từ cdnjs đúng phiên bản trên (`html2canvas/1.4.1`, `qrcode-generator/1.4.4`).

### Bước 3 – Chỉnh mặc định theo yêu cầu
Chỉ sửa giá trị trong `this.state` của constructor:
- Nội dung & màu: chữ, `count`, `style` (khóa trong bảng phong cách), `gridOn` (đặt bằng `STYLES[style].grid` trừ khi người dùng muốn khác), `a1`/`a2`/`bg1`/`bg2` (đặt `bg1`/`bg2` theo `STYLES[style]` khi đổi phong cách), `qrLink`, `qrCaption`, `scale`.
  Gợi ý chọn phong cách: bảo mật/hạ tầng → `matrix`/`circuit`/`hex`; AI, dữ liệu → `network`/`aurora`; sự kiện thương hiệu, sang trọng → `glass`/`aurora`; năng lượng, viễn thông → `waves`; cần ghép lên ảnh/video khác → `clearDark`/`clearLight`.
  Thêm phong cách mới: thêm một mục vào `STYLES` (decor là một trong các họa tiết có sẵn, hoặc thêm khối `<sc-if>` họa tiết mới + cờ `decorX` trong `renderVals()` + nhánh ô xem trước trong `styleTiles`).
- Khung ảnh: `frameShape` (`circle|rounded|leaf|square`), `frameBorder` (`glow|thin|double|none`), `frameDecor` (`rings|hud|none`).
- Biểu tượng: `badgeOn` (true/false), `badgeIcon` (`lock|shield|chip|globe|none`), `badgeText`, `badgeSub` (chuỗi rỗng = ẩn), `wmIcon` (`lock|shield|globe|chip|none`), `metaIcons`, `ctaArrow`.
  Sự kiện không thuộc mảng bảo mật thì gợi ý đổi nhãn (ví dụ "AI Summit" + icon chip) hoặc tắt nhãn, và đổi/tắt biểu tượng chìm cho hợp chủ đề. Nếu có `qrLink` mặc định, sinh sẵn QR trong `componentDidMount` bằng `this.setState(this.makeQr(this.state.qrLink))`. Thêm phong cách/bảng màu mới bằng cách bổ sung vào `STYLES` / `PALETTES` ở đầu script.

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
- Không dùng `background-clip: text`, `filter` CSS, `object-fit`, `clip-path` trên banner (vì vậy khung ảnh chỉ dùng hình dạng tạo được bằng `border-radius`; html2canvas vẽ đúng bán kính từng góc như "Hình lá").
- Viền kép là một div riêng nằm ngoài ảnh 9px, bán kính = bán kính ảnh + 9px (`frameRadius(size, 9)`), không dùng box-shadow nhiều lớp.
- Mỗi biểu tượng tùy chọn là một khối `<sc-if>` riêng chứa cả `<svg>` (không đặt `<sc-if>` bên trong `<svg>`).
- **Phần tử bán trong suốt không được có `box-shadow`** (tấm kính của phong cách Kính mờ): html2canvas vẽ bóng thành khối đặc lộ qua lớp trong suốt — dùng viền sáng thay bóng.
- Họa tiết nhiều điểm/đường (Mạng hạt, Tổ ong) dựng sẵn thành chuỗi `d` của vài `<path>` trong JS (`makeNetwork`, `makeHex`), không lặp phần tử SVG bằng `<sc-for>`; chấm tròn = đoạn `h0.01` với `stroke-linecap: round`.
- Đã kiểm thử xuất PNG cả 7 phong cách mới (khớp preview; 2 kiểu trong suốt cho alpha = 0) và 4 hình dạng × viền phát sáng/kép × góc HUD, icon nhãn khiên, biểu tượng chìm quả cầu — khớp preview.
- Trước khi chụp: `document.fonts.load` các weight 400–800 của Be Vietnam Pro rồi `await document.fonts.ready`.
