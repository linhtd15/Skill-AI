# Cấu trúc `bien-ban.json` (Claude viết, script kiểm chứng)

Mọi trường không có trong bản ghi/ghi chú → `null` (không bịa). Thời gian `t`, `nguoi` của trích dẫn do script tự điền từ `seg`.

```json
{
  "meta": {
    "tieu_de": "Họp kế hoạch bán hàng Tết 2027",
    "muc_dich": "Một câu nêu mục đích cuộc họp, lấy từ lời chủ trì.",
    "ngay_hop": "2026-11-19",          // bắt buộc để quy đổi hạn tương đối; không biết → null
    "gio_bat_dau": "09:00", "gio_ket_thuc": null,
    "dia_diem": null, "hinh_thuc": "Trực tuyến",
    "co_quan": null, "so": null, "dia_danh": null, "so_ban": null,
    "chu_tri": "Trần Minh Hoàng", "thu_ky": "Phạm Ngọc Lan",
    "nguon": "hop-mau.mp4"
  },
  "nguoi_tham_gia": [
    {"ten": "Nguyễn Thu Hà", "email": "ha@example.com", "vai_tro": "Marketing", "vang": false, "ly_do_vang": null}
  ],
  "tom_tat": ["4–6 ý, mỗi ý ≤ 25 từ"],
  "chu_de": [
    {"id": "T1", "tieu_de": "Khai mạc và mục tiêu", "tom_tat": "1–2 câu ≤ 40 từ.",
     "trich_dan": [{"seg": 1, "text": "đoạn chép nguyên văn từ ban-ghi.txt", "chinh": true},
                   {"seg": 2, "text": "trích dẫn phụ"}]}
  ],
  "quyet_dinh": [
    {"id": "QĐ1", "noi_dung": "Chốt ngân sách 450 triệu đồng.", "chu_de": "T3",
     "trich_dan": [{"seg": 11, "text": "chốt ngân sách quảng cáo Tết là 450 triệu đồng"}]}
  ],
  "hanh_dong": [
    {"id": "V1", "cong_viec": "Hoàn thiện kế hoạch truyền thông, gửi chủ trì.", "phu_trach": "Nguyễn Thu Hà",
     "han": "2026-11-27", "han_goc": "thứ Sáu tuần sau", "chu_de": "T4",
     "trich_dan": [{"seg": 15, "text": "Chị Hà phụ trách hoàn thiện kế hoạch truyền thông, gửi tôi trước thứ Sáu tuần sau"}]},
    {"id": "V4", "cong_viec": "Kiểm tra tồn kho trước Tết.", "phu_trach": null, "han": null, "han_goc": null, "chu_de": "T5",
     "trich_dan": [{"seg": 18, "text": "chưa có người nhận"}]}
  ],
  "van_de_mo": [
    {"id": "M1", "noi_dung": "Chưa quyết đơn vị vận chuyển dự phòng.", "loai": "RUI_RO", "chu_de": "T6",
     "trich_dan": [{"seg": 20, "text": "chưa quyết, để họp sau"}]}
  ],
  "bo_qua": [{"seg": 3, "ly_do": "Thư ký nhận ghi biên bản – thủ tục, không phải việc sau họp."}],
  "can_lam_ro": [{"muc": "Địa điểm họp", "cau_hoi": "Cuộc họp tổ chức ở đâu (phòng/nền tảng)?"}]
}
```

## Quy tắc kiểm chứng (script chặn nếu vi phạm)

| Trường | Điều kiện |
|---|---|
| `trich_dan[].text` | Là chuỗi con NGUYÊN VĂN của đoạn `seg` (hoặc đoạn đó + đoạn kế tiếp). Không dấu câu/hoa thường thì bỏ qua khi so. Không được là câu ảo giác đã lọc. |
| `phu_trach` | Có trong `nguoi_tham_gia`; VÀ (người nói của trích dẫn chính là người đó + câu có cụm tự nhận "em sẽ / tôi nhận / để em…") HOẶC tên người đó xuất hiện trong câu trích. |
| `han` | Chỉ khi `han_goc` xuất hiện trong câu trích. Ngày tương đối chỉ quy đổi khi có `meta.ngay_hop`; script tự tính lại và so khớp. "cuối tuần", "tuần sau" (không có thứ) → mơ hồ, để `han: null`. |
| Từ khoá | Mọi đoạn chứa từ khoá trong `config.json → kiem_chung.tu_khoa_bat_buoc` phải được trích ở đâu đó hoặc nằm trong `bo_qua` kèm lý do. |
| `chu_de` | Mỗi chủ đề ≥ 1 trích dẫn; đánh `"chinh": true` cho câu tiêu biểu (dùng làm ảnh chụp và câu in nghiêng trong PDF). |
