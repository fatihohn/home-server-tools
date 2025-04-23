import os
import re
import threading
import traceback
import cv2
import datetime
import subprocess
import time
import shutil
from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()
rtsp_url = os.getenv("MOTION_RECORDER_RTSP_URL")
TARGET_CLASSES = {'person', 'dog', 'cat'}

if not rtsp_url:
    raise ValueError("MOTION_RECORDER_RTSP_URL is not set in the environment variables")
else:
    print(f"MOTION_RECORDER_RTSP_URL: {rtsp_url}")

model = YOLO("yolov8n.pt")
model.fuse()
model.half()
cv2.setNumThreads(1)

def contains_target_object(frame):
    results = model(frame)
    names = model.names
    for box in results[0].boxes:
        class_id = int(box.cls[0])
        label = names[class_id]
        if label in TARGET_CLASSES:
            return True
    return False

def monitor_fps_and_kill(process, min_fps=5, duration=5):
    low_fps_start = None
    fps_pattern = re.compile(r'fps=(\d+(\.\d+)?)')

    for line in iter(process.stderr.readline, b''):
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
                    print("❗ FPS가 너무 낮습니다. 프로세스를 종료합니다.")
                    process.terminate()
                    break
            else:
                low_fps_start = None

def detect_target_in_video(video_path, max_frames=5):
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

def detect_motion_and_record(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("카메라 열기 실패")
        return
    else:
        print("카메라 열기 성공")

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()
    frame_interval = 3
    frame_count = 0

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
                save_dir = f"/recordings/{date_str}"
                os.makedirs(save_dir, exist_ok=True)

                temp_filename = f"/recordings/tmp_{time_str}.mp4"
                final_filename = os.path.join(save_dir, f"motion_{time_str}.mp4")

                try:
                    process = subprocess.Popen(
                        [
                            "ffmpeg",
                            "-y",
                            "-rtsp_transport", "tcp",
                            "-timeout", "5000000",
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
                        ],
                        stderr=subprocess.PIPE,
                        stdout=subprocess.DEVNULL
                    )
                    threading.Thread(target=monitor_fps_and_kill, args=(process,), daemon=True).start()
                    process.wait()
                except Exception as e:
                    process.terminate()

                # 타겟 객체 있는지 확인 후 저장 여부 결정
                if detect_target_in_video(temp_filename):
                    shutil.move(temp_filename, final_filename)
                    print(f"녹화 완료: {final_filename}")
                else:
                    os.remove(temp_filename)
                    print("타겟 객체 없음. 영상 삭제됨.")
                time.sleep(1)

        frame1 = frame2
        frame_count += 1
        if frame_count % frame_interval != 0:
            ret, frame2 = cap.read()
            continue

    cap.release()

if __name__ == "__main__":
    while True:
        try:
            detect_motion_and_record(rtsp_url)
        except Exception as e:
            print("❗ 에러 발생, 5초 후 재시도:")
            traceback.print_exc()
            time.sleep(5)
