# Parkive

Parkive 是一个用于管理知识库的命令行工具。它的目标是以非侵入性的方式辅助用户管理以 Markdown 形式存在的笔记、日记。Parkive 是非侵入性的，它的所有配置文件和标记全部存储在`.parkive`目录下，不会在 Markdown 文件中留下任何标记。用户可以直接使用 Typora 等软件阅读和编辑知识库里的文件。

Parkive 假设用户的知识库是这样的：所有的笔记文件为文本文件（例如 Markdown）；图片以外部链接或本地路径的形式，存放在 Markdown 的图片标签 `![alt](url)` 或 HTML 的图片标签 `<img src="" >` 中；使用 git 将知识库与远程仓库同步。

Parkive 假设用户使用 git 进行备份， 提供了两种备份方式 `parkive git sync` 和 `parkive git snapshot`。前者将工作区的修改覆盖到上一次提交，不会新增提交记录，可以理解为 “将本地的修改同步到远程仓库”；后者则将当前的状态保存为一个快照提交，再创建一个新的空白提交，供下次进行`sync`。

Markdown 或 HTML 形式的笔记、日记通常会将图片存储在图床服务器上，通过链接访问。如果有多个图床服务器的实例（例如，部署在多个服务器上的反向代理服务），就需要切换理图片 URL 的前缀。使用`parkive source` 可以很方便地在不同来源间切换。

在 Parkive 中，来源 source 指的是由名称和 URL 组成的二元组。例如 `aliyun : https://bucket-name.oss-cn-shanghai.aliyuncs.com`。将 source 添加到 Parkive 后，就可以很方便地使用名称对其进行管理。用户可以使用 Parkive 扫描知识库中的图片来源、查看不同来源的图片数量，以及将一种来源的图片切换到另一种来源。

## 安装

手动构建：

~~~bash
uv sync
uv build
cd dist
uv tool install parkive-*.whl
~~~

或者直接从 releases 页面下载 `.whl` 文件进行安装。

~~~bash
# download the latest wheel from the releases page and install it using pip or uv.
uv tool install parkive-*.whl
~~~

## 使用

命令概览：

~~~bash
parkive init	# 初始化配置文件目录

parkive git sync	# 使用 git 同步到远程仓库, 覆盖上一次提交。
parkive git snapshot # 创建快照提交，便于后续回滚。

parkive source add  # 添加新的 source
parkive source remove   # 删除 source
parkive source change   # 将文件中的图片 URL 从一个 source 切换到另一个 source
parkive source inspect
parkive source status

parkive tool wc # 常用功能: 字数统计
~~~

工作流程：

~~~bash
$ parkive init	# 初始化仓库
initialized parkive at [PATH]

# 修改笔记
# 写日记
# ...

$ parkive git sync	# 同步到远程仓库
✓ git rev-parse HEAD
✓ git add .
✓ git commit --amend --no-edit
✓ git push origin main --force
sync finished.

## 为了防止某次 sync 失误覆盖掉之前的内容，可以使用快照功能
#parkive git snapshot

# 添加几个可以被 Parkive 所管理的图片来源
$ parkive source add localhost http://127.0.0.1:1234
$ parkive source add server http://xxx.xxx.xxx.xxx:1234

# 查看当前知识库的图片来源
$ parkive source status
Known sources:
localhost	http://127.0.0.1:1234		390
server		http://xxx.xxx.xxx.xxx:1234	91

Unknown sources:
(relative-or-invalid-url)       6
https://picasso-static.xiaohongshu.com  2
https://api2.mubu.com   1

# 切换图片的来源
$ parkive source change localhost server
changed source 'localhost' => 'server', replaced 91 urls in 4 files.
~~~

## 配置文件

用户配置文件在`.parkive`目录下的`config.toml`文件中，示例如下：

~~~toml
# config.toml 示例
[scope]
scan_glob = ["*.md", "**/*.md"]		# Parkive 管理的文件范围，语法为 Glob 模式 
skip_dirs = [".git", ".parkive"]	# 需要忽略的文件夹
~~~

