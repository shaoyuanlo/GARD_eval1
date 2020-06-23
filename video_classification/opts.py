import argparse

def parse_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='/home/sylo/SegNet/flowattack/3D-ResNets-PyTorch/video_classification/ucfTrainTestlist/testlist01_jpg.txt', type=str, help='Input file path')
    parser.add_argument('--video_root', default='/home/sylo/SegNet/flowattack/UCF-101_jpg', type=str, help='Root path of input videos')
    parser.add_argument('--model', required=True, type=str, help='Model file path')
    parser.add_argument('--output', default='output.json', type=str, help='Output file path')
    parser.add_argument('--mode', default='score', type=str, help='Mode (score | feature). score outputs class scores. feature outputs features (after global average pooling).')
    parser.add_argument('--batch_size', default=32, type=int, help='Batch Size')
    parser.add_argument('--n_threads', default=4, type=int, help='Number of threads for multi-thread loading')
    parser.add_argument('--model_name', default='resnext', type=str, help='Currently only support resnet')
    parser.add_argument('--model_depth', default=101, type=int, help='Depth of resnet (10 | 18 | 34 | 50 | 101)')
    parser.add_argument('--resnet_shortcut', default='B', type=str, help='Shortcut type of resnet (A | B)')
    parser.add_argument('--wide_resnet_k', default=2, type=int, help='Wide resnet k')
    parser.add_argument('--resnext_cardinality', default=32, type=int, help='ResNeXt cardinality')
    parser.add_argument('--no_cuda', action='store_true', help='If true, cuda is not used.')
    parser.set_defaults(verbose=False)
    parser.add_argument('--verbose', action='store_true', help='')
    parser.set_defaults(verbose=False)
    parser.add_argument('--exp_name', required=True, type=str, help='name of the experiment, results are stored in results/exp_name.txt')
    parser.add_argument('--save_image', action='store_true', help='')	
    parser.add_argument('--epsilon', default=4, type=int, help='attack epsilon, eps/256')
    parser.add_argument('--attack_iter', default=5, type=int, help='number of attack iterations')
    parser.add_argument('--step_size', default=1.0, type=float, help='learning rate of attack')
    parser.add_argument('--sparsity', default=40, type=int, help='temporal sparsity of video attacks')
    parser.add_argument('--attack_type', required=True, type=str, help='attack type')
    parser.add_argument('--roa_size', default=30, type=int, help='roa size')
    parser.add_argument('--roa_stride', default=1, type=int, help='roa stride')
    parser.add_argument('--framing_width', default=5, type=int, help='framing mask')
    parser.add_argument('--attack_bn', default='clean', type=str, help='which bn to attack')
    parser.add_argument('--inf_bn', default='clean', type=str, help='which bn to inference')	
    parser.add_argument('--num_pixel', default=100, type=int, help='number of attack pixels')	

    args = parser.parse_args()

    return args