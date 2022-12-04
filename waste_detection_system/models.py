# -*- coding: utf-8 -*-

from . import shared_data as base

from enum import Enum
from torch import load, hub
from itertools import chain

from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2, FasterRCNN_ResNet50_FPN_V2_Weights, FasterRCNN
from torchvision.models.detection import fcos_resnet50_fpn, FCOS_ResNet50_FPN_Weights, FCOS
from torchvision.models.detection import retinanet_resnet50_fpn_v2, RetinaNet_ResNet50_FPN_V2_Weights, RetinaNet
from torchvision.models.detection import ssd300_vgg16, SSD300_VGG16_Weights
from torchvision.models.detection.ssd import SSD

from torchinfo import summary

AVAILABLE_MODELS = Enum('Models', 'FASTERRCNN FCOS RETINANET SSD')


def load_partial_weights(model, weights):
    # load partial weights for warmstarting
    #model.load_state_dict(weights, strict=False)
    model_dict = model.state_dict()
    weights = {k: v for k, v in weights.items() if k in model_dict and v.size() == model_dict[k].size()}
    model_dict.update(weights)
    model.load_state_dict(model_dict)
    return model


def print_stats(model, transfer_learning_level):
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f'TLL = {transfer_learning_level} | {trainable_params} trainable params '
        f'({round((trainable_params/total_params)*100, 2)}%) | '
        f'{total_params} total params')


def pretty_summary(model):
    print(summary(model, depth=3, col_names=["num_params", "trainable"]))

# TRANSFER LEARNING LEVEL:
# TLL=0 : train from scratch
# TLL=1 : transfer learning, train only the head
# TLL>1 : fine-tuning, trains the head plus the (n-1) number of layers from top to bottom
#         MIN = 2, MAX = 5

def get_base_model(num_classes : int, chosen_model : AVAILABLE_MODELS, 
                    transfer_learning_level : int):
    if chosen_model == AVAILABLE_MODELS.FASTERRCNN: return get_fasterrcnn(num_classes, 
                                                                transfer_learning_level)
    elif chosen_model == AVAILABLE_MODELS.FCOS: return get_fcos(num_classes, 
                                                                transfer_learning_level)
    elif chosen_model == AVAILABLE_MODELS.RETINANET: return get_retinanet(num_classes, 
                                                                transfer_learning_level)
    elif chosen_model == AVAILABLE_MODELS.SSD : return get_ssd(num_classes, 
                                                                transfer_learning_level)
    else: return None


def apply_tll_to_fasterrcnn(model, transfer_learning_level : int):
    # TLL=0 : train from scratch
    if transfer_learning_level == 0:
        for param in model.parameters():
            param.requires_grad = True
    # TLL=1 : transfer learning, train only the head
    elif transfer_learning_level == 1:
        for param in chain(model.transform.parameters(),
                           model.backbone.parameters(),
                           model.rpn.parameters()):
            param.requires_grad = False
        for param in model.roi_heads.parameters():
            param.requires_grad = True
    # TLL>1 : fine-tuning, trains the head plus the (n-1) number of layers from top to bottom
    elif transfer_learning_level >= 2 and transfer_learning_level <= 5:
        for param in model.transform.parameters():
            param.requires_grad = False
        
        if transfer_learning_level == 2:
            for param in model.backbone.parameters():
                param.requires_grad = False
        elif transfer_learning_level == 3:
            for param in model.backbone.body.parameters():
                param.requires_grad = False
        elif transfer_learning_level >= 4:
            for child in list(model.backbone.body.children())[:7]:
                for param in child.parameters():
                    param.requires_grad = False
            for child in list(model.backbone.body.children())[7:]:
                for param in child.parameters():
                    param.requires_grad = True
        
        if transfer_learning_level >= 3:
            for param in model.backbone.fpn.parameters():
                param.requires_grad = True
        
        for param in model.rpn.parameters():
            param.requires_grad = True
        for param in model.roi_heads.parameters():
            param.requires_grad = True
    print_stats(model, transfer_learning_level)
    return model


def apply_tll_to_fcos_retinanet(model, transfer_learning_level : int):
    # TLL=0 : train from scratch
    if transfer_learning_level == 0:
        for param in model.parameters():
            param.requires_grad = True
    # TLL=1 : transfer learning, train only the head
    elif transfer_learning_level == 1:
        for param in chain(model.transform.parameters(),
                           model.backbone.parameters(),
                           model.anchor_generator.parameters(),
                           model.head.regression_head.parameters()):
            param.requires_grad = False
        for param in model.head.classification_head.parameters():
            param.requires_grad = True
    # TLL>1 : fine-tuning, trains the head plus the (n-1) number of layers from top to bottom
    elif transfer_learning_level >= 2 and transfer_learning_level <= 5:
        for param in model.transform.parameters():
            param.requires_grad = False
        
        if transfer_learning_level == 2:
            for param in model.backbone.parameters():
                param.requires_grad = False
        elif transfer_learning_level == 3:
            for param in model.backbone.body.parameters():
                param.requires_grad = False
        elif transfer_learning_level == 4:
            for child in list(model.backbone.body.children())[:7]:
                for param in child.parameters():
                    param.requires_grad = False
            for child in list(model.backbone.body.children())[7:]:
                for param in child.parameters():
                    param.requires_grad = True
        elif transfer_learning_level == 5:
            for child in list(model.backbone.body.children())[:6]:
                for param in child.parameters():
                    param.requires_grad = False
            for child in list(model.backbone.body.children())[6:]:
                for param in child.parameters():
                    param.requires_grad = True
        
        if transfer_learning_level >= 3:
            for param in model.backbone.fpn.parameters():
                param.requires_grad = True
        
        for param in model.anchor_generator.parameters():
            param.requires_grad = True
        for param in model.head.parameters():
            param.requires_grad = True
    print_stats(model, transfer_learning_level)
    return model


def apply_tll_to_ssd(model, transfer_learning_level : int):
    # TLL=0 : train from scratch
    if transfer_learning_level == 0:
        for param in model.parameters():
            param.requires_grad = True
    # TLL=1 : transfer learning, train only the head
    elif transfer_learning_level == 1:
        for param in chain(model.transform.parameters(),
                           model.backbone.parameters(),
                           model.anchor_generator.parameters(),
                           model.head.regression_head.parameters()):
            param.requires_grad = False
        for param in model.head.classification_head.parameters():
            param.requires_grad = True
    # TLL>1 : fine-tuning, trains the head plus the (n-1) number of layers from top to bottom
    elif transfer_learning_level >= 2 and transfer_learning_level <= 5:
        for param in model.transform.parameters():
            param.requires_grad = False
        
        if transfer_learning_level == 2:
            for param in model.backbone.parameters():
                param.requires_grad = False
        elif transfer_learning_level == 3:
            for param in model.backbone.features.parameters():
                param.requires_grad = False
            for child in list(model.backbone.extra.children())[:2]:
                for param in child.parameters():
                    param.requires_grad = False
            for child in list(model.backbone.extra.children())[2:]:
                for param in child.parameters():
                    param.requires_grad = True
        elif transfer_learning_level == 4:
            for param in model.backbone.features.parameters():
                param.requires_grad = False
            for child in list(model.backbone.extra.children())[:1]:
                for param in child.parameters():
                    param.requires_grad = False
            for child in list(model.backbone.extra.children())[1:]:
                for param in child.parameters():
                    param.requires_grad = True
        elif transfer_learning_level == 5:
            for param in model.backbone.features.parameters():
                param.requires_grad = False
            for param in model.backbone.extra.parameters():
                param.requires_grad = True
        
        for param in model.anchor_generator.parameters():
            param.requires_grad = True
        for param in model.head.parameters():
            param.requires_grad = True
    print_stats(model, transfer_learning_level)
    return model


def get_fasterrcnn(num_classes : int, transfer_learning_level : int):
    FasterRCNN.model_num_classes = 0  # type: ignore
    model = load_partial_weights(
            model=fasterrcnn_resnet50_fpn_v2(num_classes=num_classes+1),
            weights=FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT.get_state_dict(progress=True)
    )
    model.model_num_classes = num_classes+1  # type: ignore
    return apply_tll_to_fasterrcnn(model, transfer_learning_level)


def get_fcos(num_classes : int, transfer_learning_level : int):
    FCOS.model_num_classes = 0  # type: ignore
    model = load_partial_weights(
            model=fcos_resnet50_fpn(num_classes=num_classes+1),
            weights=FCOS_ResNet50_FPN_Weights.DEFAULT.get_state_dict(progress=True)
    )
    model.model_num_classes = num_classes+1  # type: ignore
    return apply_tll_to_fcos_retinanet(model, transfer_learning_level)


def get_retinanet(num_classes : int, transfer_learning_level : int):
    RetinaNet.model_num_classes = 0  # type: ignore
    model = load_partial_weights(
            model=retinanet_resnet50_fpn_v2(num_classes=num_classes+1),
            weights=RetinaNet_ResNet50_FPN_V2_Weights.DEFAULT.get_state_dict(progress=True)
    )
    model.model_num_classes = num_classes+1  # type: ignore
    return apply_tll_to_fcos_retinanet(model=model, transfer_learning_level=transfer_learning_level)
    

def get_ssd(num_classes : int, transfer_learning_level : int):
    SSD.model_num_classes = 0  # type: ignore
    model = load_partial_weights(
            model=ssd300_vgg16(num_classes=num_classes+1),
            weights=SSD300_VGG16_Weights.DEFAULT.get_state_dict(progress=True)
    )
    model.model_num_classes = num_classes+1  # type: ignore
    return apply_tll_to_ssd(model, transfer_learning_level)