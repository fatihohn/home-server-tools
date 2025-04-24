import os
import re
import threading
import traceback
import cv2
import datetime
import subprocess
import time
import shutil
import select
from dotenv import load_dotenv
from ultralytics import YOLO

# === 설정 ===
load_dotenv()
rtsp_url = os.getenv("MOTION_RECORDER_RTSP_URL")
RECORDINGS_DIR = "/recordings"
TARGET_CLASSES = {'person', 'dog', 'cat'}

if not rtsp_url:
    raise ValueError("MOTION_RECORDER_RTSP_URL is not set in the environment variables")
else:
    print(f"MOTION_RECORDER_RTSP_URL: {rtsp_url}")

# === 모델 로딩 ===
model = YOLO("yolov8n.pt")
model.fuse()
model.half()
cv2.setNumThreads(1)

# === 타겟 객체 감지 ===
def contains_target_object(frame):
    results = model(frame)
    for box in results[0].boxes:
        class_id = int(box.cls[0])
        label = model.names[class_id]
        if label in TARGET_CLASSES:
            return True
    return False

# === FPS 감시 후 비정상적으로 낮으면 프로세스 종료 ===
def monitor_fps_and_kill(process, min_fps=5, duration=5):
    low_fps_start = None
    fps_pattern = re.compile(r'fps=(\d+(\.\d+)?)')

    while True:
        rlist, _, _ = select.select([process.stderr], [], [], 1.0)
        if rlist:
            line = process.stderr.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='ignore').strip()
            print(decoded)
            match = fps_pattern.search(decoded)
            if match:
                fps = float(match.group(1))
                print(f"📉 현재 FPS: {fps}")
                if fps <= min_fps:
                    if low_fps_start is None:
                        low_fps_start = time.time()
                    elif time.time() - low_fps_start > duration:
                        print("❗ FPS 저하로 FFmpeg 종료")
                        process.terminate()
                        break
                else:
                    low_fps_start = None
        elif process.poll() is not None:
            break

# === 영상 내 타겟 객체 존재 여부 확인 ===
def detect_target_in_video(video_path, max_frames=5):
    if not os.path.exists(video_path):
        return False

    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, verbose=False)[0]
        detected = {model.model.names[int(cls)] for cls in results.boxes.cls}
        if detected & TARGET_CLASSES:
            cap.release()
            return True
        frame_count += 1
    cap.release()
    return False

# === 메인 동작 루프 ===
def detect_motion_and_record(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("카메라 열기 실패")
        return
    else:
        print("카메라 열기 성공")

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    while ret:
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (11, 11), 0)
        _, thresh = cv2.threshold(blur, 50, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if any(cv2.contourArea(contour) > 4000 for contour in contours):
            print("모션 감지됨. 객체 인식 중...")
            if contains_target_object(frame2):
                print("사람/동물 인식됨! 30초 녹화 시작...")

                now = datetime.datetime.now()
                date_str = now.strftime("%Y%m%d")
                time_str = now.strftime("%H%M%S")
                save_dir = os.path.join(RECORDINGS_DIR, date_str)
                os.makedirs(save_dir, exist_ok=True)

                temp_filename = os.path.join(RECORDINGS_DIR, f"tmp_{time_str}.mp4")
                final_filename = os.path.join(save_dir, f"motion_{time_str}.mp4")

                cmd = [
                    "timeout", "35s",
                    "ffmpeg",
                    "-y",
                    "-rtsp_transport", "tcp",
                    "-i", rtsp_url,
                    "-r", "15",
                    "-vsync", "vfr",
                    "-t", "30",
                    "-threads", "1",
                    "-vcodec", "libx264",
                    "-preset", "ultrafast",
                    "-bufsize", "2M",
                    "-vf", "scale=960:720",
                    temp_filename,
                ]

                try:
                    process = subprocess.Popen(
                        cmd,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.DEVNULL
                    )
                    threading.Thread(target=monitor_fps_and_kill, args=(process,), daemon=True).start()
                    process.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    print("❗ FFmpeg 타임아웃 - 강제 종료합니다.")
                    process.kill()
                except Exception as e:
                    print("❗ FFmpeg 실행 오류:", str(e))
                    process.kill()

                if os.path.exists(temp_filename) and detect_target_in_video(temp_filename):
                    shutil.move(temp_filename, final_filename)
                    print(f"녹화 완료: {final_filename}")
                else:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                    print("타겟 객체 없음 또는 영상 없음. 파일 삭제됨.")

                time.sleep(1)

        frame1 = frame2
        ret, frame2 = cap.read()

    cap.release()

# === 진입점 ===
if __name__ == "__main__":
    while True:
        try:
            detect_motion_and_record(rtsp_url)
        except Exception:
            print("❗ 에러 발생, 5초 후 재시도:")
            traceback.print_exc()
            time.sleep(5)
