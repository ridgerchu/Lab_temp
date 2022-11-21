cd /home/ridger/%E6%96%87%E6%A1%A3/ImageNet_Test
conda activate snn
python -m torch.distributed.launch --nproc_per_node=2 -m ImageNet_VGG --T 1 --model spiking_vgg11_bn --data-path /home/ridger/datasets/tiny-imagenet-200 --batch-size 16 --lr 0.01 --lr-scheduler cosa --epochs 90 --opt adamw