"""DocumentRegion 数据模型

VLMExtractor（Task 3）提取文档区域后，用此 dataclass 表示；
RegionChunker（Task 4）根据 type 字段进行类型感知的分块。

设计决策：
- 选择 dataclass 而非 Pydantic BaseModel：此模型是内部 DTO，不涉及
  JSON 反序列化或 API 边界校验，dataclass 更轻量且无额外依赖。
- bbox 使用 tuple 而非 list：区域坐标在创建后不应被修改，
  tuple 的不可变性提供了天然的防篡改保护。
"""

from dataclasses import dataclass

# 为什么用 frozenset 而非 list：集合查找是 O(1)，且 frozenset 不可变，
# 避免运行时被意外修改导致校验逻辑失效。
VALID_REGION_TYPES = frozenset({"text", "table", "figure", "equation", "header"})


@dataclass
class DocumentRegion:
    """文档区域——VLM 提取出的最小语义单元。

    每个实例代表文档中的一个可识别区域（文字段落、表格、图片等），
    携带类型信息、文本内容、可选的边界框和置信度。
    """

    # 为什么用 str 而非枚举：下游序列化（存入数据库、写入 JSON）时
    # 字符串比枚举成员更直接，省去了 .value 转换；同时上游 VLM 输出
    # 本身就是字符串，避免来回转换的开销。
    type: str

    # 为什么 content 始终存字符串而非按类型分字段（如 table_data / image_caption）：
    # 统一的 content 字段让 RegionChunker 的下游逻辑只需读 content，
    # 无需按类型做 switch/case，减少了分支复杂度。
    content: str

    # 为什么用 tuple | None 而非 dataclass：坐标四元组 (x0, y0, x1, y1)
    # 没有命名字段的需求，tuple 足够且占用更少内存；
    # None 表示该区域无法确定位置（例如纯文本段落）。
    bbox: tuple | None

    # 为什么 confidence 用 float 而非 Decimal：置信度来自模型推理，
    # 本身是 float32 精度，Decimal 会引入不必要的转换开销且无精度收益。
    confidence: float

    # 为什么默认值是 "" 而非 None：下游拼接 base64 时，
    # 空字符串可以直接用于 f-string 或 join，无需先做 None 检查，
    # 减少了调用方的条件分支。
    image_base64: str = ""

    def __post_init__(self) -> None:
        """在构造完成后立即执行校验和规范化。

        为什么放在 __post_init__ 而非 __init__：
        dataclass 自动生成 __init__，我们无法（也不应该）覆盖它；
        __post_init__ 是 dataclass 提供的标准钩子，保证在 __init__ 末尾
        自动调用，时序确定且不会被子类遗漏。
        """
        # 为什么在构造时校验类型而非在下游使用时校验：
        # 尽早失败（fail-fast）原则——构造时立即抛出 ValueError
        # 比在 RegionChunker 处理到一半才发现类型非法更容易定位问题，
        # 错误栈会直接指向创建 DocumentRegion 的那一行。
        if self.type not in VALID_REGION_TYPES:
            raise ValueError(
                f"不支持的区域类型: '{self.type}'，"
                f"允许的类型: {', '.join(sorted(VALID_REGION_TYPES))}"
            )

        # 为什么非 figure 类型清空 image_base64：
        # 文本/表格/公式/标题区域理论上不应该携带图片数据，
        # 但上游 VLM 可能误填此字段；强制清空可以：
        # 1. 避免序列化时意外膨胀（一个 base64 字符串可达数 MB）；
        # 2. 让下游代码可以安全假设"只有 figure 才有图片"，无需额外检查。
        if self.type != "figure":
            self.image_base64 = ""
