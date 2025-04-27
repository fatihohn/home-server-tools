FROM golang:1.21

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# 앱 디렉토리 만들기
WORKDIR /app

RUN mkdir -p /recordings

# Go 모듈 복사
COPY go.mod go.sum ./
RUN go mod tidy

# 소스 복사
COPY . .

# 빌드
RUN go build -o motion-recorder .

# 컨테이너 시작 시 실행할 명령어
CMD ["./motion-recorder"]