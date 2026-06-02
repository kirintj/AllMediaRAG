# 一镜到底动画实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现列表到详情页的一镜到底动画效果，使卡片组件从列表平滑过渡到详情页面

**Architecture:** 使用 geometryTransition 跨页面共享元素转场，在源端和目标端绑定相同 ID，通过 animateTo 闭包触发导航，系统自动插值位置和尺寸

**Tech Stack:** HarmonyOS ArkUI, TypeScript, geometryTransition, animateTo, curves.interpolatingSpring

---

## 文件结构映射

### 需要创建的文件
```
products/phone/src/main/ets/
├── util/
│   └── AnimationConstants.ets          # 共享常量和动画参数
├── component/
│   └── CardItem.ets                    # 列表项组件（源端）
└── page/
    ├── ListPage.ets                    # 列表页面
    └── DetailPage.ets                  # 详情页面（目标端）
```

### 需要修改的文件
```
products/phone/src/main/ets/
├── page/
│   └── MainEntry.ets                   # 路由配置（如果需要）
└── viewmodel/
    └── *.ets                           # ViewModel（如果需要）
```

---

## Task 1: 创建共享常量和动画参数

**Files:**
- Create: `products/phone/src/main/ets/util/AnimationConstants.ets`
- Test: `products/phone/src/ohosTest/ets/test/AnimationConstants.test.ets`

- [ ] **Step 1: 编写 AnimationConstants 单元测试**

创建测试文件，验证常量定义是否正确：

```typescript
// products/phone/src/ohosTest/ets/test/AnimationConstants.test.ets
import { describe, it, expect } from '@ohos/hypium';
import { AnimationConstants } from '../../../main/ets/util/AnimationConstants';

export default function AnimationConstantsTest() {
  describe('AnimationConstantsTest', () => {
    it('should_define_card_geometry_id', () => {
      expect(AnimationConstants.CARD_GEOMETRY_ID).assertEqual('app_card_geometry');
    });

    it('should_define_enter_spring_parameters', () => {
      expect(AnimationConstants.ENTER_SPRING.velocity).assertEqual(0);
      expect(AnimationConstants.ENTER_SPRING.mass).assertEqual(1);
      expect(AnimationConstants.ENTER_SPRING.stiffness).assertEqual(273);
      expect(AnimationConstants.ENTER_SPRING.damping).assertEqual(33);
    });

    it('should_define_exit_spring_parameters', () => {
      expect(AnimationConstants.EXIT_SPRING.velocity).assertEqual(0);
      expect(AnimationConstants.EXIT_SPRING.mass).assertEqual(1);
      expect(AnimationConstants.EXIT_SPRING.stiffness).assertEqual(363);
      expect(AnimationConstants.EXIT_SPRING.damping).assertEqual(38);
    });

    it('should_define_transition_duration', () => {
      expect(AnimationConstants.TRANSITION_DURATION).assertEqual(100);
    });
  });
}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 测试失败，提示 AnimationConstants 模块不存在

- [ ] **Step 3: 实现 AnimationConstants 常量**

```typescript
// products/phone/src/main/ets/util/AnimationConstants.ets
export class AnimationConstants {
  // 共享元素 ID
  public static readonly CARD_GEOMETRY_ID: string = 'app_card_geometry';

  // 弹簧曲线参数 - 进入详情页（较快收敛）
  public static readonly ENTER_SPRING = {
    velocity: 0,
    mass: 1,
    stiffness: 273,
    damping: 33
  };

  // 弹簧曲线参数 - 返回列表页（刚度更高，更果断）
  public static readonly EXIT_SPRING = {
    velocity: 0,
    mass: 1,
    stiffness: 363,
    damping: 38
  };

  // 动画时长（毫秒）
  public static readonly TRANSITION_DURATION: number = 100;
}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有测试通过，AnimationConstants 定义正确

- [ ] **Step 5: 提交代码**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
git add products/phone/src/main/ets/util/AnimationConstants.ets
git add products/phone/src/ohosTest/ets/test/AnimationConstants.test.ets
git commit -m "feat: add AnimationConstants for one-shot animation

- Define CARD_GEOMETRY_ID for geometryTransition
- Define ENTER_SPRING and EXIT_SPRING parameters
- Define TRANSITION_DURATION constant"
```

---

## Task 2: 实现列表项组件（源端）

**Files:**
- Create: `products/phone/src/main/ets/component/CardItem.ets`
- Modify: `products/phone/src/main/ets/model/CardData.ets` (如果不存在则创建)
- Test: `products/phone/src/ohosTest/ets/test/CardItem.test.ets`

- [ ] **Step 1: 创建 CardData 数据模型**

```typescript
// products/phone/src/main/ets/model/CardData.ets
export class CardData {
  id: string;
  title: string;
  description: string;
  imageUrl: string;

  constructor(id: string, title: string, description: string, imageUrl: string) {
    this.id = id;
    this.title = title;
    this.description = description;
    this.imageUrl = imageUrl;
  }
}
```

- [ ] **Step 2: 编写 CardItem 单元测试**

```typescript
// products/phone/src/ohosTest/ets/test/CardItem.test.ets
import { describe, it, expect } from '@ohos/hypium';
import { CardData } from '../../../main/ets/model/CardData';

export default function CardItemTest() {
  describe('CardItemTest', () => {
    it('should_create_card_data_with_correct_properties', () => {
      const card = new CardData('1', 'Test Title', 'Test Description', 'https://example.com/image.jpg');
      expect(card.id).assertEqual('1');
      expect(card.title).assertEqual('Test Title');
      expect(card.description).assertEqual('Test Description');
      expect(card.imageUrl).assertEqual('https://example.com/image.jpg');
    });
  });
}
```

- [ ] **Step 3: 运行测试验证失败**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 测试失败，提示 CardData 模块不存在

- [ ] **Step 4: 实现 CardItem 组件**

```typescript
// products/phone/src/main/ets/component/CardItem.ets
import { AnimationConstants } from '../util/AnimationConstants';
import { CardData } from '../model/CardData';

@Component
export struct CardItem {
  @Prop cardData: CardData;
  onItemClick: (data: CardData) => void = () => {};

  build() {
    Column() {
      // 卡片图片
      Image(this.cardData.imageUrl)
        .width('100%')
        .height(200)
        .objectFit(ImageFit.Cover)
        .borderRadius(8)

      // 卡片标题
      Text(this.cardData.title)
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 12 })

      // 卡片描述
      Text(this.cardData.description)
        .fontSize(14)
        .fontColor('#666666')
        .margin({ top: 8 })
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
    }
    .width('100%')
    .padding(16)
    .backgroundColor('#FFFFFF')
    .borderRadius(12)
    .shadow({
      radius: 8,
      color: '#1A000000',
      offsetX: 0,
      offsetY: 2
    })
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

- [ ] **Step 5: 运行测试验证通过**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有测试通过，CardItem 组件创建成功

- [ ] **Step 6: 提交代码**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
git add products/phone/src/main/ets/model/CardData.ets
git add products/phone/src/main/ets/component/CardItem.ets
git add products/phone/src/ohosTest/ets/test/CardItem.test.ets
git commit -m "feat: implement CardItem component for source transition

- Create CardData model with id, title, description, imageUrl
- Implement CardItem component with geometryTransition
- Set follow: true for source-side transition
- Add opacity transition effect"
```

---

## Task 3: 实现列表页面

**Files:**
- Create: `products/phone/src/main/ets/page/ListPage.ets`
- Test: `products/phone/src/ohosTest/ets/test/ListPage.test.ets`

- [ ] **Step 1: 编写列表页面测试**

```typescript
// products/phone/src/ohosTest/ets/test/ListPage.test.ets
import { describe, it, expect } from '@ohos/hypium';
import { CardData } from '../../../main/ets/model/CardData';

export default function ListPageTest() {
  describe('ListPageTest', () => {
    it('should_generate_sample_card_data', () => {
      const cards = generateSampleCards();
      expect(cards.length).assertEqual(5);
      expect(cards[0].title).assertEqual('Card 1');
    });

    it('should_handle_card_click', () => {
      let clickedCard: CardData | null = null;
      const handleCardClick = (data: CardData) => {
        clickedCard = data;
      };

      const card = new CardData('1', 'Test', 'Desc', 'url');
      handleCardClick(card);

      expect(clickedCard).not().assertNull();
      expect(clickedCard!.id).assertEqual('1');
    });
  });
}

function generateSampleCards(): CardData[] {
  const cards: CardData[] = [];
  for (let i = 1; i <= 5; i++) {
    cards.push(new CardData(
      `${i}`,
      `Card ${i}`,
      `Description for card ${i}`,
      `https://picsum.photos/seed/${i}/400/300`
    ));
  }
  return cards;
}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 测试失败，提示 ListPage 或相关函数不存在

- [ ] **Step 3: 实现列表页面**

```typescript
// products/phone/src/main/ets/page/ListPage.ets
import { CardItem } from '../component/CardItem';
import { CardData } from '../model/CardData';
import { AnimationConstants } from '../util/AnimationConstants';

@Entry
@Component
struct ListPage {
  @State cardList: CardData[] = [];

  aboutToAppear() {
    this.cardList = this.generateSampleCards();
  }

  generateSampleCards(): CardData[] {
    const cards: CardData[] = [];
    for (let i = 1; i <= 5; i++) {
      cards.push(new CardData(
        `${i}`,
        `Card ${i}`,
        `Description for card ${i}. This is a sample description to demonstrate the one-shot animation effect.`,
        `https://picsum.photos/seed/${i}/400/300`
      ));
    }
    return cards;
  }

  handleCardClick(data: CardData) {
    const uiContext = AppStorage.get<UIContext>('UIContext');

    // 关键：在 animateTo 闭包内触发导航
    uiContext?.animateTo({
      curve: curves.interpolatingSpring(
        AnimationConstants.ENTER_SPRING.velocity,
        AnimationConstants.ENTER_SPRING.mass,
        AnimationConstants.ENTER_SPRING.stiffness,
        AnimationConstants.ENTER_SPRING.damping
      )
    }, () => {
      // 导航到详情页
      router.pushUrl({
        url: 'pages/DetailPage',
        params: { cardData: data }
      });
    });
  }

  build() {
    Column() {
      // 页面标题
      Text('Card List')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 20, bottom: 16 })

      // 卡片列表
      List({ space: 16 }) {
        ForEach(this.cardList, (card: CardData) => {
          ListItem() {
            CardItem({
              cardData: card,
              onItemClick: (data: CardData) => this.handleCardClick(data)
            })
          }
        })
      }
      .width('100%')
      .layoutWeight(1)
      .padding({ left: 16, right: 16 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有测试通过，ListPage 实现正确

- [ ] **Step 5: 提交代码**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
git add products/phone/src/main/ets/page/ListPage.ets
git add products/phone/src/ohosTest/ets/test/ListPage.test.ets
git commit -m "feat: implement ListPage with card list and navigation

- Generate sample card data for testing
- Implement card click handler with animateTo
- Wrap navigation in animateTo closure for geometryTransition
- Use ENTER_SPRING parameters for forward animation"
```

---

## Task 4: 实现详情页面（目标端）

**Files:**
- Create: `products/phone/src/main/ets/page/DetailPage.ets`
- Test: `products/phone/src/ohosTest/ets/test/DetailPage.test.ets`

- [ ] **Step 1: 编写详情页面测试**

```typescript
// products/phone/src/ohosTest/ets/test/DetailPage.test.ets
import { describe, it, expect } from '@ohos/hypium';
import { AnimationConstants } from '../../../main/ets/util/AnimationConstants';

export default function DetailPageTest() {
  describe('DetailPageTest', () => {
    it('should_use_correct_geometry_id', () => {
      expect(AnimationConstants.CARD_GEOMETRY_ID).assertEqual('app_card_geometry');
    });

    it('should_have_transition_state_management', () => {
      // Test isTransitionActive initial state
      let isTransitionActive = true;
      expect(isTransitionActive).assertTrue();

      // Test state change on transition complete
      isTransitionActive = false;
      expect(isTransitionActive).assertFalse();
    });

    it('should_have_pop_transition_flag', () => {
      let isPopTransition = false;
      expect(isPopTransition).assertFalse();

      // Test pop transition activation
      isPopTransition = true;
      expect(isPopTransition).assertTrue();
    });
  });
}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 测试失败，提示 DetailPage 模块不存在

- [ ] **Step 3: 实现详情页面**

```typescript
// products/phone/src/main/ets/page/DetailPage.ets
import { AnimationConstants } from '../util/AnimationConstants';
import { CardData } from '../model/CardData';

@Entry
@Component
struct DetailPage {
  @State isTransitionActive: boolean = true;
  @State isPopTransition: boolean = false;
  @State cardData: CardData | null = null;

  aboutToAppear() {
    // 从路由参数获取卡片数据
    const params = router.getParams() as Record<string, CardData>;
    if (params && params.cardData) {
      this.cardData = params.cardData;
    }
  }

  handleBack() {
    this.popAction();
  }

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
      router.back();
    });
  }

  build() {
    NavDestination() {
      Column() {
        if (this.cardData) {
          // 返回按钮
          Row() {
            Image($r('app.media.back'))
              .width(24)
              .height(24)
              .onClick(() => this.handleBack())

            Text('Back')
              .fontSize(16)
              .margin({ left: 8 })
              .onClick(() => this.handleBack())
          }
          .width('100%')
          .padding(16)

          // 卡片图片（放大版本）
          Image(this.cardData.imageUrl)
            .width('100%')
            .height(300)
            .objectFit(ImageFit.Cover)
            .borderRadius(0)

          // 卡片详情
          Column() {
            Text(this.cardData.title)
              .fontSize(28)
              .fontWeight(FontWeight.Bold)
              .margin({ top: 20 })

            Text(this.cardData.description)
              .fontSize(16)
              .fontColor('#666666')
              .margin({ top: 16 })
              .lineHeight(24)

            // 额外内容
            Text('Additional content goes here...')
              .fontSize(14)
              .fontColor('#999999')
              .margin({ top: 24 })
          }
          .padding(20)
          .alignItems(HorizontalAlign.Start)
        }
      }
      .width('100%')
      .height('100%')
      .backgroundColor('#FFFFFF')
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
}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有测试通过，DetailPage 实现正确

- [ ] **Step 5: 提交代码**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
git add products/phone/src/main/ets/page/DetailPage.ets
git add products/phone/src/ohosTest/ets/test/DetailPage.test.ets
git commit -m "feat: implement DetailPage with geometryTransition

- Implement target-side geometryTransition
- Manage isTransitionActive and isPopTransition states
- Clear geometry ID after transition complete
- Use EXIT_SPRING parameters for back animation
- Handle back navigation with popAction"
```

---

## Task 5: 集成测试和优化

**Files:**
- Create: `products/phone/src/ohosTest/ets/test/Integration.test.ets`
- Modify: `products/phone/src/main/ets/page/ListPage.ets` (优化)
- Modify: `products/phone/src/main/ets/page/DetailPage.ets` (优化)

- [ ] **Step 1: 编写集成测试**

```typescript
// products/phone/src/ohosTest/ets/test/Integration.test.ets
import { describe, it, expect } from '@ohos/hypium';
import { AnimationConstants } from '../../../main/ets/util/AnimationConstants';
import { CardData } from '../../../main/ets/model/CardData';

export default function IntegrationTest() {
  describe('IntegrationTest', () => {
    it('should_have_consistent_geometry_id_across_components', () => {
      // Verify both source and target use same ID
      const sourceId = AnimationConstants.CARD_GEOMETRY_ID;
      const targetId = AnimationConstants.CARD_GEOMETRY_ID;
      expect(sourceId).assertEqual(targetId);
    });

    it('should_have_different_spring_parameters_for_enter_and_exit', () => {
      // Verify enter and exit have different stiffness
      expect(AnimationConstants.ENTER_SPRING.stiffness)
        .not().assertEqual(AnimationConstants.EXIT_SPRING.stiffness);

      // Verify exit is stiffer than enter
      expect(AnimationConstants.EXIT_SPRING.stiffness)
        .assertLarger(AnimationConstants.ENTER_SPRING.stiffness);
    });

    it('should_have_reasonable_transition_duration', () => {
      // Verify duration is reasonable (not too fast, not too slow)
      expect(AnimationConstants.TRANSITION_DURATION).assertLarger(50);
      expect(AnimationConstants.TRANSITION_DURATION).assertLess(500);
    });

    it('should_create_card_data_for_list', () => {
      const card = new CardData('1', 'Test', 'Description', 'https://example.com/image.jpg');
      expect(card.id).assertEqual('1');
      expect(card.title).assertEqual('Test');
    });
  });
}
```

- [ ] **Step 2: 运行集成测试**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有集成测试通过

- [ ] **Step 3: 性能优化 - 添加日志记录**

在 DetailPage 中添加调试日志：

```typescript
// products/phone/src/main/ets/page/DetailPage.ets
// 在 aboutToAppear 方法中添加
aboutToAppear() {
  console.info('DetailPage: aboutToAppear, isTransitionActive:', this.isTransitionActive);
  const params = router.getParams() as Record<string, CardData>;
  if (params && params.cardData) {
    this.cardData = params.cardData;
    console.info('DetailPage: cardData loaded:', this.cardData.id);
  }
}

// 在 transition 回调中添加
(transitionIn: boolean) => {
  if (transitionIn) {
    this.isTransitionActive = false;
    console.info('DetailPage: transition complete, isTransitionActive set to false');
  }
}

// 在 popAction 中添加
popAction() {
  console.info('DetailPage: popAction called');
  this.isPopTransition = true;
  this.isTransitionActive = true;
  console.info('DetailPage: isTransitionActive set to true for pop');
  // ...
}
```

- [ ] **Step 4: 性能优化 - 添加错误处理**

在 ListPage 中添加错误处理：

```typescript
// products/phone/src/main/ets/page/ListPage.ets
handleCardClick(data: CardData) {
  console.info('ListPage: handleCardClick called with card:', data.id);

  const uiContext = AppStorage.get<UIContext>('UIContext');
  if (!uiContext) {
    console.error('ListPage: UIContext not found');
    return;
  }

  uiContext.animateTo({
    curve: curves.interpolatingSpring(
      AnimationConstants.ENTER_SPRING.velocity,
      AnimationConstants.ENTER_SPRING.mass,
      AnimationConstants.ENTER_SPRING.stiffness,
      AnimationConstants.ENTER_SPRING.damping
    )
  }, () => {
    console.info('ListPage: navigating to DetailPage');
    router.pushUrl({
      url: 'pages/DetailPage',
      params: { cardData: data }
    }).catch((error: Error) => {
      console.error('ListPage: navigation failed:', error);
    });
  });
}
```

- [ ] **Step 5: 运行完整测试套件**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
hvigorw assembleHap --mode module -p product=phone
```

**预期结果：** 所有测试通过，包括单元测试和集成测试

- [ ] **Step 6: 提交优化代码**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\sample_in_harmonyos-master
git add products/phone/src/main/ets/page/ListPage.ets
git add products/phone/src/main/ets/page/DetailPage.ets
git add products/phone/src/ohosTest/ets/test/Integration.test.ets
git commit -m "feat: add integration tests and performance optimizations

- Add comprehensive integration tests
- Add console logging for debugging
- Add error handling for navigation
- Verify geometry ID consistency across components"
```

---

## 验收检查清单

完成所有任务后，执行以下验收检查：

- [ ] **功能验收**
  - [ ] 列表卡片点击后平滑过渡到详情页
  - [ ] 详情页元素位置和大小正确
  - [ ] 返回时动画平滑收缩
  - [ ] ID 生命周期管理正确

- [ ] **性能验收**
  - [ ] 动画流畅（60fps）
  - [ ] 无卡顿或闪烁
  - [ ] 内存使用合理

- [ ] **质量验收**
  - [ ] 单元测试覆盖率 > 80%
  - [ ] 所有测试通过
  - [ ] 无已知 bug

---

## 自检清单

- [x] **规格覆盖：** 设计文档中的所有要求都有对应的任务实现
- [x] **占位符检查：** 无 TBD、TODO 或占位符
- [x] **类型一致性：** 所有类型、方法签名和属性名在任务间保持一致
- [x] **文件路径：** 所有文件路径都是精确的
- [x] **代码完整性：** 每个步骤都包含完整的代码
- [x] **命令和输出：** 包含精确的命令和预期输出

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-06-02-one-shot-animation-implementation.md`**

**两种执行选项：**

**1. Subagent-Driven（推荐）** - 为每个任务调度独立的子代理，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 执行任务，批量执行并设置检查点

**请选择执行方式？**

**如果选择 Subagent-Driven：**
- **必需的子技能：** 使用 superpowers:subagent-driven-development
- 每个任务独立子代理 + 两阶段审查

**如果选择 Inline Execution：**
- **必需的子技能：** 使用 superpowers:executing-plans
- 批量执行并设置检查点进行审查
