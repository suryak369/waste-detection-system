# -*- coding: utf-8 -*-
from pathlib import Path
import json
from typing import Union
from codecarbon import EmissionsTracker
import pandas as pd
import torch

from . import shared_data as base
from . import models
from . import trainer
from . import hyperparameter_search as hyper



def configure(name: str, config: Union[Path, str]):
    configuration = Path(config)
    chk_dir = configuration.parent.resolve()
    with open(configuration, 'r') as f:
        configuration = json.load(f)
    
    epochs = configuration['epochs']
    momentum = configuration['momentum']
    optimizer = configuration['optimizer'] if 'optimizer' in configuration.keys()\
        else 'SGD'
    scheduler = configuration['scheduler'] if 'scheduler' in configuration.keys()\
        else None
    scheduler_steps = configuration['scheduler_steps'] if 'scheduler_steps' in\
        configuration.keys() else None

    lr = configuration['lr']

    weight_decay = configuration['weight_decay']

    bs = configuration['batch_size']
    checkpoint_dir = chk_dir / name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = str(checkpoint_dir)
    
    results_dir = Path(configuration['results_dir']) / name if 'results_dir' in configuration.keys()\
        else checkpoint_dir

    return {
        'epochs' : epochs, 'momentum' : momentum,  'optimizer' : optimizer,
        'scheduler' : scheduler, 'scheduler_steps' : scheduler_steps,
        'lr' : lr, 'bs' : bs, 'weight_decay' : weight_decay,
        'checkpoint_dir' : checkpoint_dir, 'results_dir' : results_dir
    }



def hyperparameter_search(labels: pd.DataFrame, name: str, config: Union[Path, str],
    selected_model : models.AVAILABLE_MODELS, num_classes : int, tll : int,
    resortit_zw : int, weights: Union[Path, str, None] = None):
    
    configuration = configure(name, config)

    if weights: weights = torch.load(weights)
    
    hyper.hyperparameter_search(labels, name, configuration, selected_model, 
        num_classes, tll, resortit_zw, weights)




def train(labels: pd.DataFrame, name: str, config: Union[Path, str], resortit_zw : int,
            selected_model : models.AVAILABLE_MODELS, num_classes : int, tll : int,
            weights: Union[Path, str, None] = None):

    configuration = configure(name, config)
    
    model = models.get_base_model(num_classes, selected_model, tll)
    assert model is not None

    if weights:
        weights = torch.load(weights)
        model = models.load_partial_weights(model, weights)
    
    gpu_ids = [base.GPU] if torch.cuda.is_available() and base.USE_GPU else None
    
    tracker = EmissionsTracker(project_name=name, experiment_id='train', gpu_ids=gpu_ids, 
        log_level='error', tracking_mode='process', measure_power_secs=30)  # type: ignore

    tracker.start()
    best_model_path, model_trainer = trainer.train(model=model, dataset=labels, 
        config=configuration, 
        neptune_project=base.NEPTUNE_PROJECTS[selected_model][resortit_zw])
    tracker.stop()