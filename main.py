from ultralytics import YOLO
import cv2
from fast_plate_ocr import LicensePlateRecognizer
import numpy as np

model = YOLO('plate-detection-model/best.pt')

image_path = ('test-image-single/KB2492YT.jpeg')
image = cv2.imread(image_path)
# These are used later to find the closest box to the center of the image
img_height, img_width = image.shape[:2]
img_center = np.array([img_width / 2, img_height / 2])

results = model(image)

selected_box = None
min_distance = float('inf')

# Find the box that are closest to the center of the image (incase of multiple detections)
if results and results[0].boxes is not None:
    boxes = results[0].boxes.xyxy.cpu().numpy()

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        box_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
        distance_to_center = np.linalg.norm(box_center - img_center)

        if distance_to_center < min_distance:
            min_distance = distance_to_center
            selected_box = (x1, y1, x2, y2)

if selected_box is None:
    print("No license plate detected.")
    exit()

# This padding really helps with the OCR results
# In the IMG_0705.jpeg, if padding is 0 the OCR results in K6185NWH
# But with padding of 3, it results in KB6185WH, the correct result
# Only pad 3 and 4 works, 2 and below or 5 and above breaks the results
# And then we crop the plate
pad = 0
x1, y1, x2, y2 = selected_box
x1 = max(x1 - pad, 0)
y1 = max(y1 - pad, 0)
x2 = min(x2 + pad, img_width)
y2 = min(y2 + pad, img_height)
cropped_plate = image[y1:y2, x1:x2]

# Soften the image slightly
# The OCR model needs a little bit of blurring to work well
blurred_plate = cv2.GaussianBlur(cropped_plate, (23, 23), 8.0)

# Resize plate to the expected input size for OCR
# Resize to 128x64
resized_plate = cv2.resize(blurred_plate, (128, 64))


# Gaussian blur is the best solution for now, 2024/06/24 12:50 AM
# Further improvement of the image hurt the OCR results
# I think because the model is trained on images that are not preprocessed
# And on images that are not high quality, this might be a good thing
# Apply stronger Gaussian blur by increasing kernel size and sigma, currently not needed

# Optional: Show the grayscale plate (for testing purposes)
# cv2.imshow("Selected Plate", resized_plate)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

# OCR expects [1, 64, 128, 3]
input_img = np.expand_dims(resized_plate, axis=0)  # shape: (1, 64, 128, 3)
m = LicensePlateRecognizer('cct-s-v1-global-model')
result = m.run(input_img)

# Ensure we extract string from list
if isinstance(result, list) and len(result) > 0:
    ocr_result = result[0]
else:
    ocr_result = str(result)

# Clean the OCR result
recognized_plate = ocr_result.replace('_', '').replace(' ', '').upper()

print(f"PLATE_RESULT: {recognized_plate}")