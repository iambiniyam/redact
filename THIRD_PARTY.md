# Third-party components

## YuNet face detector

- Model: `face_detection_yunet_2023mar.onnx`
- Source: [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- License: see the OpenCV Zoo model directory (Apache-2.0 for the zoo, with model-specific notes)
- Used for face detection; downloaded by `scripts/download_models.py`.

## Indra OCR (optional)

- Code: Apache-2.0.
- Model weights: OpenRAIL-M. Free for research, personal use, and startups under $20M funding or revenue. Not for building a competing OCR API. Read the upstream license before commercial use.
- Downloaded only when `--with-indra` is used.

## RapidOCR

- Package: `rapidocr-onnxruntime`
- License: Apache-2.0
- OCR models are bundled with the wheel; no separate download.

## Other runtime

- PyMuPDF (AGPL-3.0 or commercial), OpenCV (Apache-2.0), Pillow (HPND), NumPy (BSD-3-Clause).
- Note: PyMuPDF's AGPL license may matter for redistribution; review before commercial use.
