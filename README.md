# RFID Defect Analytics Dashboard

Ứng dụng web dashboard theo dõi chất lượng sản xuất trên 4 lines sản xuất

Hệ thống tổng hợp dữ liệu lỗi từ hai nguồn — file CSV dữ liệu sản phẩm gốc và một API endpoint trực tiếp

---

## Mục lục

1. [Cấu trúc dự án](#cấu-trúc-dự-án)
2. [Hướng dẫn cài đặt và chạy](#hướng-dẫn-cài-đặt-và-chạy)
3. [Tính năng dashboard](#tính-năng-dashboard)
4. [Câu hỏi phân tích](#câu-hỏi-phân-tích)
5. [Hạn chế và khả năng phát triển](#hạn-chế-và-khả-năng-phát-triển)

---

## Cấu trúc dự án

```
RFID_Data-Analyst_Case-Study-Test-Jun/
├── backend/
│   ├── main.py            # FastAPI app và định nghĩa các route
│   ├── data.py            # Logic fetch, merge, cache và tổng hợp dữ liệu
│   ├── models.py          # Pydantic response schemas
│   └── requirements.txt
├── frontend/
│   └── app.py             # Streamlit dashboard
├── data/
│   └── master_data.csv    # Dữ liệu sản phẩm gốc (từ repo)
├── Summary.ipynb          # Notebook phân tích khám phá dữ liệu (EDA)
├── requirements.txt       # Thư viện Python
└── README.md
```

---

## Hướng dẫn cài đặt và chạy

### Yêu cầu

- Python 3.11+
- Git

### 1. Clone repository

```bash
git clone https://github.com/phongtdt/RFID_Data-Analyst_Case-Study-Test-Jun.git
cd RFID_Data-Analyst_Case-Study-Test-Jun
```

### 2. Tạo và kích hoạt môi trường ảo

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Cài đặt thư viện

```bash
pip install fastapi uvicorn pandas requests scipy streamlit plotly
```

Hoặc dùng file requirements:

```bash
pip install -r requirements.txt
```

### 4. Chạy backend (FastAPI)

Mở terminal tại thư mục gốc của dự án:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API sẽ hoạt động tại `http://localhost:8000`.
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### 5. Chạy frontend (Streamlit)

Mở **terminal thứ hai** tại thư mục gốc của dự án:

```bash
cd frontend
streamlit run app.py
```

Dashboard sẽ tự động mở tại `http://localhost:8501`.

### Các API Endpoint

| Method | Endpoint                          | Mô tả                                           |
| ------ | --------------------------------- | ------------------------------------------------- |
| GET    | `/api/summary`                  | Tổng quan KPI                                    |
| GET    | `/api/trends`                   | Xu hướng lỗi theo tháng + đánh dấu anomaly |
| GET    | `/api/by-line`                  | Thống kê lỗi theo dây chuyền sản xuất      |
| GET    | `/api/by-product?top_n=20`      | Top N sản phẩm theo số lượng lỗi            |
| GET    | `/api/location-severity`        | Crosstab + kiểm định chi-square                |
| GET    | `/api/repair-cost?group_by=...` | Phân tích chi phí sửa chữa theo chiều       |
| GET    | `/api/anomalies`                | Phát hiện anomaly theo tháng (z-score)         |
| GET    | `/api/export/csv`               | Tải toàn bộ dataset đã merge                 |
| POST   | `/refresh`                      | Buộc tải lại dữ liệu từ nguồn              |

---

## Tính năng trên dashboard

Dashboard được tổ chức thành 5 trang, điều hướng qua sidebar:

**Overview (Tổng quan)**
Cái nhìn toàn cảnh về báo cáo. Hiển thị 5 card KPI (tổng số lỗi, tổng chi phí sửa chữa, chi phí trung bình mỗi lỗi, tỷ lệ lỗi, dây chuyền có nhiều lỗi nhất), biểu đồ đường xu hướng từ tháng 1/2024 đến tháng 6/2024, biểu đồ donut thể hiện tỷ lệ lỗi theo dây chuyền sản xuất và bảng tóm tắt so sánh của cả 4 chuyền.

**Trend Analysis (Phân tích xu hướng)**
Phân tích chi tiết số lượng lỗi từ tháng 1/2024 đến tháng 6/2024. Bao gồm biểu đồ đường có chú thích với đánh dấu anomaly (các tháng có số lỗi vượt ngưỡng mean ± 1.5 độ lệch chuẩn), biểu đồ thanh thể hiện phần trăm thay đổi tháng-qua-tháng (MoM), và nhãn xu hướng tổng thể được xác định từ hệ số góc hồi quy tuyến tính.

**Defect Breakdown (Phân tích chi tiết lỗi)**
3 tab bao gồm các hướng phân tích khác nhau. Tab Location & Severity hiển thị heatmap số lượng lỗi theo vị trí và mức độ nghiêm trọng, biểu đồ cột chồng và kết quả kiểm định chi-square độc lập. Tab By Production Line dùng biểu đồ hai trục để so sánh số lượng lỗi và tỷ lệ lỗi với nhau. Tab By Product hiển thị biểu đồ thanh ngang của các sản phẩm có nhiều lỗi nhất với nút thanh trượt để điều chỉnh số sản phẩm hiển thị.

**Repair Cost (Chi phí sửa chữa)**
Thanh điều khiển cho phép người dùng chuyển đổi các nhóm giữa dây chuyền sản xuất, danh mục, mức độ nghiêm trọng và loại lỗi. Trang hiển thị biểu đồ donut cho tỷ lệ tổng chi phí và biểu đồ thanh cho chi phí trung bình mỗi lỗi. Bảng dữ liệu có định dạng gradient màu được đưa vào, kèm nút tải toàn bộ dataset dạng CSV.

**Anomaly Detection (Phát hiện bất thường)**
Biểu đồ kiểm soát hiển thị số lượng lỗi theo tháng với vùng hoạt động bình thường được tô màu xanh. Các tháng có z-score vượt ngưỡng 1.5 được đánh dấu bằng biểu tượng ngôi sao. Bảng z-score bên dưới biểu đồ tô đỏ các hàng bất thường, và banner tóm tắt báo cáo số tháng bị phát hiện bất thường.

---

## Câu hỏi phân tích

### Câu 1. Phân tích xu hướng từ tháng 1/2024 đến tháng 6/2024

**Số liệu quan sát:**

Số lượng lỗi trong sáu tháng như sau:

| Tháng | Số lượng lỗi | Thay đổi MoM (%) |
| ------ | ---------------- | ------------------ |
| Jan    | 150              | —                 |
| Feb    | 121              | −19.33%           |
| Mar    | 149              | +23.14%            |
| Apr    | 198              | +32.89%            |
| May    | 213              | +7.58%             |
| Jun    | 259              | +21.60%            |

**Nhận định:**

Hồi quy tuyến tính trên số lượng lỗi theo tháng cho thấy hệ số góc **dương**, phản ánh xu hướng **tăng dần** trong suốt kỳ. Mặc dù tháng 2 ghi nhận mức giảm đáng kể (−19.33%), đây chỉ là dao động ngắn hạn — từ tháng 3 trở đi, số lỗi tăng liên tục và kết thúc ở mức 259 lỗi trong tháng 6, cao hơn **72.7%** so với tháng 1.

Đây là **dấu hiệu tiêu cực**. Số lượng lỗi tăng trong 4 tháng liên tiếp (Mar–Jun) cho thấy khả năng kiểm soát chất lượng đang suy giảm, sản lượng tăng nhưng không có điều chỉnh tương ứng về chất lượng, hoặc các nguyên nhân gốc rễ chưa được xử lý triệt để đang tích lũy trên một hoặc nhiều dây chuyền. Thực tế là mô hình này chỉ trở nên rõ ràng qua dữ liệu tổng hợp — thay vì được phát hiện ở cấp dây chuyền — xác nhận vấn đề ban đầu: báo cáo thủ công hàng tuần đến tay người ra quyết định quá trễ để can thiệp kịp thời.

**Mô hình đáng chú ý trong kỳ:**

Tháng **Jun** bị hệ thống phát hiện anomaly đánh dấu là bất thường về mặt thống kê (z-score =1.495 ~ 1.5). Điều này cần được theo dõi lại tại dây chuyền sản xuất và sản phẩm cho tháng đó — trang Defect Breakdown của dashboard có thể được dùng để xác định dây chuyền hoặc loại lỗi nào gây ra đợt tăng đột biến này.

---

### Câu 2. Vị trí lỗi và mức độ nghiêm trọng

**Theo location:**

Trong kỳ tháng 1–6/2024, lỗi được phân bố theo ba vị trí:

| Vị trí  | Số lượng | % Tổng |
| --------- | ----------- | ------- |
| Surface   | 389         | 35.78%  |
| Component | 351         | 32.29%  |
| Internal  | 347         | 31.92%  |

**Surface** chiếm tỷ lệ lỗi cao nhất. Tuy nhiên, ba vị trí có phân bố khá đồng đều (35.78% / 32.29% / 31.92%), cho thấy lỗi xảy ra trải rộng chứ không tập trung tại một điểm duy nhất.

**Mối quan hệ giữa vị trí và mức độ nghiêm trọng:**

Kiểm định chi-square về tính độc lập được thực hiện trên bảng crosstab giữa vị trí lỗi và mức độ nghiêm trọng:

- Chi-square statistic: `39.1914`
- P-value: `0.000098`
- Degrees of freedom: `12`

**Kết quả:** P-value **nhỏ hơn** 0.05, có nghĩa là **có** mối quan hệ thống kê có ý nghĩa giữa nơi xảy ra lỗi và mức độ nghiêm trọng của lỗi đó.

Vị trí lỗi không độc lập nên để có cái nhìn rõ ràng hơn ta nên quan sát heatmap để có thể tìm được tổ hợp các điều kiện có thể gây ra nguyên nhân.

 **Heatmap:**

Heatmap trên trang Defect Breakdown hiển thị số lượng thô cho từng tổ hợp vị trí–mức độ nghiêm trọng. Các ô có màu đậm nhất chỉ ra các tổ hợp có giá trịcao nhất cần được ưu tiên phân tích nguyên nhân.

Tổ hợp có giá trị cao nhất:

* Surface và Minor: 158
* Component và Critical: 150

---

### Câu 3. Các điểm đáng chú ý khác

**Pattern 1 — Lỗi theo dây chuyền sản xuất**

Line **4** có **344** lỗi - số lượng lỗi cao nhất trong 4 lines. Nhưng line **3** chiếm tỷ lệ lỗi không cân xứng so với sản lượng của nó cao nhất. Tỷ lệ lỗi (defect rate) là **1.389%**,  có thể thấy 2 dây chuyền này tạo ra nhiều lỗi hơn trên mỗi đơn vị sản phẩm.

**Pattern 2 — Chi phí sửa chữa bất thường theo mức độ nghiêm trọng**

Như kỳ vọng, lỗi Critical có chi phí sửa chữa trung bình cao hơn lỗi Minor. Tuy nhiên, phân bố trong từng nhóm mức độ nghiêm trọng khá rộng. Một số lỗi Minor có chi phí sửa chữa nằm trong cùng khoảng với lỗi Moderate, cho thấy tiêu chí phân loại mức độ nghiêm trọng có thể chưa được áp dụng nhất quán giữa các dây chuyền hoặc phương pháp kiểm tra — hoặc một số loại lỗi được gán nhãn Minor lại đòi hỏi công sức sửa chữa không tương xứng.

**Pattern 3 — Tập trung theo loại lỗi**

Lỗi **Functional** chiếm đa số trong tổng số lỗi được ghi nhận. Nếu một loại chiếm hơn 50% khối lượng, đây là một điểm đòn bẩy duy nhất: giải quyết nguyên nhân gốc rễ của loại lỗi chiếm ưu thế sẽ có tác động lớn hơn đến tổng số lỗi so với bất kỳ can thiệp đơn lẻ nào khác.

**Pattern 4 — Phương pháp kiểm tra**

Trong dataset chỉ ghi nhận hai phương pháp: Manual Testing và Visual Inspection. Nếu một phương pháp liên quan đến tỷ lệ phát hiện lỗi Critical cao hơn, điều này có thể cho thấy phương pháp đó hiệu quả hơn trong việc phát hiện các vấn đề nghiêm trọng, hoặc được triển khai nhiều hơn trên các sản phẩm có rủi ro cao. So sánh phân bố mức độ nghiêm trọng theo phương pháp kiểm tra có thể cung cấp thông tin cho các quyết định về việc mở rộng phạm vi kiểm tra tự động.
