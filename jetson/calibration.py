import cv2
import numpy as np
import time
import math

# ================= CẤU HÌNH HỆ THỐNG =================
CAM_INDEX = 0                 # Camera USB
FRAME_WIDTH = 320            # Giảm độ phân giải cho Jetson Nano
FRAME_HEIGHT = 240

ANGLE_TOLERANCE = 5.0        # Độ lệch cho phép (độ)
SMOOTHING_ALPHA = 0.7        # 0–1, càng cao càng mượt, phản ứng chậm hơn

ROI_HEIGHT_RATIO = 0.5       # Dùng nửa dưới khung hình
NUM_INIT_FRAMES = 30         # Số frame khởi động để lấy góc thẳng

SHOW_DEBUG = False           # Đặt True nếu cần xem debug trên màn hình
# ======================================================


class MotorController:
    """
    Lớp này là chỗ nối với hệ thống điều khiển thật.
    Thay nội dung trong send_command() cho phù hợp với mạch điều khiển của bạn.
    """

    def __init__(self):
        # Khởi tạo UART / GPIO / CAN / v.v. ở đây nếu cần
        # Ví dụ:
        # import serial
        # self.ser = serial.Serial('/dev/ttyTHS1', 115200, timeout=0.1)
        pass

    def send_command(self, cmd: str):
        """
        cmd thuộc { 'S', 'L', 'R' }.
        - 'S': dừng xe
        - 'L': chỉnh hướng sang trái
        - 'R': chỉnh hướng sang phải
        """
        # TODO: thay print bằng lệnh gửi xuống mạch điều khiển.
        # Ví dụ nếu dùng UART:
        # self.ser.write((cmd + '\n').encode('ascii'))

        print(f"[MOTOR] {cmd}")


def preprocess_frame(frame):
    """
    Tiền xử lý ảnh: grayscale, blur, Canny, ROI.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    h, w = edges.shape
    mask = np.zeros_like(edges)
    y_top = int(h * (1 - ROI_HEIGHT_RATIO))
    roi_vertices = np.array([[
        (0, y_top),
        (w, y_top),
        (w, h),
        (0, h)
    ]], dtype=np.int32)
    cv2.fillPoly(mask, roi_vertices, 255)
    roi = cv2.bitwise_and(edges, mask)

    return roi


def detect_dominant_angle(edge_img):
    """
    Tìm các đoạn thẳng bằng HoughLinesP, tính góc trung bình (độ).
    Trả về None nếu không tìm được đường.
    """
    lines = cv2.HoughLinesP(
        edge_img,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=20,
        maxLineGap=8
    )

    if lines is None:
        return None

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0:
            angle = 90.0
        else:
            angle = math.degrees(math.atan2(dy, dx))
        angles.append(angle)

    if not angles:
        return None

    return float(np.mean(angles))


def init_baseline_angle(cap):
    """
    Lấy góc thẳng ban đầu khi khởi động:
    - Xe đứng yên, đầu xe đặt thẳng theo tuyến đường chuẩn.
    - Camera nhìn thấy vạch đường.
    - Lấy NUM_INIT_FRAMES frame để tính trung bình góc.
    """
    init_angles = []

    for _ in range(NUM_INIT_FRAMES):
        ret, frame = cap.read()
        if not ret:
            continue

        roi = preprocess_frame(frame)
        angle = detect_dominant_angle(roi)
        if angle is not None:
            init_angles.append(angle)

        time.sleep(0.03)

    if not init_angles:
        return None

    return float(np.mean(init_angles))


def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("Lỗi: không mở được camera.")
        return

    motor = MotorController()

    print("Đang lấy góc thẳng ban đầu, giữ xe đứng yên và đặt thẳng theo tuyến đường...")
    baseline_angle = init_baseline_angle(cap)

    if baseline_angle is None:
        print("Lỗi: không phát hiện được đường trong giai đoạn khởi động. Thoát.")
        cap.release()
        return

    print(f"Góc thẳng chuẩn (baseline_angle) = {baseline_angle:.2f} độ")

    smoothed_angle = baseline_angle
    already_sent_stop_for_this_deviation = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Mất tín hiệu camera.")
                break

            roi = preprocess_frame(frame)
            angle = detect_dominant_angle(roi)

            command_to_send = None

            if angle is not None:
                smoothed_angle = (
                    SMOOTHING_ALPHA * smoothed_angle
                    + (1.0 - SMOOTHING_ALPHA) * angle
                )
                diff = smoothed_angle - baseline_angle

                # Không lệch: không ra lệnh, reset trạng thái
                if abs(diff) <= ANGLE_TOLERANCE:
                    command_to_send = None
                    already_sent_stop_for_this_deviation = False

                else:
                    # Lệch: nếu chưa stop thì gửi S, sau đó mới L/R
                    if not already_sent_stop_for_this_deviation:
                        command_to_send = "S"
                        already_sent_stop_for_this_deviation = True
                    else:
                        # diff > 0: lệch theo một phía, chỉnh L
                        # diff < 0: lệch phía ngược lại, chỉnh R
                        if diff > 0:
                            command_to_send = "L"
                        else:
                            command_to_send = "R"

                if command_to_send is not None:
                    motor.send_command(command_to_send)
                    print(
                        f"angle={smoothed_angle:.2f}°, "
                        f"baseline={baseline_angle:.2f}°, "
                        f"diff={diff:.2f}° -> cmd={command_to_send}"
                    )

            # Nếu angle is None (không thấy đường): không gửi lệnh, xử lý ở tầng cao hơn nếu cần

            if SHOW_DEBUG:
                debug_frame = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                cv2.imshow("ROI", debug_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

    except KeyboardInterrupt:
        print("Dừng bởi người dùng.")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
