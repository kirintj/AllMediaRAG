# pgvector Windows 安装指南 (PostgreSQL 16)

## 方法 1: 使用 Stack Builder（推荐）

1. 打开 **Stack Builder**（在开始菜单中找到 PostgreSQL 16）
2. 选择你的 PostgreSQL 16 实例
3. 在分类中找到 **Spatial Extensions**
4. 选择 **pgvector** 并安装
5. 完成后重启 PostgreSQL 服务

## 方法 2: 手动安装预编译版本

### 步骤 1: 下载 pgvector

访问 GitHub Releases 页面：
https://github.com/pgvector/pgvector/releases

下载适用于 Windows x64 的最新版本，例如：
`pgvector-0.8.0-windows-x64.zip`

### 步骤 2: 解压文件

将下载的 zip 文件解压，你会看到以下文件：
```
vector--1.0.sql
vector--1.0--1.1.sql
...
vector.control
vector.dll
```

### 步骤 3: 复制文件到 PostgreSQL 目录

将文件复制到 PostgreSQL 安装目录：

```bash
# 复制 DLL 到 lib 目录
copy vector.dll "D:\Develop\PostgreSQL\16\lib\"

# 复制 SQL 和 control 文件到 extension 目录
copy vector*.sql "D:\Develop\PostgreSQL\16\share\extension\"
copy vector.control "D:\Develop\PostgreSQL\16\share\extension\"
```

### 步骤 4: 重启 PostgreSQL 服务

打开服务管理器（services.msc），找到 PostgreSQL 服务并重启。

## 方法 3: 使用 vcpkg 编译

```bash
# 安装 vcpkg（如果还没有）
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
bootstrap-vcpkg.bat

# 安装 pgvector
vcpkg install pgvector

# 将编译好的文件复制到 PostgreSQL 目录
```

## 方法 4: 使用 Chocolatey

```bash
choco install pgvector
```

## 验证安装

安装完成后，运行以下 SQL 命令验证：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

如果看到 vector 扩展的信息，说明安装成功。

## 常见问题

### 1. 找不到 Stack Builder

Stack Builder 通常在以下位置：
- 开始菜单 → PostgreSQL 16 → Stack Builder
- 或运行：`"D:\Develop\PostgreSQL\16\bin\StackBuilder.exe"`

### 2. DLL 加载失败

确保：
- vector.dll 版本与 PostgreSQL 版本匹配（都是 16.x 64位）
- DLL 已复制到正确的 lib 目录
- PostgreSQL 服务已重启

### 3. 扩展创建失败

检查：
- SQL 文件和 control 文件是否在 `share/extension` 目录
- 文件权限是否正确
- PostgreSQL 日志中的详细错误信息

## 官方文档

- pgvector GitHub: https://github.com/pgvector/pgvector
- Windows 安装说明: https://github.com/pgvector/pgvector#windows
- PostgreSQL 扩展文档: https://www.postgresql.org/docs/current/extend-extensions.html
