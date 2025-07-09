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
supported_ext = ('.jpg', '.jpeg', '.png')

# Counters
total_images = 0
correct = 0
incorrect = 0

for filename in os.listdir(image_dir):
    if not filename.lower().endswith(supported_ext):
        continue

    total_images += 1
    image_path = os.path.join(image_dir, filename)
    image = cv2.imread(image_path)
    if image is None:
        print(f"[{filename}] Failed to load image.")
        continue

    # Ground truth extraction from filename (remove extension)
    ground_truth = os.path.splitext(filename)[0].upper().replace(" ", "")

    img_height, img_width = image.shape[:2]
    img_center = np.array([img_width / 2, img_height / 2])

    results = model(image)
    selected_box = None
    min_distance = float('inf')

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
        pad = 0
        x1, y1, x2, y2 = selected_box
        x1 = max(x1 - pad, 0)
        y1 = max(y1 - pad, 0)
        x2 = min(x2 + pad, img_width)
        y2 = min(y2 + pad, img_height)
        cropped_plate = image[y1:y2, x1:x2]

        # blurred_plate = cv2.GaussianBlur(cropped_plate, (3, 3), 1.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (5, 5), 2.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (7, 7), 3.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (11, 11), 4.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (15, 15), 5.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (17, 17), 6.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (21, 21), 7.0)
        blurred_plate = cv2.GaussianBlur(cropped_plate, (23, 23), 8.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (25, 25), 9.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (27, 27), 10.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (29, 29), 11.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (31, 31), 12.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (33, 33), 13.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (35, 35), 14.0)
        # blurred_plate = cv2.GaussianBlur(cropped_plate, (37, 37), 15.0)

        # # Show the cropped result
        # cv2.imshow(f"Cropped Plate - {filename}", blurred_plate)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        resized_plate = cv2.resize(blurred_plate, (128, 64))

        input_img = np.expand_dims(resized_plate, axis=0)
        result = ocr_model.run(input_img)

        detected_plate = result[0].strip().upper().replace("_", "") if result else ""


        if detected_plate == ground_truth:
            correct += 1
            status = "BENAR"
        else:
            incorrect += 1
            status = "SALAH"

        print(f"[{filename}] GT: {ground_truth} | Pred: {detected_plate} => {status}")
    else:
        incorrect += 1
        print(f"[{filename}] No license plate detected => SALAH")

# Final results
print("\n====================")
print(f"Total Images: {total_images}")
print(f"Benar: {correct}")
print(f"Salah: {incorrect}")
accuracy = (correct / total_images * 100) if total_images > 0 else 0
print(f"Akurasi: {accuracy:.2f}%")
