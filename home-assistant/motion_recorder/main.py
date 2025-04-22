import os
import cv2
import datetime
import subprocess
from dotenv import load_dotenv
import time

# TODO. 동물 및 사람 인식 추가

# .env 파일에서 환경변수 로드
load_dotenv()
rtsp_url = os.getenv("RTSP_URL")

if not rtsp_url:
    raise ValueError("RTSP_URL is not set in the environment variables")
else:
    print(f"RTSP_URL: {rtsp_url}")

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
            print("모션 감지됨! 30초 녹화 시작...")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/recordings/motion_{timestamp}.mp4"

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-rtsp_transport", "tcp",
                    "-timeout", "5000000",
                    "-i", rtsp_url,
                    "-r", "15",
                    "-vsync", "vfr",
                    "-t", "30",
                    "-vcodec", "libx264",
                    "-preset", "veryfast",
                    filename,
                ]
            )
            print(f"녹화 완료: {filename}")

            # 30초 재감지 방지
            time.sleep(30)

        frame1 = frame2
        ret, frame2 = cap.read()

    cap.release()
    
detect_motion_and_record(rtsp_url)
