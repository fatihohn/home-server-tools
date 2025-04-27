package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

var (
	rtspURL       = os.Getenv("MOTION_RECORDER_RTSP_URL")
	yoloAPI       = os.Getenv("MOTION_RECORDER_YOLO_API")
	baseDirectory = os.Getenv("MOTION_RECORDER_SAVE_PATH")
)

const (
	recordingTime = 30 * time.Second // 녹화 시간 30초
)

func captureFrame(rtspURL string) ([]byte, error) {
	cmd := exec.Command(
		"ffmpeg",
		"-rtsp_transport", "tcp",
		"-i", rtspURL,
		"-frames:v", "1",
		"-f", "image2pipe",
		"-vcodec", "png",
		"-",
	)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = io.Discard

	if err := cmd.Run(); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func detectMotion(frame []byte) (bool, error) {
	req, err := http.NewRequest("POST", yoloAPI, bytes.NewReader(frame))
	if err != nil {
		return false, err
	}
	req.Header.Set("Content-Type", "application/octet-stream")

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		return true, nil
	}
	return false, nil
}

func ensureDir(path string) error {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return os.MkdirAll(path, 0755)
	}
	return nil
}

func startRecording(rtspURL, outputPath string, duration time.Duration) (*exec.Cmd, error) {
	cmd := exec.Command(
		"timeout", "35s",
		"ffmpeg",
		"-y",
		"-rtsp_transport", "tcp",
		"-i", rtspURL,
		"-t", fmt.Sprintf("%.0f", duration.Seconds()),
    "-vf", "scale=960:720",
    "-c:v", "libx264",  // 비디오 코덱을 libx264로 변경
    "-preset", "ultrafast",  // 빠른 인코딩을 위한 옵션
    "-c:a", "aac",      // 오디오 코덱을 aac로 설정
		"-threads", "1",
		outputPath,
	)
	err := cmd.Start()
	if err != nil {
		return nil, err
	}
	return cmd, nil
}

func buildOutputPath(baseDir string, t time.Time) (string, error) {
	dateDir := t.Format("20060102")
	dirPath := filepath.Join(baseDir, dateDir)
	if err := ensureDir(dirPath); err != nil {
		return "", err
	}
	filename := fmt.Sprintf("motion_%s.mp4", t.Format("150405"))
	return filepath.Join(dirPath, filename), nil
}

func main() {
	isRecording := false

	for {
		frame, err := captureFrame(rtspURL)
		if err != nil {
			fmt.Println("Failed to capture frame:", err)
			time.Sleep(1 * time.Second)
			continue
		}

		motionDetected, err := detectMotion(frame)
		if err != nil {
			fmt.Println("YOLO detection error:", err)
			time.Sleep(1 * time.Second)
			continue
		}

		if motionDetected && !isRecording {
			now := time.Now()
			outputPath, err := buildOutputPath(baseDirectory, now)
			if err != nil {
				fmt.Println("Failed to build output path:", err)
				continue
			}
			fmt.Println("Motion detected! Start recording:", outputPath)

			cmd, err := startRecording(rtspURL, outputPath, recordingTime)
			if err != nil {
				fmt.Println("Failed to start recording:", err)
				continue
			}
			isRecording = true

			go func() {
				fmt.Println("Recording in progress...")
				if err := cmd.Wait(); err != nil {
					fmt.Println("Recording error:", err)
				}
				// Wait for the recording to finish
				cmd.Wait()
				isRecording = false
				fmt.Println("Recording finished:", outputPath)
			}()
		}

		time.Sleep(1 * time.Second)
	}
}
