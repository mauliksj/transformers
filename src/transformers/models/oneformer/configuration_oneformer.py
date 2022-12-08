# coding=utf-8
# Copyright 2022 SHI-Labs Copyright 2022 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""OneFormer model configuration"""
import copy
from typing import Dict, Optional

from transformers import MaskFormerSwinConfig

from ...configuration_utils import PretrainedConfig
from ...utils import logging
from ..auto import CONFIG_MAPPING


logger = logging.get_logger(__name__)

ONEFORMER_PRETRAINED_CONFIG_ARCHIVE_MAP = {
    "shi-labs/oneformer_ade20k_swin_tiny": (
        "https://huggingface.co/shi-labs/oneformer_ade20k_swin_tiny/blob/main/config.json"
    ),
    # See all OneFormer models at https://huggingface.co/models?filter=oneformer
}


class OneFormerConfig(PretrainedConfig):
    r"""
    This is the configuration class to store the configuration of a [`OneFormerModel`]. It is used to instantiate a
    OneFormer model according to the specified arguments, defining the model architecture. Instantiating a
    configuration with the defaults will yield a similar configuration to that of the OneFormer
    [shi-labs/oneformer_ade20k_swin_tiny](https://huggingface.co/shi-labs/oneformer_ade20k_swin_tiny) architecture
    trained on [ADE20k-150](https://huggingface.co/datasets/scene_parse_150).

    Configuration objects inherit from [`PretrainedConfig`] and can be used to control the model outputs. Read the
    documentation from [`PretrainedConfig`] for more information.

    Currently, OneFormer supports the [Swin Transformer](swin) and [Dilated Neighborhood Attention Transformer](dinat)
    as backbones.

    Args:
        output_attentions (`bool`, *optional*, defaults to `True`):
            Whether to output attention weights.
        output_hidden_states (`bool`, *optional*, defaults to `True`):
            Whether to output intermediate predictions.
        return_dict (`bool`, *optional*, defaults to `True`):
            Whether to return output as tuples or dataclass objects.
        general_config (`dict`, *optional*)
            Dictionary containing general configuration like backbone_type, loss weights, number of classes, etc.
        backbone_config (`dict`, *optional*, defaults to `swin-tiny-patch4-window7-224`)
            Dictionary containing configuration for the backbone module like patch size, num_heads, etc.
        text_encoder_config (`dict`, *optional*, defaults to a dictionary with the following keys)
            Dictionary containing configuration for the text-mapper module and task encoder like sequence length,
            number of linear layers in MLP, etc.
        decoder_config (`dict`, *optional*, defaults to a dictionary with the following keys)
            Dictionary containing configuration for the text-mapper module and task encoder like sequence length,
            number of linear layers in MLP, etc.

    Raises:
        `ValueError`:
            Raised if the backbone model type selected is not in `["swin", "dinat", "maskformer-swin"]`
    Examples:
    ```python
    >>> from transformers import OneFormerConfig, OneFormerModel

    >>> # Initializing a OneFormer shi-labs/oneformer_ade20k_swin_tiny configuration
    >>> configuration = OneFormerConfig()
    >>> # Initializing a model (with random weights) from the shi-labs/oneformer_ade20k_swin_tiny style configuration
    >>> model = OneFormerModel(configuration)
    >>> # Accessing the model configuration
    >>> configuration = model.config
    ```
    """
    model_type = "oneformer"
    backbones_supported = ["swin", "dinat", "maskformer-swin"]

    def __init__(
        self,
        general_config: Optional[Dict] = None,
        backbone_config: Optional[Dict] = None,
        text_encoder_config: Optional[Dict] = None,
        decoder_config: Optional[Dict] = None,
        **kwargs,
    ):
        cfgs = self._setup_cfg(general_config, backbone_config, text_encoder_config, decoder_config)

        general_config, backbone_config, text_encoder_config, decoder_config = cfgs

        self.general_config = general_config
        self.backbone_config = backbone_config
        self.text_encoder_config = text_encoder_config
        self.decoder_config = decoder_config

        self.hidden_size = self.decoder_config["hidden_dim"]
        self.num_attention_heads = self.decoder_config["num_heads"]
        self.num_hidden_layers = self.decoder_config["decoder_layers"]
        self.init_std = self.general_config["init_std"]
        self.init_xavier_std = self.general_config["init_xavier_std"]

        super().__init__(**kwargs)

    def _setup_cfg(
        self,
        general_config: Optional[Dict] = None,
        backbone_config: Optional[MaskFormerSwinConfig] = None,
        text_encoder_config: Optional[Dict] = None,
        decoder_config: Optional[Dict] = None,
    ) -> Dict[str, any]:
        if general_config is None:
            general_config = {}
            general_config["ignore_value"] = 255
            general_config["num_classes"] = 150
            general_config["num_queries"] = 150
            general_config["no_object_weight"] = 0.1
            general_config["deep_supervision"] = True
            general_config["class_weight"] = 2.0
            general_config["mask_weight"] = 5.0
            general_config["dice_weight"] = 5.0
            general_config["contrastive_weight"] = 0.5
            general_config["contrastive_temperature"] = 0.07
            general_config["train_num_points"] = 12544
            general_config["oversample_ratio"] = 3.0
            general_config["importance_sample_ratio"] = 0.75
            general_config["init_std"] = 0.02
            general_config["init_xavier_std"] = 1.0
            general_config["layer_norm_eps"] = 1e-05
            general_config["is_train"] = False
            general_config["use_auxiliary_loss"] = True
            general_config["output_auxiliary_logits"] = True
            general_config["strides"] = [4, 8, 16, 32]

        if backbone_config is None:
            backbone_config = MaskFormerSwinConfig(
                image_size=224,
                in_channels=3,
                patch_size=4,
                embed_dim=96,
                depths=[2, 2, 6, 2],
                num_heads=[3, 6, 12, 24],
                window_size=7,
                drop_path_rate=0.3,
                out_features=["stage1", "stage2", "stage3", "stage4"],
            )
        else:
            backbone_model_type = (
                backbone_config.pop("model_type") if isinstance(backbone_config, dict) else backbone_config.model_type
            )
            if backbone_model_type not in self.backbones_supported:
                raise ValueError(
                    f"Backbone {backbone_model_type} not supported, please use one of"
                    f" {','.join(self.backbones_supported)}"
                )
            if isinstance(backbone_config, dict):
                config_class = CONFIG_MAPPING[backbone_model_type]
                backbone_config = config_class.from_dict(backbone_config)

        if text_encoder_config is None:
            text_encoder_config = {}
            text_encoder_config["task_seq_len"] = 77
            text_encoder_config["max_seq_len"] = 77
            text_encoder_config["text_encoder_width"] = 256
            text_encoder_config["text_encoder_context_length"] = 77
            text_encoder_config["text_encoder_num_layers"] = 6
            text_encoder_config["text_encoder_vocab_size"] = 49408
            text_encoder_config["text_encoder_proj_layers"] = 2
            text_encoder_config["text_encoder_n_ctx"] = 16

        if decoder_config is None:
            decoder_config = {}
            decoder_config["conv_dim"] = 256
            decoder_config["mask_dim"] = 256
            decoder_config["hidden_dim"] = 256
            decoder_config["encoder_feedforward_dim"] = 1024
            decoder_config["norm"] = "GN"
            decoder_config["encoder_layers"] = 6
            decoder_config["decoder_layers"] = 10
            decoder_config["use_task_norm"] = True
            decoder_config["num_heads"] = 8
            decoder_config["dropout"] = 0.1
            decoder_config["dim_feedforward"] = 2048
            decoder_config["pre_norm"] = False
            decoder_config["enforce_input_proj"] = False
            decoder_config["query_dec_layers"] = 2
            decoder_config["common_stride"] = 4

        return general_config, backbone_config, text_encoder_config, decoder_config

    def to_dict(self) -> Dict[str, any]:
        """
        Serializes this instance to a Python dictionary. Override the default [`~PretrainedConfig.to_dict`]. Returns:
            `Dict[str, any]`: Dictionary of all the attributes that make up this configuration instance,
        """
        output = copy.deepcopy(self.__dict__)
        output["backbone_config"] = self.backbone_config.to_dict()
        output["model_type"] = self.__class__.model_type
        return output
