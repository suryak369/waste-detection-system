from typing import List, Dict
from pathlib import Path

from pandas import DataFrame
import numpy as np
from PIL import Image

from .transformations import ComposeDouble, Clip, normalize_01
from .transformations import FunctionWrapperDouble
import torch
from torchvision import transforms
from torch.utils.data import Dataset

from . import shared_data as base



class WasteDetectionDataset(Dataset):
    def __init__(self, data: DataFrame, mapping: Dict) -> None:
        self.transforms = ComposeDouble([
            Clip(),
            FunctionWrapperDouble(np.moveaxis, source=-1, destination=0),
            FunctionWrapperDouble(normalize_01)
        ])
        self.mapping = mapping

        self.inputs : List[Path] = []
        self.targets : Dict[Path, List] = {}

        for img_path in data.path.unique():
            idx = base.ROOT / img_path
            self.inputs.append(idx)
            self.targets[idx] = data[data.path == img_path].apply(  # type: ignore
                lambda row: {
                    'label' : row['label'],
                    'bounding-box': [row['bbox-x'], row['bbox-y'],
                                    row['bbox-x']+row['bbox-w'], 
                                    row['bbox-y']+row['bbox-h']]
                }, 
                axis=1
            )
    
    def __len__(self) -> int:
        return len(self.inputs)
    
    def __getitem__(self, index) -> Dict:
        input_path = self.inputs[index]
        targets = self.targets[input_path]

        x = transforms.ToTensor()(Image.open(input_path).convert('RGB'))
        
        boxes = [row['bounding-box'] for row in targets]
        boxes = torch.tensor(boxes).to(torch.float32)

        labels = [self.mapping[row['label']] for row in targets]
        labels = torch.tensor(labels).to(torch.int64)

        y = {'boxes' : boxes, 'labels' : labels}

        return {'x' : x, 'y' : y, 'path' : input_path}