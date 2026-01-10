Giải thuật khởi tạo nghiệm (Initial Solution) được triển khai trong `src/initializer.py` sử dụng chiến lược **Cluster + Nearest Neighbor**, kết hợp với việc xác định nhiệm vụ Drone Resupply sau khi đã hình thành lộ trình xe tải.

Các bước thực hiện chi tiết:

1. **Phân cụm khách hàng (Clustering)**
   - Tính góc (angle) của tất cả khách hàng so với Depot.
   - Sắp xếp khách hàng theo chiều tăng dần của góc.
   - Chia danh sách đã sắp xếp thành *k* cụm (k là số lượng xe tải).
   - **Xử lý cặp Pickup-Delivery (C2)**: Đảm bảo tính hợp lệ bằng cách kiểm tra nếu điểm Pickup và Delivery nằm ở hai cụm khác nhau, điểm Delivery sẽ được chuyển về cụm của điểm Pickup.

2. **Xây dựng lộ trình xe tải (Truck Route Construction)**
   - Với mỗi cụm khách hàng, xây dựng lộ trình cho một xe tải:
     - Sử dụng thuật toán tham lam **Nearest Neighbor** (Láng giềng gần nhất): Từ vị trí hiện tại (bắt đầu là Depot), chọn điểm đến tiếp theo là điểm gần nhất thỏa mãn các ràng buộc về tải trọng (Capacity).
     - **Quản lý tải trọng**:
       - Tải trọng xe được tính toán động khi nhận hàng (Pickup / Resupply) và giao hàng (Delivery).
       - Nếu thêm điểm tiếp theo khiến xe vượt quá tải trọng tối đa, xe sẽ quay về Depot (kết thúc Trip hiện tại và bắt đầu Trip mới).
     - **Nguyên tắc chèn điểm C2**:
       - Khi xe ghé điểm Pickup, điểm Delivery tương ứng được thêm vào danh sách "chờ giao" (pending deliveries).
       - Điểm Delivery này sẽ được xem xét chọn làm điểm đến tiếp theo trong các bước lặp sau (nếu nó là điểm gần nhất).
       - Nếu kết thúc danh sách khách hàng mà vẫn còn điểm "chờ giao", chúng sẽ được chèn vào cuối lộ trình của Trip hiện tại.

3. **Gán nhiệm vụ Drone (Drone Resupply Assignment)**
   - Sau khi có lộ trình sơ bộ của xe tải, thuật toán xác định các gói hàng loại C1 (giao từ Depot) nên được chuyển sang Drone để tối ưu thời gian:
     - **Tiêu chí**: Các gói hàng có thời gian sẵn sàng (`ready_time`) lớn, nếu xe tải mang theo sẽ phải chờ lâu tại Depot (xe tới điểm giao sớm hơn nhiều so với `ready_time` của gói hàng).
     - **Tạo Mission**:
       - Các gói hàng thỏa mãn tiêu chí trên thuộc cùng một Trip của xe tải sẽ được gom nhóm.
       - Kiểm tra sức chứa của Drone (tối đa 10 packages) và thời gian bay tối đa (Flight Endurance).
       - Điểm gặp gỡ (Meet Point) chính là vị trí khách hàng trong lộ trình xe tải, nơi Drone sẽ bay đến để tiếp tế.
     - **Phân phối**: Các Mission được chia đều cho các Drone theo cơ chế vòng tròn (Round-robin).
