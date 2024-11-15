# ANPEP
面向企业采购的自动谈判平台设计与开发
Design and Development of an Automated Negotiation Platform for Enterprise Procurement

## 项目简介
本项目是一个面向企业采购的自动谈判平台，旨在通过自动化谈判技术提高采购效率和降低成本。该平台基于智能谈判算法，能够自动与供应商进行谈判，以达成双方都满意的协议。项目采用Python语言开发，利用了多线程技术来实现并行谈判，以提高谈判效率。

## 功能特点
- 自动化谈判：平台能够自动与供应商进行谈判，以达成双方都满意的协议。
- 多线程谈判：采用多线程技术，实现并行谈判，提高谈判效率。

## 使用方法
1. 安装Python环境
2. 克隆项目到本地
3. 运行main.py文件

## 注意事项
- 请确保Python环境已安装
- 请确保已安装所需的第三方库
- 请确保已正确配置项目中的参数和配置文件

## 项目结构
├── main.py
├── negotiation # 谈判模块
│   ├── __init__.py
│   ├── session.py
│   ├── negotiators.py  # 包含 SmartAspirationNegotiator 类
│   ├── utils.py
├── my_threading # 多线程模块
│   ├── __init__.py
│   ├── thread_tasks.py
└── requirements.txt

- README.md：项目说明文档
- AIvsAIver.py：前期agent对agent单独谈判实现，不带UI
- singleyneg.py：单线程单独谈判实现，带UI
- multiplyneg.py: 多线程谈判单独实现，带UI，最终版本finalver
- software.puml: 项目架构图

## 备注
本项目由于工期问题和小组成员合作经验不足，代码较为混乱，仍然需要进一步优化和重构。