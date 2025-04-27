from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import numpy as np

app = Flask(__name__)
model = YOLO("yolov8n.pt")
TARGET_CLASSES = {"person", "dog", "cat"}

@app.route("/detect", methods=["POST"])
def detect():
    file_bytes = np.asarray(bytearray(request.data), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    results = model(img)
    names = model.names
    for box in results[0].boxes:
        if names[int(box.cls[0])] in TARGET_CLASSES:
            return jsonify({"detected": True})
    return jsonify({"detected": False}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
