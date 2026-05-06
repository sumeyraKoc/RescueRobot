# -*- coding: utf-8 -*-

"""
Imports and Dependencies

This section loads all required libraries for:
- Data processing (NumPy, OpenCV)
- Visualization (Matplotlib)
- Deep learning (PyTorch, timm)
- Dataset handling (COCO API)
- Wavelet transforms (DWT)"""

# Standard Library Imports
import os
import random
import shutil
import zipfile
import warnings
import logging

# Third-Party Imports
import cv2
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt

# PyTorch Imports
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.ops as ops

# External ML Libraries
import timm
from pycocotools.coco import COCO
from pytorch_wavelets import DWTForward


# suppress timm warnings (correct logger)
logging.getLogger("timm.models._builder").setLevel(logging.ERROR)

# suppress PyTorch scheduler warning
warnings.filterwarnings(
    "ignore",
    message="Detected call of `lr_scheduler.step()` before `optimizer.step()`"
)

"""## Model and Modules"""
class Backbone(nn.Module):
    def __init__(self, in_ch=3, model_name="mobilenetv3_large_100", out_ch=256):
        super().__init__()

        self.model = timm.create_model(
            model_name,
            pretrained=True,
            features_only=True,
            out_indices=(2, 3, 4),  # stable pyramid levels
            in_chans=in_ch
        )

        self.channels = self.model.feature_info.channels()
        selected_channels = self.channels  # filtered by out_indices

        # unify channels
        self.proj = nn.ModuleList([
            nn.Conv2d(c, out_ch, 1) for c in selected_channels
        ])

        # refinement (adds depth)
        self.refine = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(out_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.SiLU(inplace=True),

                nn.Conv2d(out_ch, out_ch, 3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.SiLU(inplace=True),
            )
            for _ in selected_channels
        ])

    def forward(self, x):
      feats = self.model(x)  # [P3, P4, P5]

      out = []
      for i, f in enumerate(feats):
          f = self.proj[i](f)
          f = self.refine[i](f)
          out.append(f)

      return out

class ScalarConfidenceGate(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.net = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(c, c // 2, 1),
            nn.SiLU(inplace=True),
            nn.Conv2d(c // 2, c, 1)   # per-channel gating
        )

    def forward(self, x):
        w = torch.sigmoid(self.net(x))  # [0, 1]

        # residual-style gating (more stable)
        return x * (0.5 + w)   # range [0.5, 1.5]

class SafeResidualFusion(nn.Module):
    def __init__(self, c):
        super().__init__()

        self.refine = nn.Sequential(
            nn.Conv2d(c * 2, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),

            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
        )

        # learnable fusion weight
        self.alpha = nn.Parameter(torch.tensor(0.5))

    def forward(self, base, new):
        fused = self.refine(torch.cat([base, new], dim=1))

        # table residual fusion
        return base + torch.sigmoid(self.alpha) * fused

"""## Wawelet Transformation and IR Component Specific Classes"""

class WaveletDecompose(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.dwt = DWTForward(J=1, wave='haar')

        # learnable scaling
        self.low_proj = nn.Conv2d(c, c, 1)
        self.high_proj = nn.Conv2d(c * 3, c, 1)

    def forward(self, x):
        yl, yh = self.dwt(x)
        yh = yh[0]  # (B, C, 3, H/2, W/2)

        yh = yh.view(x.size(0), -1, yl.size(2), yl.size(3))

        # normalize and project
        yl = self.low_proj(yl)
        yh = self.high_proj(yh)

        return yl, yh

class FrequencyMixer(nn.Module):
    def __init__(self, c):
        super().__init__()

        self.gate = nn.Sequential(
            nn.Conv2d(c * 2, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
            nn.Conv2d(c, c, 1),
            nn.Sigmoid()
        )

        self.refine = nn.Sequential(
            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True)
        )

    def forward(self, low, high):
        w = self.gate(torch.cat([low, high], dim=1))

        fused = w * low + (1 - w) * high

        return fused + self.refine(fused)  # residual boost

class EdgeEnhance(nn.Module):
    def __init__(self, c):
        super().__init__()

        # Sobel kernels
        kx = torch.tensor([[1,0,-1],[2,0,-2],[1,0,-1]], dtype=torch.float32)
        ky = kx.t()

        self.register_buffer("kx", kx.view(1,1,3,3))
        self.register_buffer("ky", ky.view(1,1,3,3))

        # projection
        self.proj = nn.Conv2d(1, c, 1)

        # normalization
        self.bn = nn.BatchNorm2d(c)

        # learnable strength
        self.alpha = nn.Parameter(torch.tensor(0.2))

    def forward(self, ir):
        if ir is None:
            return None

        # Sobel gradients
        gx = F.conv2d(ir, self.kx, padding=1)
        gy = F.conv2d(ir, self.ky, padding=1)

        # magnitude
        edge = torch.sqrt(gx**2 + gy**2 + 1e-6)

        # normalize
        edge = edge / (edge.mean(dim=[2,3], keepdim=True) + 1e-6)

        # project to feature space
        edge = self.proj(edge)
        edge = self.bn(edge)

        # controlled scaling instead of tanh
        return torch.sigmoid(self.alpha) * edge

class SpatialPoolingAttention(nn.Module):
    def __init__(self, c):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(4, c // 4, 3, padding=1),   # now 4 channels input
            nn.BatchNorm2d(c // 4),
            nn.SiLU(inplace=True),

            nn.Conv2d(c // 4, 1, 1)
        )

    def forward(self, x):
        # standard pooling
        avg = torch.mean(x, dim=1, keepdim=True)
        mx, _ = torch.max(x, dim=1, keepdim=True)

        # directional signals
        gx = torch.mean(x, dim=2, keepdim=True)  # horizontal awareness
        gy = torch.mean(x, dim=3, keepdim=True)  # vertical awareness

        # expand to match H,W
        gx = gx.expand_as(avg)
        gy = gy.expand_as(avg)

        # combine all signals
        attn = torch.cat([avg, mx, gx, gy], dim=1)

        attn = torch.sigmoid(self.conv(attn))

        return x * (0.5 + attn)   # stable residual attention

class FusionBlock(nn.Module):
    def __init__(self, c, use_ir=False, use_wavelet=False):
        super().__init__()

        self.use_ir = use_ir
        self.use_wavelet = use_wavelet

        # CORE
        self.conf = ScalarConfidenceGate(c)
        self.safe = SafeResidualFusion(c)
        self.spatial = SpatialPoolingAttention(c)

        # IR
        self.edge = EdgeEnhance(c)
        self.ir_proj = nn.Conv2d(1, c, 1)

        # adaptive IR gating
        self.ir_gate = nn.Sequential(
            nn.Conv2d(c * 2, c, 1),
            nn.Sigmoid()
        )

        #  WAVELET
        if self.use_wavelet:
            self.wave = WaveletDecompose(c)
            self.freq_mixer = FrequencyMixer(c)

    def forward(self, rgb, ir=None):
        # RGB BASE
        rgb = self.conf(rgb)
        fused = rgb


        # IR FUSION
        if self.use_ir and ir is not None:

            ir_resized = F.interpolate(
                ir, size=rgb.shape[-2:], mode='bilinear', align_corners=False
            )

            ir_feat = self.ir_proj(ir_resized)

            # main fusion (residual)
            fused = self.safe(fused, ir_feat)

            # EDGE GUIDANCE
            edge = self.edge(ir)
            if edge is not None:
                edge = F.interpolate(
                    edge, size=fused.shape[-2:], mode='bilinear', align_corners=False
                )

                # gated edge fusion
                w = self.ir_gate(torch.cat([fused, edge], dim=1))
                fused = fused * (1 - w) + edge * w

        # WAVELET (OPTIONAL)
        if self.use_wavelet and self.use_ir and ir is not None:

            r_low, r_high = self.wave(rgb)
            i_low, i_high = self.wave(ir)

            freq = self.freq_mixer(r_low + i_low, r_high + i_high)

            freq = F.interpolate(
                freq, size=fused.shape[-2:], mode='bilinear', align_corners=False
            )

            fused = fused + 0.1 * freq  # light residual

        # SPATIAL ATTENTION
        fused = self.spatial(fused)

        return fused

class FusionBackbone(nn.Module):
    def __init__(self, use_ir=False, out_ch=256):
        super().__init__()

        self.use_ir = use_ir
        self.out_ch = out_ch

        # RGB backbone
        self.rgb = Backbone(in_ch=3, out_ch=out_ch)

        # now channels are FIXED
        ch = [out_ch, out_ch, out_ch]

        # fusion blocks
        self.fusion = nn.ModuleList([
            FusionBlock(c, use_ir=use_ir) for c in ch
        ])

        # IR pyramid (scale-aware)
        if use_ir:
            self.ir_downsample = nn.ModuleList([
                nn.Identity(),                 # P3
                nn.AvgPool2d(2),              # P4
                nn.AvgPool2d(4)               # P5
            ])

    def forward(self, rgb, ir=None):
        # RGB FEATURES
        rgb_feats = self.rgb(rgb)   # [P3, P4, P5]

        # RGB-ONLY MODE
        if not self.use_ir or ir is None:
            return rgb_feats


        # IR PREP (multi-scale)
        ir_feats = []
        for i in range(len(rgb_feats)):
            ir_scaled = self.ir_downsample[i](ir)
            ir_feats.append(ir_scaled)

        # FUSION
        fused = []
        for i in range(len(rgb_feats)):
            f = self.fusion[i](rgb_feats[i], ir_feats[i])
            fused.append(f)

        return fused

class SimpleFPN(nn.Module):
    def __init__(self, c=256):
        super().__init__()

        # TOP-DOWN
        self.lat5 = nn.Conv2d(c, c, 1)
        self.lat4 = nn.Conv2d(c, c, 1)

        self.smooth4 = nn.Sequential(
            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
        )

        self.smooth3 = nn.Sequential(
            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
        )

        # BOTTOM-UP (PAN)
        self.down3 = nn.Conv2d(c, c, 3, stride=2, padding=1)
        self.down4 = nn.Conv2d(c, c, 3, stride=2, padding=1)

        self.out4 = nn.Sequential(
            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
        )

        self.out5 = nn.Sequential(
            nn.Conv2d(c, c, 3, padding=1),
            nn.BatchNorm2d(c),
            nn.SiLU(inplace=True),
        )

    def forward(self, feats):
        c3, c4, c5 = feats

        # TOP-DOWN
        p5 = c5

        p4 = c4 + F.interpolate(self.lat5(c5), scale_factor=2, mode="nearest")
        p4 = self.smooth4(p4)

        p3 = c3 + F.interpolate(self.lat4(p4), scale_factor=2, mode="nearest")
        p3 = self.smooth3(p3)

        # BOTTOM-UP
        p4 = p4 + self.down3(p3)
        p4 = self.out4(p4)

        p5 = p5 + self.down4(p4)
        p5 = self.out5(p5)

        return [p3, p4, p5]

class YOLOHeadDFL(nn.Module):
    def __init__(self, channels, num_classes=1, reg_max=16):
        super().__init__()

        self.num_classes = num_classes
        self.reg_max = reg_max

        self.heads = nn.ModuleList([
            self._build_head(c) for c in channels
        ])

    def _build_head(self, c):
        return nn.ModuleDict({

            "stem": nn.Sequential(
                nn.Conv2d(c, c, 3, padding=1),
                nn.BatchNorm2d(c),
                nn.SiLU(inplace=True),

                nn.Conv2d(c, c, 3, padding=1),
                nn.BatchNorm2d(c),
                nn.SiLU(inplace=True),
            ),

            # DFL box: 4 * reg_max
            "box": nn.Conv2d(c, 4 * self.reg_max, 1),

            "obj": nn.Conv2d(c, 1, 1),
            "cls": nn.Conv2d(c, self.num_classes, 1),
        })

    def forward(self, feats):
        outs = []

        for head, x in zip(self.heads, feats):
            x = head["stem"](x)

            box = head["box"](x)   # [B, 4*reg_max, H, W]
            obj = head["obj"](x)
            cls = head["cls"](x)

            out = torch.cat([box, obj, cls], dim=1)
            outs.append(out)

        return outs

class FullModel(nn.Module):
    def __init__(self, num_classes=1, use_ir=False):
        super().__init__()

        self.use_ir = use_ir

        # backbone
        self.backbone = FusionBackbone(use_ir=use_ir)

        self.out_ch = 256

        # FPN
        self.fpn = SimpleFPN(self.out_ch)

        # head (must match FPN!)
        self.detector = YOLOHeadDFL([self.out_ch] * 3, num_classes)

    def forward(self, rgb, ir=None):

        feats = self.backbone(rgb, ir)   # → [256,256,256]

        feats = self.fpn(feats)          # → [256,256,256]

        preds = self.detector(feats)

        return preds







