# Thuật Toán Khởi Tạo Nghiệm Ban Đầu (Initial Solution Construction)

Hệ thống sử dụng chiến lược **Greedy Heuristic kết hợp Clustering** để tạo ra lời giải ban đầu nhanh chóng nhưng vẫn đảm bảo chất lượng khá tốt làm đầu vào cho thuật toán tối ưu hóa (Tabu Search). Quy trình bao gồm 4 bước chính:

## 1. Phân Cụm Khách Hàng (Customer Clustering)

Để đơn giản hóa bài toán và cân bằng tải giữa các xe tải, hệ thống chia khách hàng thành các nhóm (clusters) dựa trên vị trí địa lý.

- **Phương pháp**: Phân chia theo góc cực (Polar Angle).
- **Cách thực hiện**:
  1. Tính góc của mỗi khách hàng so với Depot (sử dụng hàm `atan2(dy, dx)`).
  2. Sắp xếp danh sách khách hàng theo góc tăng dần.
  3. Chia danh sách đã sắp xếp thành `NUM_TRUCKS` phần bằng nhau.
  4. Mỗi phần tương ứng với một Cluster được gán cho một xe tải cụ thể.
- **Xử lý ràng buộc C2**: Nếu một cặp Pickup-Delivery (P-DL) bị chia cắt vào 2 cluster khác nhau, điểm Delivery sẽ được chuyển về cluster của điểm Pickup để đảm bảo tính khả thi (pickup phải được thực hiện trước delivery trên cùng một xe hoặc xe khác, nhưng để đơn giản khởi tạo, ta ưu tiên cùng xe).

## 2. Xây Dựng Lộ Trình Xe Tải (Truck Route Construction)

Với mỗi cluster, lộ trình xe tải được xây dựng bằng thuật toán **Nearest Neighbor** (Láng giềng gần nhất) có kiểm tra ràng buộc tải trọng (Capacity).

- **Quy trình**:
  1. Xe tải xuất phát từ Depot (Load = 0).
  2. Tại vị trí hiện tại, tìm khách hàng chưa phục vụ *gần nhất* trong cluster.
  3. **Kiểm tra Capacity**:
     - Nếu thêm khách hàng vào trip hiện tại mà không vượt quá `TRUCK_CAPACITY` -> Thêm vào trip.
     - Nếu vượt quá -> Kết thúc trip hiện tại (quay về Depot), bắt đầu một Trip mới.
  4. Lặp lại cho đến khi phục vụ hết khách hàng trong cluster.
- **Xử lý đặc biệt**:
  - Khách hàng loại C2 (Pickup & Delivery) được xử lý kèm theo ràng buộc thứ tự (Pickup trước Delivery).

## 3. Gán Nhiệm Vụ Drone (Drone Resupply Assignment)

Sau khi có lộ trình sơ bộ của xe tải, hệ thống xác định các cơ hội để sử dụng Drone vận chuyển hàng hóa (Resupply) cho các khách hàng loại C1 (Delivery from Depot) có yêu cầu thời gian (`ready_time`) cao.

- **Điều kiện Resupply**: Drone được sử dụng nếu xe tải dự kiến đến khách hàng *SỚM HƠN* thời gian gói hàng sẵn sàng tại kho (`arrival_time < ready_time`). Thay vì xe tải phải chờ tại Depot, Drone sẽ mang hàng đến gặp xe tải tại điểm khách hàng (Meet Point).
- **Quy trình**:
  1. Duyệt qua từng Trip của xe tải.
  2. Xác định các khách hàng C1 thỏa mãn điều kiện Resupply.
  3. **Gom nhóm (Batching)**: Các gói hàng trên cùng một Trip được gom vào cùng một Drone Mission nếu tổng trọng lượng `≤ DRONE_CAPACITY`.
  4. Chọn **Meet Point** ban đầu là vị trí của khách hàng đầu tiên trong nhóm.

## 4. Sửa Chữa Lời Giải (Repair Heuristic)

Drone có giới hạn nghiêm ngặt về thời gian bay (`DRONE_FLIGHT_TIME = 90 phút`). Lời giải ban đầu có thể tạo ra các Mission vi phạm ràng buộc này (do Drone phải chờ Truck quá lâu hoặc quãng đường quá xa).

Hàm `_repair_drone_missions` được sử dụng để đảm bảo tính khả thi:

- **Đầu vào**: Lời giải ban đầu có thể chứa các Mission không hợp lệ (Infeasible).
- **Quy trình lặp (Max 10 iterations)**:
  1. Kiểm tra tính khả thi (`is_feasible()`) của toàn bộ lời giải.
  2. Nếu phát hiện Mission vi phạm `flight_time`:
     - **Tìm Meet Point Mới**: Thuật toán Backtrack từ vị trí gói hàng ngược về đầu Trip để tìm một điểm gặp mới tối ưu hơn.
     - **Điều kiện chọn Meet Point**: Điểm gặp mới phải đảm bảo tổng thời gian hoạt động của Drone (Bay đi + Chờ xe tải + Xếp dỡ + Bay về) nhỏ hơn giới hạn cho phép (với hệ số an toàn 90%).
     - Nếu tìm được Meet Point hợp lệ -> Cập nhật Mission.
     - Nếu KHÔNG tìm được -> **Loại bỏ Mission**, gói hàng sẽ được chuyển sang vận chuyển bằng Xe tải (Load từ Depot) như bình thường.
  3. Lặp lại cho đến khi không còn vi phạm nào.

Kết quả cuối cùng là một lời giải **chấp nhận được (Feasible)**, sẵn sàng cho giai đoạn tối ưu hóa tiếp theo (Tabu Search).
