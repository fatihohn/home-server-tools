#!/bin/bash

# 기준: 7일 이상 지난 /recordings 내 디렉토리 삭제
find /recordings/* -maxdepth 0 -type d -mtime +14 -exec rm -rf {} \;
