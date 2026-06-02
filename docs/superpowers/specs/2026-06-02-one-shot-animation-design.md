# 一镜到底动画实现设计文档

> **日期:** 2026-06-02
> **状态:** 草案

---

## 1. 项目概述

### 1.1 项目目标

在现有 HarmonyOS/ArkUI 项目中实现"一镜到底"（连续过渡）动画效果，具体为：
- **场景：** 列表到详情的展开动画
- **元素：** 卡片/容器组件
- **方案：** 使用 geometryTransition 实现跨页面共享元素转场

### 1.2 预期效果

1. 用户点击列表中的卡片
2. 卡片平滑放大过渡到详情页面
3. 详情页的内容连续展示，无视觉割裂
4. 返回时反向动画平滑收缩

---

## 2. 技术方案

### 2.1 核心技术：geometryTransition

**原理：** 在源页面和目标页面上绑定相同的 geometryTransition ID，通过 animateTo 闭包触发页面导航，系统自动在源组件和目标组件之间插值位置、尺寸和透明度。

**优点：**
- ✅ 系统级支持，动画精度高
- ✅ 实现复杂度中等
- ✅ 适合跨页面元素连续过渡
- ✅ 自动处理位置和大小的插值

**局限：**
- ⚠️ 仅限于特定框架（ArkUI）
- ⚠️ 需要管理 ID 生命周期

### 2.2 实现架构

```
┌─────────────────────────────────────────────────────────┐
│                      架构总览                           │
├─────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐     ┌──────────────┐     ┌──────────┐   │
│  │ 列表页   │────▶│  animateTo   │────▶│ 详情页   │   │
│  │ (源端)   │     │  导航触发器   │     │ (目标端) │   │
│  └──────────┘     └──────────────┘     └──────────┘   │
│        │                                      ▲        │
│        └──────────── geometryTransition ──────┘        │
│                      (共享 ID)                        │
│                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 详细设计

### 3.1 核心组件

#### 3.1.1 共享 ID 管理器

**文件：** `utils/CommonConstants.ets`

```typescript
export class AnimationConstants {
  // 共享元素 ID
  public static readonly CARD_GEOMETRY_ID: string = 'app_card_geometry';

  // 动画参数
  public static readonly ENTER_SPRING: SpringOptions = {
    velocity: 0,
    mass: 1,
    stiffness: 273,
    damping: 33
  };

  public static readonly EXIT_SPRING: SpringOptions = {
    velocity: 0,
    mass: 1,
    stiffness: 363,
    damping: 38
  };

  // 动画时长
  public static readonly TRANSITION_DURATION: number = 100;
}
```

#### 3.1.2 列表项组件（源端）

**文件：** `components/CardItem.ets`

```typescript
@Component
struct CardItem {
  @State cardData: CardData;
  onItemClick: (data: CardData) => void;

  build() {
    Column() {
      // 卡片内容
    }
    .geometryTransition(AnimationConstants.CARD_GEOMETRY_ID, {
      follow: true  // 关键：源端设置 follow: true
    })
    .transition(TransitionEffect.OPACITY)
    .onClick(() => {
      this.onItemClick(this.cardData);
    })
  }
}
```

**关键点：**
- `.geometryTransition(ID, { follow: true })` 设置为跟随方
- `.transition(TransitionEffect.OPACITY)` 处理透明度渐变

#### 3.1.3 列表页面

**文件：** `pages/ListPage.ets`

```typescript
@Entry
@Component
struct ListPage {
  @State cardList: CardData[] = [];

  handleCardClick(data: CardData) {
    const uiContext = AppStorage.get<UIContext>(StorageKey.UI_CONTEXT);

    // 关键：在 animateTo 闭包内触发导航
    uiContext?.animateTo({
      curve: curves.interpolatingSpring(
        AnimationConstants.ENTER_SPRING.velocity,
        AnimationConstants.ENTER_SPRING.mass,
        AnimationConstants.ENTER_SPRING.stiffness,
        AnimationConstants.ENTER_SPRING.damping
      )
    }, () => {
      currentPageContext?.openPage({
        routerName: PageEnum.DETAIL_PAGE,
        param: { cardData: data }
      }, false);
    });
  }

  build() {
    List() {
      ForEach(this.cardList, (data: CardData) => {
        ListItem() {
          CardItem({ cardData: data, onItemClick: this.handleCardClick })
        }
      })
    }
  }
}
```

#### 3.1.4 详情页面（目标端）

**文件：** `pages/DetailPage.ets`

```typescript
@Entry
@Component
struct DetailPage {
  @State isTransitionActive: boolean = true;
  @State isPopTransition: boolean = false;
  @State cardData: CardData;

  build() {
    NavDestination() {
      Column() {
        // 详情页内容
      }
      .geometryTransition(
        this.isTransitionActive
          ? AnimationConstants.CARD_GEOMETRY_ID
          : ''
      )
      .transition(
        this.isTransitionActive
          ? (this.isPopTransition
            ? TransitionEffect.OPACITY
            : TransitionEffect.OPACITY.animation({
                duration: AnimationConstants.TRANSITION_DURATION
              }))
          : undefined,
        // 转场完成回调
        (transitionIn: boolean) => {
          if (transitionIn) {
            this.isTransitionActive = false;
          }
        }
      )
    }
  }

  // 返回动画
  popAction() {
    this.isPopTransition = true;
    this.isTransitionActive = true;

    this.getUIContext().animateTo({
      curve: curves.interpolatingSpring(
        AnimationConstants.EXIT_SPRING.velocity,
        AnimationConstants.EXIT_SPRING.mass,
        AnimationConstants.EXIT_SPRING.stiffness,
        AnimationConstants.EXIT_SPRING.damping
      )
    }, () => {
      // 触发返回
    });
  }
}
```

**关键点：**
- 进入动画完成后清除 ID（`isTransitionActive = false`）
- 返回时重新激活 ID（`isTransitionActive = true`）
- 使用不同的弹簧参数区分进入和返回动画

---

## 4. 子代理并行开发方案

### 4.1 任务分解

基于子代理并行开发方法，将实现分解为以下独立任务：

| 任务 | 描述 | 依赖 |
|------|------|------|
| **Task 1** | 创建共享常量和动画参数 | 无 |
| **Task 2** | 实现列表项组件（源端） | Task 1 |
| **Task 3** | 实现列表页面 | Task 2 |
| **Task 4** | 实现详情页面（目标端） | Task 1 |
| **Task 5** | 集成测试和优化 | Task 3, Task 4 |

### 4.2 子代理调度策略

```
Phase 1: 并行开发基础设施
├── Subagent 1: 创建 AnimationConstants
└── Subagent 2: 创建通用组件基础

Phase 2: 并行开发页面组件
├── Subagent 3: 实现列表项组件
├── Subagent 4: 实现列表页面
└── Subagent 5: 实现详情页面

Phase 3: 集成和验证
└── Subagent 6: 集成测试
```

### 4.3 子代理任务规范

每个子代理应遵循以下规范：

1. **TDD 原则：** 先写测试，再写实现
2. **代码审查：** 实现完成后进行规格合规审查和代码质量审查
3. **文档更新：** 更新相关文档

---

## 5. 实施计划

### 5.1 阶段一：基础设施（预计 30 分钟）

- [ ] 创建 AnimationConstants 常量定义
- [ ] 设置测试环境
- [ ] 编写单元测试基础框架

### 5.2 阶段二：组件开发（预计 60 分钟）

- [ ] 实现列表项组件（CardItem.ets）
- [ ] 实现列表页面（ListPage.ets）
- [ ] 实现详情页面（DetailPage.ets）
- [ ] 编写组件单元测试

### 5.3 阶段三：集成测试（预计 30 分钟）

- [ ] 测试列表到详情的导航
- [ ] 测试详情页返回动画
- [ ] 测试 ID 生命周期管理
- [ ] 性能优化和调优

### 5.4 阶段四：优化和验证（预计 20 分钟）

- [ ] 弹簧参数调优
- [ ] 无障碍支持
- [ ] 文档完善

---

## 6. 关键注意事项

### 6.1 ID 生命周期管理

```
页面进入动画开始    转场完成回调触发    页面返回动画开始    返回完成
      │                  │                  │              │
      ▼                  ▼                  ▼              ▼
 isTransitionActive  isTransitionActive  isTransitionActive   (页面销毁)
 = true             = false            = true
 ID = 'xxx'         ID = ''            ID = 'xxx'
```

**为什么要清空 ID：**
- 防止后续布局更新意外触发动画
- 避免视觉异常

### 6.2 animateTo 包裹导航

**正确：**
```typescript
uiContext.animateTo({ curve: ... }, () => {
  navPathStack.pushPath({ name: 'DetailPage', param: { ... } });
});
```

**错误：**
```typescript
navPathStack.pushPath({ name: 'DetailPage', param: { ... } });
// 不会触发 geometryTransition 动画
```

### 6.3 弹簧参数调优建议

| 场景 | velocity | mass | stiffness | damping | 特点 |
|------|----------|------|-----------|---------|------|
| 前导航（进入详情） | 0 | 1 | 273 | 33 | 较快收敛 |
| 返回（返回列表） | 0 | 1 | 363 | 38 | 刚度更高，更果断 |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 列表卡片点击后平滑过渡到详情页
- [ ] 详情页元素位置和大小正确
- [ ] 返回时动画平滑收缩
- [ ] ID 生命周期管理正确

### 7.2 性能验收

- [ ] 动画流畅（60fps）
- [ ] 无卡顿或闪烁
- [ ] 内存使用合理

### 7.3 质量验收

- [ ] 单元测试覆盖率 > 80%
- [ ] 代码通过 ESLint 检查
- [ ] 无已知 bug

---

## 8. 参考资料

- HarmonyOS ArkUI 动画文档
- geometryTransition API 参考
- curves.interpolatingSpring 参数说明

---

## 9. 附录

### 9.1 常用弹簧参数

```typescript
// 常用的弹簧曲线参数组合
const SPRING_PRESETS = {
  // 轻快动画
  LIGHT: { velocity: 0, mass: 1, stiffness: 200, damping: 20 },
  // 标准动画
  STANDARD: { velocity: 0, mass: 1, stiffness: 273, damping: 33 },
  // 果断动画
  DECISIVE: { velocity: 0, mass: 1, stiffness: 363, damping: 38 },
  // 弹性动画
  BOUNCY: { velocity: 0, mass: 1, stiffness: 288, damping: 30 }
};
```

### 9.2 调试技巧

1. **日志记录：** 在关键位置添加日志，打印 isTransitionActive 状态
2. **慢速动画：** 临时增大动画时长，观察细节
3. **ID 检查：** 确保源端和目标端的 ID 完全一致
4. **控制台输出：** 使用 DevTools 检查组件树

---

**文档完成时间:** 2026-06-02
**下一步:** 根据此设计文档编写实施计划
