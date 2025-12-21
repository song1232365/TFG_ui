from modelscope import snapshot_download
import os
# 使用相对路径，支持本地部署
current_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = snapshot_download('iic/CosyVoice2-0.5B', local_dir=os.path.join(current_dir, 'pretrained_models/CosyVoice2-0.5B'))