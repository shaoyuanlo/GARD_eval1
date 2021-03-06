import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import math
from functools import partial

__all__ = ['ResNeXt', 'resnet50', 'resnet101']


def conv3x3x3(in_planes, out_planes, stride=1):
    # 3x3x3 convolution with padding
    return nn.Conv3d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


def downsample_basic_block(x, planes, stride):
    out = F.avg_pool3d(x, kernel_size=1, stride=stride)
    zero_pads = torch.Tensor(out.size(0), planes - out.size(1), out.size(2), out.size(3), out.size(4)).zero_()
    if isinstance(out.data, torch.cuda.FloatTensor):
        zero_pads = zero_pads.cuda()

    out = Variable(torch.cat([out.data, zero_pads], dim=1))

    return out


class OUCD_3(nn.Module):
    
    def __init__(self, inCh):
        super(OUCD_3, self).__init__()

        outCh = 8

        # beginning conv		
        self.conv_1x1a = nn.Conv3d(inCh, outCh, 1, bias=False)

        # KNet        
        self.enc_k1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_k2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)
        self.enc_k3 = nn.Conv3d(outCh*4, outCh*8, 3, padding=1, bias=False)
							 
        self.dec_k1 = nn.Conv3d(outCh*8, outCh*4, 3, padding=1, bias=False)
        self.dec_k2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_k3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)
							 
        # UNet               
        self.enc_u1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_u2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)
        self.enc_u3 = nn.Conv3d(outCh*4, outCh*8, 3, padding=1, bias=False)
							 
        self.dec_u1 = nn.Conv3d(outCh*8, outCh*4, 3, padding=1, bias=False)
        self.dec_u2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_u3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)	

        # Inter
        self.inter_k1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)
        self.inter_k2 = nn.Conv3d(outCh*4, outCh*4, 1, bias=False)

        self.inter_u1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)
        self.inter_u2 = nn.Conv3d(outCh*4, outCh*4, 1, bias=False)		

        # final conv
        self.conv_1x1b = nn.Conv3d(outCh, outCh, 1, bias=False)		
        self.conv_1x1c = nn.Conv3d(outCh, inCh, 1, bias=False)		
    
    def forward(self, x):

        # beginning conv
        out_begin = self.conv_1x1a(x)	
        out_begin = F.relu_(out_begin)		

        # KNet
        out = self.enc_k1(out_begin)		
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a1 = self.inter_k1(out)
        out_a1 = F.relu_(out_a1)  # size=2, channel=2		
        out = self.enc_k2(out)		
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a2 = self.inter_k2(out)
        out_a2 = F.relu_(out_a2)  # size=4, channel=4		
        out = self.enc_k3(out)		
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)  # size=8, channel=8		

        out = self.dec_k1(out)		
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=4, channel=4
        out = out + out_a2		
        out = self.dec_k2(out)		
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=2, channel=2		
        out = out + out_a1		
        out = self.dec_k3(out)		
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=1, channel=1		

        # UNet
        out_u = self.enc_u1(out_begin)		
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)	
        out_u_a1 = self.inter_u1(out_u)
        out_u_a1 = F.relu_(out_u_a1)  # size=1/2, channel=2
        out_u = self.enc_u2(out_u)	
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)
        out_u_a2 = self.inter_u2(out_u)
        out_u_a2 = F.relu_(out_u_a2)  # size=1/4, channel=4
        out_u = self.enc_u3(out_u)
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)  # size=1/8, channel=8	
		
        out_u = self.dec_u1(out_u)
        out_u = F.interpolate(out_u, size=(20,7,7), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1/4, channel=4		
        out_u = out_u + out_u_a2
        out_u = self.dec_u2(out_u)
        out_u = F.interpolate(out_u, scale_factor=(1,2,2), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1/2, channel=2
        out_u = out_u + out_u_a1
        out_u = self.dec_u3(out_u)
        out_u = F.interpolate(out_u, scale_factor=(1,2,2), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1, channel=1

        # final conv
        out_u = self.conv_1x1b(out_u)
        out_u = F.relu_(out_u)		
        out = out + out_u		
        out = self.conv_1x1c(out)
        
        return F.relu_(out)


class OUCD_2(nn.Module):
    
    def __init__(self, inCh):
        super(OUCD_2, self).__init__()

        outCh = 8

        # beginning conv		
        self.conv_1x1a = nn.Conv3d(inCh, outCh, 1, bias=False)

        # KNet        
        self.enc_k1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_k2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)
        self.enc_k3 = nn.Conv3d(outCh*4, outCh*8, 3, padding=1, bias=False)

        self.dec_k1 = nn.Conv3d(outCh*8, outCh*4, 3, padding=1, bias=False)
        self.dec_k2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_k3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)

        # UNet
        self.enc_u1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_u2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)

        self.dec_u2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_u3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)

        # Inter
        self.inter_k1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)
        self.inter_k2 = nn.Conv3d(outCh*4, outCh*4, 1, bias=False)

        self.inter_u1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)		

        # final conv
        self.conv_1x1b = nn.Conv3d(outCh, outCh, 1, bias=False)		
        self.conv_1x1c = nn.Conv3d(outCh, inCh, 1, bias=False)		
    
    def forward(self, x):

        # beginning conv
        out_begin = self.conv_1x1a(x)
        out_begin = F.relu_(out_begin)		

        # KNet
        out = self.enc_k1(out_begin)
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a1 = self.inter_k1(out)
        out_a1 = F.relu_(out_a1)  # size=2, channel=2		
        out = self.enc_k2(out)		
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a2 = self.inter_k2(out)
        out_a2 = F.relu_(out_a2)  # size=4, channel=4		
        out = self.enc_k3(out)	
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)  # size=8, channel=8		

        out = self.dec_k1(out)
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=4, channel=4
        out = out + out_a2		
        out = self.dec_k2(out)	
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=2, channel=2		
        out = out + out_a1		
        out = self.dec_k3(out)	
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=1, channel=1	

        # UNet
        out_u = self.enc_u1(out_begin)	
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)
        out_u_a1 = self.inter_u1(out_u)
        out_u_a1 = F.relu_(out_u_a1)  # size=1/2, channel=2
        out_u = self.enc_u2(out_u)	
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)  # size=1/4, channel=4
	
        out_u = self.dec_u2(out_u)
        out_u = F.interpolate(out_u, size=(10,7,7), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1/2, channel=2
        out_u = out_u + out_u_a1
        out_u = self.dec_u3(out_u)	
        out_u = F.interpolate(out_u, scale_factor=(1,2,2), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1, channel=1

        # final conv
        out_u = self.conv_1x1b(out_u)
        out_u = F.relu_(out_u)		
        out = out + out_u		
        out = self.conv_1x1c(out)		
        
        return F.relu_(out)


class OUCD_1(nn.Module):
    
    def __init__(self, inCh):
        super(OUCD_1, self).__init__()

        outCh = 8

        # beginning conv		
        self.conv_1x1a = nn.Conv3d(inCh, outCh, 1, bias=False)

        # KNet        
        self.enc_k1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_k2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)
        self.enc_k3 = nn.Conv3d(outCh*4, outCh*8, 3, padding=1, bias=False)

        self.dec_k1 = nn.Conv3d(outCh*8, outCh*4, 3, padding=1, bias=False)
        self.dec_k2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_k3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)

        # UNet
        self.enc_u1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)

        self.dec_u3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)

        # Inter
        self.inter_k1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)
        self.inter_k2 = nn.Conv3d(outCh*4, outCh*4, 1, bias=False)		

        # final conv
        self.conv_1x1b = nn.Conv3d(outCh, outCh, 1, bias=False)		
        self.conv_1x1c = nn.Conv3d(outCh, inCh, 1, bias=False)		
    
    def forward(self, x):

        # beginning conv
        out_begin = self.conv_1x1a(x)
        out_begin = F.relu_(out_begin)		

        # KNet
        out = self.enc_k1(out_begin)	
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a1 = self.inter_k1(out)
        out_a1 = F.relu_(out_a1)  # size=2, channel=2		
        out = self.enc_k2(out)	
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a2 = self.inter_k2(out)
        out_a2 = F.relu_(out_a2)  # size=4, channel=4		
        out = self.enc_k3(out)	
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)  # size=8, channel=8		

        out = self.dec_k1(out)
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=4, channel=4
        out = out + out_a2		
        out = self.dec_k2(out)	
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=2, channel=2		
        out = out + out_a1		
        out = self.dec_k3(out)	
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=1, channel=1	

        # UNet
        out_u = self.enc_u1(out_begin)		
        out_u = F.max_pool3d(out_u, (1,2,2), stride=(1,2,2))
        out_u = F.relu_(out_u)  # size=1/2, channel=2
        out_u = out_u
	
        out_u = self.dec_u3(out_u)		
        out_u = F.interpolate(out_u, size=(5,7,7), mode='trilinear')
        out_u = F.relu_(out_u)  # size=1, channel=1

        # final conv
        out_u = self.conv_1x1b(out_u)
        out_u = F.relu_(out_u)		
        out = out + out_u		
        out = self.conv_1x1c(out)		
        
        return F.relu_(out)
		

class OUCD_0(nn.Module):
    
    def __init__(self, inCh):
        super(OUCD_0, self).__init__()

        outCh = 8

        # beginning conv		
        self.conv_1x1a = nn.Conv3d(inCh, outCh, 1, bias=False)

        # KNet        
        self.enc_k1 = nn.Conv3d(outCh, outCh*2, 3, padding=1, bias=False)
        self.enc_k2 = nn.Conv3d(outCh*2, outCh*4, 3, padding=1, bias=False)
        self.enc_k3 = nn.Conv3d(outCh*4, outCh*8, 3, padding=1, bias=False)

        self.dec_k1 = nn.Conv3d(outCh*8, outCh*4, 3, padding=1, bias=False)
        self.dec_k2 = nn.Conv3d(outCh*4, outCh*2, 3, padding=1, bias=False)
        self.dec_k3 = nn.Conv3d(outCh*2, outCh, 3, padding=1, bias=False)

        # Inter
        self.inter_k1 = nn.Conv3d(outCh*2, outCh*2, 1, bias=False)
        self.inter_k2 = nn.Conv3d(outCh*4, outCh*4, 1, bias=False)

        # final conv
        self.conv_1x1c = nn.Conv3d(outCh, inCh, 1, bias=False)		
    
    def forward(self, x):

        # beginning conv
        out_begin = self.conv_1x1a(x)
        out_begin = F.relu_(out_begin)		

        # KNet
        out = self.enc_k1(out_begin)		
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a1 = self.inter_k1(out)
        out_a1 = F.relu_(out_a1)  # size=2, channel=2		
        out = self.enc_k2(out)	
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)
        out_a2 = self.inter_k2(out)
        out_a2 = F.relu_(out_a2)  # size=4, channel=4		
        out = self.enc_k3(out)
        out = F.interpolate(out, scale_factor=(1,2,2), mode='trilinear')
        out = F.relu_(out)  # size=8, channel=8		

        out = self.dec_k1(out)	
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=4, channel=4
        out = out + out_a2		
        out = self.dec_k2(out)		
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=2, channel=2		
        out = out + out_a1		
        out = self.dec_k3(out)		
        out = F.max_pool3d(out, (1,2,2), stride=(1,2,2))
        out = F.relu_(out)  # size=1, channel=1	

        # final conv		
        out = self.conv_1x1c(out)	
        
        return F.relu_(out)


class ResNeXtBottleneck(nn.Module):
    expansion = 2

    def __init__(self, inplanes, planes, cardinality, stride=1, downsample=None):
        super(ResNeXtBottleneck, self).__init__()
        mid_planes = cardinality * int(planes / 32)
        self.conv1 = nn.Conv3d(inplanes, mid_planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm3d(mid_planes)
        self.conv2 = nn.Conv3d(mid_planes, mid_planes, kernel_size=3, stride=stride, padding=1, groups=cardinality, bias=False)
        self.bn2 = nn.BatchNorm3d(mid_planes)
        self.conv3 = nn.Conv3d(mid_planes, planes * self.expansion, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm3d(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNeXt(nn.Module):

    def __init__(self, block, layers, sample_size, sample_duration, shortcut_type='B', cardinality=32, num_classes=400):
        self.inplanes = 64
        super(ResNeXt, self).__init__()
		
        self.conv1 = nn.Conv3d(3, 64, kernel_size=7, stride=(1, 2, 2), padding=(3, 3, 3), bias=False)
        self.bn1 = nn.BatchNorm3d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool3d(kernel_size=(3, 3, 3), stride=2, padding=1)
		
        self.layer1 = self._make_layer(block, 128, layers[0], shortcut_type, cardinality)
        self.layer2 = self._make_layer(block, 256, layers[1], shortcut_type, cardinality, stride=2)
        self.layer3 = self._make_layer(block, 512, layers[2], shortcut_type, cardinality, stride=2)
        self.layer4 = self._make_layer(block, 1024, layers[3], shortcut_type, cardinality, stride=2)
		
        last_duration = int(math.ceil(sample_duration / 16))
        last_size = int(math.ceil(sample_size / 32))
        self.avgpool = nn.AvgPool3d((last_duration, last_size, last_size), stride=1)
        self.fc = nn.Linear(cardinality * 32 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv3d):
                m.weight = nn.init.kaiming_normal(m.weight, mode='fan_out')
            elif isinstance(m, nn.BatchNorm3d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
				
        #self.denoise_res2 = OUCD_3(64)
        #self.denoise_res3 = OUCD_2(128)
        self.denoise_res4 = OUCD_1(1024)
        #self.denoise_res5 = OUCD_0(512)
		
        #self.conv1x1_res2 = nn.Conv3d(64, 64, 1, bias=False)
        #self.conv1x1_res3 = nn.Conv3d(128, 128, 1, bias=False)
        self.conv1x1_res4 = nn.Conv3d(1024, 1024, 1, bias=False)
        #self.conv1x1_res5 = nn.Conv3d(512, 512, 1, bias=False)		

    def _make_layer(self, block, planes, blocks, shortcut_type, cardinality, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            if shortcut_type == 'A':
                downsample = partial(downsample_basic_block, planes=planes*block.expansion, stride=stride)
            else:
                downsample = nn.Sequential(
                    nn.Conv3d(self.inplanes, planes * block.expansion, kernel_size=1, stride=stride, bias=False),
                    nn.BatchNorm3d(planes * block.expansion))

        layers = []
        layers.append(block(self.inplanes, planes, cardinality, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes, cardinality))

        return nn.Sequential(*layers)

    def forward(self, x):
	
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)		
        out = self.maxpool(out)

        out = self.layer1(out)
        #out_res2 = self.layer1(out)
        #out_de_res2 = self.denoise_res2(out_res2)
        #x_f = F.relu(out_res2 + self.conv1x1_res2(out_de_res2))		
		
        out = self.layer2(out)
        #out_res3 = self.layer2(x_f)
        #out_de_res3 = self.denoise_res3(out_res3)
        #out = F.relu(out_res3 + self.conv1x1_res3(out_de_res3))		
		
        #out = self.layer3(out)
        out_res4 = self.layer3(out)
        out_de_res4 = self.denoise_res4(out_res4)
        out = F.relu(out_res4 + self.conv1x1_res4(out_de_res4))		
		
        out = self.layer4(out)
        #out_res5 = self.layer4(out)
        #out_de_res5 = self.denoise_res5(out_res5)
        #out = F.relu(out_res5 + self.conv1x1_res5(out_de_res5))	

        out = self.avgpool(out)
        out = out.view(out.size(0), -1)
        out = self.fc(out)

        return out


def get_fine_tuning_parameters(model, ft_begin_index):
    if ft_begin_index == 0:
        return model.parameters()

    ft_module_names = []
    for i in range(ft_begin_index, 5):
        ft_module_names.append('layer{}'.format(i))
    ft_module_names.append('fc')

    parameters = []
    for k, v in model.named_parameters():
        for ft_module in ft_module_names:
            if ft_module in k:
                parameters.append({'params': v})
                break
        else:
            parameters.append({'params': v, 'lr': 0.0})

    return parameters


def resnet50(**kwargs):
    """Constructs a ResNet-50 model.
    """
    model = ResNeXt(ResNeXtBottleneck, [3, 4, 6, 3], **kwargs)
    return model


def resnet101(**kwargs):
    """Constructs a ResNet-101 model.
    """
    model = ResNeXt(ResNeXtBottleneck, [3, 4, 23, 3], **kwargs)
    return model


def resnet152(**kwargs):
    """Constructs a ResNet-101 model.
    """
    model = ResNeXt(ResNeXtBottleneck, [3, 8, 36, 3], **kwargs)
    return model
