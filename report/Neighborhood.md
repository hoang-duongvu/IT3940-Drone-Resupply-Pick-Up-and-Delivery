# Các chiến lược sinh lân cận (Neighborhood Generation Strategies)

Trong thuật toán Tabu Search được triển khai tại `src/optimization.py`, việc tìm kiếm lời giải mới dựa trên việc khám phá vùng lân cận của lời giải hiện tại thông qua 4 loại toán tử di chuyển (move operators). Mỗi loại toán tử tác động lên cấu trúc nghiệm theo cách khác nhau để cải thiện hàm mục tiêu (Makespan).

## 1. Relocate (Di chuyển khách hàng)
- **Mô tả**: Di chuyển một khách hàng từ vị trí hiện tại sang một vị trí khác (có thể trên cùng một xe hoặc xe khác, cùng chuyến hoặc chuyến khác).
- **Phạm vi áp dụng**:
  - Chỉ áp dụng cho khách hàng (không áp dụng cho Depot).
  - Tạm thời bỏ qua khách hàng thuộc cặp Pickup-Delivery (C2) để giảm độ phức tạp tính toán.
  - Không di chuyển về chính vị trí cũ hoặc vị trí liền kề ngay sau đó.
- **Mục tiêu**: Cân bằng tải trọng giữa các xe/chuyến và giảm tổng quãng đường di chuyển của từng xe.

## 2. Swap (Hoán đổi khách hàng)
- **Mô tả**: Chọn ngẫu nhiên hai khách hàng bất kỳ trong hệ thống và hoán đổi vị trí của chúng cho nhau.
- **Phạm vi áp dụng**:
  - Hai khách hàng có thể thuộc cùng một xe hoặc hai xe khác nhau.
  - Tương tự Relocate, tạm thời bỏ qua khách hàng C2.
- **Mục tiêu**: Thay đổi cấu trúc lộ trình mạnh mẽ hơn Relocate, giúp thoát khỏi các cực trị địa phương.

## 3. Add Drone Package (Thêm nhiệm vụ Drone)
- **Mô tả**: Thêm một gói hàng (Package) vào một chuyến bay (Mission) hiện có của Drone.
- **Điều kiện ràng buộc**:
  - Chỉ áp dụng cho gói hàng loại C1 (Delivery from Depot).
  - Gói hàng phải nằm trên lộ trình của xe tải mà Drone đang tương tác (resupply mission).
  - Đảm bảo tải trọng Drone không vượt quá `DRONE_CAPACITY`.
  - Đảm bảo gói hàng chưa được Drone nào khác phục vụ (đang được xe tải vận chuyển từ Depot).
- **Cơ chế cập nhật**: 
  - Nếu gói hàng mới nằm TRƯỚC điểm gặp gỡ (Meet Point) hiện tại trong lộ trình xe tải, Meet Point sẽ được cập nhật lùi về vị trí gói hàng này để đảm bảo Drone có thể lấy hàng kịp thời.

## 4. Remove Drone Package (Bớt nhiệm vụ Drone)
- **Mô tả**: Loại bỏ một gói hàng ra khỏi một chuyến bay của Drone (gói hàng sẽ quay lại nhiệm vụ của xe tải).
- **Cơ chế**:
  - Nếu Mission trở nên rỗng sau khi xóa gói hàng cuối cùng, Mission đó sẽ bị hủy bỏ hoàn toàn.
- **Mục tiêu**: Giảm tải cho Drone nếu việc sử dụng Drone gây ra sự chờ đợi không cần thiết cho xe tải, hoặc để nhường dung lượng cho các gói hàng hiệu quả hơn.

## 5. Cơ chế Cập nhật Mission Drone sau thay đổi Lộ trình (Drone Mission Update)
Khi thực hiện các thao tác **Relocate** hoặc **Swap**, lộ trình của xe tải thay đổi có thể làm hỏng các nhiệm vụ Drone hiện tại (ví dụ: điểm gặp gỡ không còn nằm trên chuyến xe cũ, hoặc các gói hàng bị phân tán sang các chuyến/xe khác nhau). Do đó, một cơ chế "sửa chữa" (`_update_drone_missions`) được kích hoạt ngay sau mỗi lần di chuyển:

1.  **Xác định lại "Neo" (Anchor)**: Với mỗi Mission, thuật toán xác định lại xem đa số các gói hàng của nó đang nằm trên chuyến xe (Trip) nào. Chuyến xe này sẽ trở thành mục tiêu phục vụ mới của Mission.
2.  **Lọc gói hàng**: Loại bỏ các gói hàng không còn nằm trên chuyến xe mục tiêu ra khỏi Mission (chúng sẽ tự động quay về trạng thái được vận chuyển bởi xe tải).
3.  **Cập nhật Điểm gặp (Meet Point)**: 
    - Nếu Mission vẫn còn gói hàng, điểm gặp gỡ mới sẽ được cập nhật lại.
    - Điểm gặp mới được chọn là vị trí khách hàng xuất hiện **sớm nhất** trong lộ trình của chuyến xe mục tiêu trong số các gói hàng mà Drone mang theo. Điều này đảm bảo Drone đến sớm nhất có thể để resupply.

## Chiến lược Lấy mẫu (Sampling Strategy)
Do không gian tìm kiếm lân cận rất lớn, thuật toán không duyệt toàn bộ mà sử dụng chiến lược lấy mẫu ngẫu nhiên (Sampling) kết hợp với tỷ lệ ưu tiên trong mỗi vòng lặp `max_iterations`:

- **Tổng số lượng ứng viên (Candidates)**: 100 moves/vòng lặp.
- **Tỷ lệ phân phối**:
  - **Relocate**: 60% (Ưu tiên tinh chỉnh cục bộ).
  - **Swap**: 30% (Đa dạng hóa cấu trúc).
  - **Drone Moves**: 10% (5% Add + 5% Remove) - Tinh chỉnh phần Drone resupply.

Chiến lược này giúp cân bằng giữa việc `Exploitation` (tinh chỉnh lộ trình xe tải) và `Exploration` (thử nghiệm cấu hình Drone mới), đồng thời đảm bảo thời gian chạy của thuật toán ở mức chấp nhận được.
