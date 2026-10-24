# Nhật ký xây nhà

Trang thông tin cho người lần đầu xây nhà, xuất bản tại https://nhatkyxaynha.vn qua GitHub Pages. Tên miền nhatkyxaynha.com chuyển hướng về nhatkyxaynha.vn.

Website là **HTML, CSS, JS tĩnh**: không CMS, không đăng nhập, không máy chủ. Các trang được sinh từ thư mục `src/` bằng một script Python nhỏ, rồi commit cả nguồn lẫn kết quả lên nhánh `main`.

## Sửa nội dung

1. Sửa tệp trong `src/` (xem bảng dưới).
2. Chạy `python tools/build.py` ở thư mục gốc (Python 3.8+, không cần cài thêm gì).
3. Script dựng lại toàn bộ trang và kiểm tra liên kết. Nếu có lỗi, nó in ra và dừng.
4. Mở thử bằng `python -m http.server` rồi vào http://localhost:8000 (không mở trực tiếp tệp, vì liên kết dùng đường dẫn tuyệt đối `/...`).
5. Commit cả `src/` lẫn các tệp HTML đã sinh, push lên `main`. Trang tự cập nhật sau 1–2 phút.

| Muốn sửa | Sửa ở |
| --- | --- |
| Chặng, truyện, công cụ, nút "Nhà bạn đang ở đâu?" | `src/site.json` |
| Lời truyện, tranh | `src/stories/<id>.html` |
| Giao diện công cụ | `src/tools/<slug>.html` (logic trong `src/js/site.js`) |
| Bài cẩm nang, chuyên sâu | `src/content/cam-nang/*.html`, `src/content/chuyen-sau/*.html` |
| Bản đồ hành trình: Quyết định chính, Sai lầm hay gặp, Giấy tờ cần có, Cổng chặng | `src/ban-do.json` |
| Hỏi nhanh | `src/hoi-nhanh.json` |
| Từ điển | `src/tu-dien.json` |
| Trang chung, địa phương | `src/pages/*.html` |
| Giao diện | `src/css/*.css` |

**Không sửa trực tiếp** các tệp HTML đã sinh (`index.html`, `chang/`, `chuyen/`, `cong-cu/`, `cam-nang/`…) hoặc `assets/css/site.css`, `assets/js/site.js`: lần build sau sẽ ghi đè.

## Thêm một bài cẩm nang

Tạo `src/content/cam-nang/<ten-bai>.html`, đầu tệp có khối meta:

```html
<!--meta {
  "code": "N2.5", "stage": 2, "status": "cho-duyet", "written": "2026-11-01",
  "title": "Tiêu đề bằng lời thường",
  "learn": "điều người đọc sẽ biết sau khi đọc.",
  "read": 5,
  "tldr": ["Ý 1", "Ý 2", "Ý 3"],
  "deeper": "slug-bai-chuyen-sau", "try": "slug-cong-cu",
  "keywords": ["từ khoá", "cho tìm kiếm"],
  "sources": [{"title": "Tên nguồn", "url": "https://..."}]
}-->
<p>Câu đầu là câu trả lời…</p>
```

Các khối dùng trong bài: `<div class="example"><p class="who">Nhà chị Hạnh</p><p>…</p></div>`, `<details class="more"><summary>Vì sao?</summary><div><p>…</p></div></details>`, `<div class="mistakes"><h2>Sai lầm thường gặp</h2><ul>…</ul></div>`, bảng bọc trong `<div class="table-wrap">`.

## Duyệt bài

- Bài mới có `"status": "cho-duyet"`: hiện ghi chú **Bản nháp**, không vào sitemap, có `noindex`.
- Khi đã duyệt: đổi thành `"status": "da-duyet"`, thêm `"reviewer": "Tên người duyệt"`, `"reviewed": "2026-11-05"`, `"next_review": "2027-05-05"`.
- Muốn tạm ẩn mọi bản nháp khỏi website: `python tools/build.py --an-nhap`.
- Bài pháp lý nên rà soát lại 6 tháng một lần hoặc khi có văn bản mới.

## Tệp khác

- `CNAME`: tên miền riêng cho GitHub Pages. Không xoá.
- `.nojekyll`: báo GitHub Pages phục vụ tệp nguyên bản, không chạy Jekyll.
- `assets/fonts/`: phông Be Vietnam Pro, Mali, Literata (giấy phép SIL OFL 1.1, kèm tệp giấy phép).
- `assets/img/og/`: ảnh chia sẻ khi gửi link qua mạng xã hội.
