from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms


class ReIDSystem:
    """
    Re-Identification by appearance using a generic image encoder (ResNet50 by default).
    - Gallery: dict employee_id -> list[np.ndarray] of L2-normalized embeddings
    - Matching: cosine similarity against gallery prototypes
    """

    def __init__(self, device: str = "cpu") -> None:
        self.device = torch.device("cuda" if device == "cuda" and torch.cuda.is_available() else "cpu")
        # Lightweight backbone (pretrained on ImageNet). In absence of torchreid, this is a practical baseline.
        backbone = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        backbone.fc = nn.Identity()
        self.encoder: nn.Module = backbone.to(self.device).eval()
        self.preprocess = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 128)),  # typical ReID aspect
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.gallery: Dict[str, List[np.ndarray]] = {}
        self.gallery_path = Path("models") / "reid_gallery.pkl"
        self._load_gallery()

    def _load_gallery(self) -> None:
        if self.gallery_path.exists():
            try:
                self.gallery = pickle.loads(self.gallery_path.read_bytes())
            except Exception:
                self.gallery = {}

    def save_gallery(self) -> None:
        self.gallery_path.parent.mkdir(parents=True, exist_ok=True)
        self.gallery_path.write_bytes(pickle.dumps(self.gallery))

    @torch.inference_mode()
    def embed(self, img_bgr: np.ndarray) -> np.ndarray:
        # img_bgr: HxWxC (OpenCV)
        if img_bgr is None or img_bgr.size == 0:
            return np.zeros((2048,), dtype=np.float32)
        img_rgb = img_bgr[:, :, ::-1].copy()
        x = self.preprocess(img_rgb).unsqueeze(0).to(self.device)
        feat = self.encoder(x).flatten().detach().cpu().numpy().astype(np.float32)
        # L2 normalize
        n = np.linalg.norm(feat) + 1e-12
        return feat / n

    def add_to_gallery(self, emp_id: str, embeddings: List[np.ndarray]) -> None:
        if not embeddings:
            return
        self.gallery.setdefault(emp_id, [])
        self.gallery[emp_id].extend([e.astype(np.float32) for e in embeddings if e is not None and e.size > 0])

    def match(self, emb: np.ndarray) -> Tuple[Optional[str], float]:
        if not self.gallery or emb is None or emb.size == 0:
            return None, 0.0
        best_emp = None
        best_sim = -1.0
        for emp, embs in self.gallery.items():
            if not embs:
                continue
            # compare to average prototype for speed
            proto = np.mean(np.stack(embs, axis=0), axis=0)
            proto = proto / (np.linalg.norm(proto) + 1e-12)
            sim = float(np.dot(emb, proto))
            if sim > best_sim:
                best_sim = sim
                best_emp = emp
        return best_emp, best_sim
