import cv2


def apply(image, h: float = 7.0, template_window: int = 7, search_window: int = 21):
    if image.ndim == 2:
        return cv2.fastNlMeansDenoising(image, None, float(h), int(template_window), int(search_window))
    return cv2.fastNlMeansDenoisingColored(image, None, float(h), float(h), int(template_window), int(search_window))
