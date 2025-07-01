import os
from ultralytics import YOLO
import cv2
from fast_plate_ocr import LicensePlateRecognizer
import numpy as np

# Initialize YOLO model and OCR recognizer
model = YOLO('plate-detection-model/best.pt')
ocr_model = LicensePlateRecognizer('cct-s-v1-global-model')

# Directory containing test images
image_dir = 'test-image-single'  # Change this to your directory path

# Supported image formats
supported_ext = ('.jpg', '.jpeg', '.png')

for filename in os.listdir(image_dir):
    if not filename.lower().endswith(supported_ext):
        continue  # Skip non-image files

    image_path = os.path.join(image_dir, filename)
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        continue

    img_height, img_width = image.shape[:2]
    img_center = np.array([img_width / 2, img_height / 2])

    results = model(image)
    selected_box = None
    min_distance = float('inf')

    # Select the detection box closest to image center
    if results and results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()

        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            box_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
            distance_to_center = np.linalg.norm(box_center - img_center)

            if distance_to_center < min_distance:
                min_distance = distance_to_center
                selected_box = (x1, y1, x2, y2)

    if selected_box is not None:
        pad = 3
        x1, y1, x2, y2 = selected_box
        x1 = max(x1 - pad, 0)
        y1 = max(y1 - pad, 0)
        x2 = min(x2 + pad, img_width)
        y2 = min(y2 + pad, img_height)
        cropped_plate = image[y1:y2, x1:x2]

        # Apply Gaussian blur before resize (recommended)
        blurred_plate = cv2.GaussianBlur(cropped_plate, (11, 11), 4.0)
        resized_plate = cv2.resize(blurred_plate, (128, 64))

        input_img = np.expand_dims(resized_plate, axis=0)  # Shape: (1, 64, 128, 3)
        result = ocr_model.run(input_img)

        print(f"[{filename}] Detected Plate: {result}")
    else:
        print(f"[{filename}] No license plate detected.")
