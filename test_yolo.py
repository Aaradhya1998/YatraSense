from ultralytics import YOLO

model = YOLO('yolov8n.pt')
results = model('https://ultralytics.com/images/bus.jpg', classes=[0])
print(results)