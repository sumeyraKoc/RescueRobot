import torch
import cv2
import numpy as np
import torchvision.ops as ops
from Model import FullModel

class PersonDetector:
    def __init__(
        self,
        model_path,
        device="cuda",
        img_size=640,
        conf_thres=0.4,
        iou_thres=0.4,
        reg_max=16
    ):
        self.device = device
        self.img_size = img_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.reg_max = reg_max

        # Load model
        self.model = FullModel(num_classes=1, use_ir=False).to(device)
        checkpoint = torch.load(model_path, map_location=device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    # =========================
    # PREPROCESS
    # =========================
    def preprocess(self, image):
        img = cv2.resize(image, (self.img_size, self.img_size))
        tensor = torch.from_numpy(img).permute(2,0,1).float() / 255.0
        tensor = tensor.unsqueeze(0).to(self.device)
        return img, tensor

    # =========================
    # DFL DECODE
    # =========================
    def decode(self, preds):
        boxes = []

        for p in preds:
            B, _, H, W = p.shape
            p = p[0]

            box_pred = p[:4 * self.reg_max]
            obj_pred = p[4 * self.reg_max]

            # DFL decode
            box_pred = box_pred.view(4, self.reg_max, H, W)
            prob = torch.softmax(box_pred, dim=1)

            proj = torch.arange(self.reg_max, device=p.device).view(1, self.reg_max, 1, 1)
            dist = (prob * proj).sum(dim=1)

            y, x = torch.meshgrid(
                torch.arange(H, device=p.device),
                torch.arange(W, device=p.device),
                indexing='ij'
            )

            cx = (x + 0.5) / W
            cy = (y + 0.5) / H

            l, t, r, b = dist

            x1 = cx - l / W
            y1 = cy - t / H
            x2 = cx + r / W
            y2 = cy + b / H

            w = x2 - x1
            h = y2 - y1
            xc = x1 + w / 2
            yc = y1 + h / 2

            obj = torch.sigmoid(obj_pred)

            mask = obj > self.conf_thres
            ys, xs = mask.nonzero(as_tuple=True)

            for y_i, x_i in zip(ys, xs):
                boxes.append([
                    xc[y_i, x_i].item(),
                    yc[y_i, x_i].item(),
                    w[y_i, x_i].item(),
                    h[y_i, x_i].item(),
                    obj[y_i, x_i].item()
                ])

        return boxes

    # =========================
    # NMS
    # =========================
    def nms(self, boxes):
        if len(boxes) == 0:
            return []

        boxes = torch.tensor(boxes)
        scores = boxes[:, 4]

        # xywh → xyxy
        xyxy = torch.zeros((boxes.shape[0], 4))
        xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
        xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
        xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
        xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2

        keep = ops.nms(xyxy, scores, self.iou_thres)
        return boxes[keep].tolist()

    # =========================
    # DRAW
    # =========================
    def draw(self, image, boxes):
        h, w = image.shape[:2]

        for (xc, yc, bw, bh, score) in boxes:
            x1 = int((xc - bw/2) * w)
            y1 = int((yc - bh/2) * h)
            x2 = int((xc + bw/2) * w)
            y2 = int((yc + bh/2) * h)

            cv2.rectangle(image, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(image, f"{score:.2f}", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        return image

    # =========================
    # MAIN INFERENCE
    # =========================
    def predict(self, image, draw=True):
        original = image.copy()

        _, tensor = self.preprocess(image)

        with torch.no_grad():
            preds = self.model(tensor)

        boxes = self.decode(preds)
        boxes = self.nms(boxes)

        if draw:
            return self.draw(original, boxes), boxes

        return boxes