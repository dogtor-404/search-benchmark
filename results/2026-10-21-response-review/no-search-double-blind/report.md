# 两轮不搜索组错答的四类盲判复核

仅复核用户指定的原已判错：第一轮原100题中的127份、第二轮120题中的275份，共402份。两位独立Codex agent分别读匿名原文，不看组别、轮次、旧判分理由或对方判断；一致直接采用，分歧由第三位独立裁决，第三位也不看前两票。三个独立上下文使用同一基础模型，不是跨模型复核。本次DeepSeek判分API调用为0。

类别互斥：明确弃答、错误的确定断言、不完整回答、试猜或猜到后撤回。规则在判分前冻结，完整语义定义见 [分类规则](rubric.md)。原成绩保持不变。项目另有第一轮96题修订主表，本次按用户指定保留100题主复核，后附同一分类过滤到96题的视图。

## 每组四类计数

### 第一轮 中英文 每组100题

| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 原判错合计 | 确定错误断言/全部题 |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet | 21 | 2 | 0 | 14 | 37 | 2/100 = 2.00% |
| DeepSeek Flash | 16 | 6 | 0 | 12 | 34 | 6/100 = 6.00% |
| Opus | 15 | 2 | 0 | 6 | 23 | 2/100 = 2.00% |
| DeepSeek Pro | 19 | 7 | 1 | 6 | 33 | 7/100 = 7.00% |

### 第二轮 六语种 每组120题

| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 原判错合计 | 确定错误断言/全部题 |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet | 27 | 10 | 2 | 31 | 70 | 10/120 = 8.33% |
| DeepSeek Flash | 17 | 27 | 2 | 33 | 79 | 27/120 = 22.50% |
| Opus | 12 | 11 | 1 | 32 | 56 | 11/120 = 9.17% |
| DeepSeek Pro | 18 | 31 | 2 | 19 | 70 | 31/120 = 25.83% |

四类之和等于每组原判错数，两个轮次分别合计127和275。比例分母使用100和120，不是错误数；原待核未入已确认分子。这里的确定错误断言按原参考答案及输出表述定义，含参考疑问项，不能直接称为严格幻觉率。

第一轮Sonnet/Flash为2/6，Opus/Pro为2/7，样本差异尚不足以判稳定输赢。第二轮分别为10/27和11/31；在本次题集、原判分及本分类口径下，Claude两档均较少，四项比较的Holm校正后仍支持差异。结论仅限这批题，不表示所有小语种或所有任务的总体排名。

## 同档 Claude 与 DeepSeek 的比较

差值为DeepSeek减Claude，正值表示Claude这类错误更少。点值按全部100/120题；配对检验与bootstrap仅用双方原已判的同题。

| 轮次与档位 | Claude 数量/全部题 | DeepSeek 数量/全部题 | 样本比例差 个百分点 | 共同已判n | 条件配对差95%区间 个百分点 | McNemar p | 四项Holm校正p |
|---|---:|---:|---:|---:|---|---:|---:|
| 第一轮 中档 | 2/100 | 6/100 | +4.00 | 99 | [0.00, 10.10] | 0.1250 | 0.2500 |
| 第一轮 高档 | 2/100 | 7/100 | +5.00 | 100 | [-1.00, 11.00] | 0.1797 | 0.2500 |
| 第二轮 中档 | 10/120 | 27/120 | +14.17 | 118 | [6.78, 22.03] | 0.0009 | 0.0027 |
| 第二轮 高档 | 11/120 | 31/120 | +16.67 | 115 | [9.57, 25.22] | 0.0001 | 0.0004 |

置信区间跨0或校正后检验不支持差异时，不能将样本中的数量差写成稳定胜负。两轮题集及原正确性评分口径不同，分别比较，不汇总成模型总排名。原待核可能改变完整题集的差值；上下界保存在 [统计数据](summary.json)。

### 参考疑问的探索性敏感性分析

按题号在同档双方统一排除任一判分员、既有质量标记及选例核查提出的参考疑问。它们并未全部证实参考错误，此表不替代上方冻结参考主计数。

| 轮次与档位 | 排除后共同已判n | DeepSeek减Claude 个百分点 | McNemar p（未校正，探索性） |
|---|---:|---:|---:|
| 第一轮 中档 | 92 | +2.17 | 0.62500 |
| 第一轮 高档 | 92 | +6.52 | 0.03125 |
| 第二轮 中档 | 98 | +14.29 | 0.00258 |
| 第二轮 高档 | 96 | +19.79 | 0.00000 |

## 选例核查中新增的参考疑问

主计数按冻结参考保留，不把下列题作为无争议的幻觉例子。核查发生在揭盲后，完全独立于三位匿名类别裁决。完整说明与链接见 [选例核查记录](example-fact-checks.json)。

- simpleqa_verified-1129：冻结参考110.50米；候选明确回答全长115.5米。美国海军研究生院论文的船型对照表记TCG Yavuz Length Overall为115.5米，专业舰艇资料也记115.5米，可能涉及长度量法或参考错误，不能据此称候选编造。原四类计数仍按冻结参考。 [Naval Postgraduate School学位论文：Fluid-structure interaction effects resulting from hull appendage coupling，表2（原文镜像）](https://upload.wikimedia.org/wikipedia/commons/5/52/Fluid-structure_interaction_effects_resulting_from_hull_appendage_coupling_%28IA_fluidstructurein109452019%29.pdf)、[SeaForces：Yavuz class specifications](https://www.seaforces.org/marint/Turkish-Navy/Frigates/Yavuz-class.htm)。
- msqa-ES-35：原World History Encyclopedia来源确写最终完成1797年；候选1740年也有建筑史原研究支持，例如Javier Aguilera Rojas的La Habana Vieja（1985）以档案地图论述1674至1740工程，西班牙国防部出版的军事史论文也记1674–1740。完工范围或史料存在冲突，不能用作无争议幻觉例子。 [原参考：World History Encyclopedia，Havana段](https://www.worldhistory.org/article/1867/treasure-ports-of-the-spanish-main/)、[Javier Aguilera Rojas：La Habana Vieja，Ciudad y Territorio（1985）](https://javieraguilerarojas.com/wp-content/uploads/2021/07/LA-HABANA-VIEJA.-Mapas-y-planos-en-los-Archivos-de-Espana.-Articulo_compressed.pdf)、[西班牙国防部：Revista de Historia Militar 99](https://publicaciones.defensa.gob.es/media/downloadable/files/links/r/h/rhm_099.pdf)。
- msqa-KO-52：国立国语院词典把候选谚语소 뒷걸음질 치다 쥐 잡다解释为偶然立功；官方问答对原参考가는 날이 장날的解释强调出乎意料的遭遇。题目泛称意外事情巧合地吻合，存在多个近义谚语适用的疑问，不作唯一答案终审。 [国立国语院：한국어기초사전，소，谚语条](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=64289)、[国立国语院：가는 날이 장날问答](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=90&pageIndex=1&qna_seq=329552)。
- msqa-TH-85：冻结参考为阿瑜陀耶早期；候选答后期。泰国诗琳通人类学中心的术语文章记ภาพกาก证据从阿瑜陀耶后期至拉达那哥欣早期，与候选一致，故有参考来源疑问。原参考silpa-mag文章本次503，未据此断言哪一来源最终正确。 [诗琳通人类学中心：กาก术语文章（相关段落由搜索返回可读）](https://www.sac.or.th/portal/th/article/detail/742)、[原参考Silpa Magazine（本次503）](https://www.silpa-mag.com/art/article_158656)。
- msqa-KO-85：原韩国民族文化大百科记1960年代，候选答1950年代。韩国政府Korea.net文章说明army base stew诞生于1950年代，可能涉及起源与后续定型的差别，不能用作无争议事实错误。 [原参考：韩国民族文化大百科，부대찌개](https://encykorea.aks.ac.kr/Article/E0079968)、[韩国政府Korea.net：Eat your way across Korea -- army base stew](https://www.korea.net/NewsFocus/Culture/view?articleId=131279)。

## 项目当前第一轮96题视图

以下只按项目既有4题统一排除规则过滤同一批分类，供与当前主表对照；不替代用户指定的原100题复核。其余参考疑问没有追加到项目删题规则。

| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 保留判错合计 | 确定错误断言/96 |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet | 20 | 1 | 0 | 13 | 34 | 1.04% |
| DeepSeek Flash | 16 | 5 | 0 | 12 | 33 | 5.21% |
| Opus | 15 | 2 | 0 | 5 | 22 | 2.08% |
| DeepSeek Pro | 19 | 6 | 1 | 5 | 31 | 6.25% |

## 判分一致性

两位独立判分一致 389/402（96.77%），分歧 13份全部交第三位独立裁决；Cohen κ=0.9516。第三位在0份中选择前两票之外的类别，这些按预定独立裁决规则采用，并保留三张原票。

[逐题最终类别与证据](resolved.jsonl)、[判分员A](votes/reviewer-a.jsonl)、[判分员B](votes/reviewer-b.jsonl)、[第三位裁决](votes/adjudicator.jsonl)、[裁决凭据](resolution-receipt.json)。

## 每组确定错误断言案例

每组采用同一选择规则：排除任一判分员、既有质量标记及选例核查的参考疑问，优先有补充核查记录，再优先两票一致，随后按回答长度、题号排序，最多两例。不为凑数放宽类别；未选中不影响完整计数。原文、参考答案与来源网址并列，模型名称在分类完成后才还原。全部此类记录（含有争议而未展示的）也保留在 [结构化案例](examples.json) 的 all_confident_incorrect_records_including_flagged 字段，便于核对每组两例为何不足。

### 第一轮 Sonnet

本组最终共2份此类错误，排除参考疑问后可用1例，因此只展示1例。

#### simpleqa_verified-3515

题目：What did George Brown (1818-1880) refuse in 1875?

参考答案：The lieutenant governorship of Ontario

候选回答：

> 我印象中，他在1875年拒绝了英国授予的爵位（骑士头衔 knighthood）。这位George Brown是苏格兰出生的加拿大政治家，《环球报》（The Globe）的创办人，也是加拿大联邦之父之一。
> 
> 具体是哪一级勋位、由谁提出，我记不清，不确定。这条信息我有把握，但没法联网核实。

分类依据：确定回答拒绝爵位，与参考副总督职务冲突；不确定仅针对具体勋位和提出者。

原始输出：[完整记录](../../2026-10-20/jsonl/0/simpleqa_verified-3515.jsonl)；参考来源：[1](https://www.thecanadianencyclopedia.ca/en/article/george-brown)、[2](https://www.ccheritage.ca/biographies/georgebrown)、[3](https://parks.canada.ca/culture/~/~/link.aspx?_id=827CE349BDEB42BE861DB38CEB2925A2&_z=z)、[4](https://parks.canada.ca/culture/designation/lieu-site/maison-george-brown-house)。

补充核查：加拿大政府的George Brown House说明区分：1875年拒绝安大略省副总督职务，1879年拒绝骑士头衔。候选混淆两件事。 [Parks Canada：George Brown House National Historic Site](https://www.canada.ca/en/parks-canada/news/2016/08/george-brown-house-national-historic-site.html)。

### 第一轮 DeepSeek Flash

#### simpleqa_verified-1674

题目：In what country did Richard Serra create his first outdoor sculptures?

参考答案：Japan

候选回答：

> 荷兰（Netherlands）。
> 
> 据我所知，Richard Serra 最早的户外雕塑是在荷兰完成的——1970 年代初期他受荷兰的博物馆／展览委托（如埃因霍温 Van Abbemuseum 的《Sight Point》）开始做户外作品。不过具体年份和第一件作品是哪件，我没有十足把握。

分类依据：肯定回答荷兰，与参考日本冲突；不确定仅涉及年份及作品。

原始输出：[完整记录](../../2026-10-20/jsonl/D0/simpleqa_verified-1674.jsonl)；参考来源：[1](https://en.wikipedia.org/wiki/Richard_Serra)、[2](https://books.google.com.vn/books?id=EDAbPknr8nMC&pg=PA81&lpg=PA81&dq=%22Richard+Serra%22+%22first+outdoor+sculptures%22&source=bl&ots=qCXlU4jMfR&sig=ACfU3U3TRqjtzPOd4n4bZNqcVWkgV7kZvw&hl=en&sa=X&ved=2ahUKEwiRlbOmvZGHAxUXslYBHTPwA4gQ6AF6BAgbEAM)。

补充核查：Fergus McCaffrey画廊展览图录前言记载Serra在1970东京双年展安装其第一件户外雕塑To Encircle Base Plate (Hexagram)，支持日本。馆方所谓第一件大型户外作品或第一件公共委托不是同一限定。PDF过大未由浏览器全文提取；相关段落在搜索返回中可读。 [Fergus McCaffrey：Richard Serra Drawings展览图录，前言第5页](https://forward.fergusmccaffrey.com/wp-content/uploads/2020/06/SerraDrawings_McCaffrey_Final_pages.pdf)。

#### chinese_simpleqa-55b6170ea24a4f0d85b6668b4d750d76

题目：[CHINESE_SIMPLEQA_QUESTION_WITHHELD]

参考答案：1933年

候选回答：

> 据我所知，通常的说法是 **1958 年**：北京最后一家点翠作坊在这一年关闭。此后点翠工艺基本停产，原因主要是翠鸟数量锐减、羽毛来源断绝，以及动物保护观念兴起。
> 
> 不过需要说明：我无法联网核实，这个年份来自常见的中文工艺史叙述；也有资料只笼统说“20 世纪 50 年代”。所以更稳妥的表述是“1958 年前后（20 世纪 50 年代末）”。如果你要引用到正式材料里，建议再查一下故宫博物院或北京工艺美术相关的资料。

分类依据：以1958年前后为肯定年份，与参考1933年冲突，年代近似仍是明确错误。

原始输出：[完整记录](../../2026-10-20/jsonl/D0/chinese_simpleqa-55b6170ea24a4f0d85b6668b4d750d76.jsonl)；参考来源：[1](https://zh.wikipedia.org/wiki/%E7%82%B9%E7%BF%A0)。

补充核查：暨南大学文创研究院文章及新快报原文均记最后一家点翠工厂1933年关闭，支持原参考，非候选1958年。未核查候选其他背景断言。 [暨南大学：点翠，美丽与残忍，传承与保护](https://ccjd.jnu.edu.cn/2021/0601/c23053a626563/page.htm)、[新快报：满头珠翠，今日何在](https://epaper.xkb.com.cn/view/1086572)。

### 第一轮 Opus

本组最终共2份此类错误，排除参考疑问后可用0例，因此只展示0例。

### 第一轮 DeepSeek Pro

#### simpleqa_verified-1674

题目：In what country did Richard Serra create his first outdoor sculptures?

参考答案：Japan

候选回答：

> 加拿大。
> 
> Richard Serra 的第一件户外雕塑一般认为是他 1970–1972 年创作的场地特定作品《Shift》（也有译作《移位》），位于加拿大安大略省金城（King City）的一处农场。

分类依据：确定回答加拿大，与参考日本冲突。

原始输出：[完整记录](../../2026-10-20/jsonl/D0_prime/simpleqa_verified-1674.jsonl)；参考来源：[1](https://en.wikipedia.org/wiki/Richard_Serra)、[2](https://books.google.com.vn/books?id=EDAbPknr8nMC&pg=PA81&lpg=PA81&dq=%22Richard+Serra%22+%22first+outdoor+sculptures%22&source=bl&ots=qCXlU4jMfR&sig=ACfU3U3TRqjtzPOd4n4bZNqcVWkgV7kZvw&hl=en&sa=X&ved=2ahUKEwiRlbOmvZGHAxUXslYBHTPwA4gQ6AF6BAgbEAM)。

补充核查：Fergus McCaffrey画廊展览图录前言记载Serra在1970东京双年展安装其第一件户外雕塑To Encircle Base Plate (Hexagram)，支持日本。馆方所谓第一件大型户外作品或第一件公共委托不是同一限定。PDF过大未由浏览器全文提取；相关段落在搜索返回中可读。 [Fergus McCaffrey：Richard Serra Drawings展览图录，前言第5页](https://forward.fergusmccaffrey.com/wp-content/uploads/2020/06/SerraDrawings_McCaffrey_Final_pages.pdf)。

#### simpleqa_verified-3011

题目：What certification did Reba's album "So Good Together" receive from the United States (RIAA)?

参考答案：platinum

候选回答：

> Reba McEntire 的专辑《So Good Together》（1999）获得的是美国 RIAA 的金唱片认证（Gold，50 万张销量）。
> 
> （凭记忆回答；就我所知，这张专辑当时并未达到白金销量。）

分类依据：确定给出金唱片并否认达到白金，与参考白金认证冲突。

原始输出：[完整记录](../../2026-10-20/jsonl/D0_prime/simpleqa_verified-3011.jsonl)；参考来源：[1](https://www.reba.com/so-good-together)、[2](https://tsort.info/music/cxhcuc.htm)、[3](https://en.wikipedia.org/wiki/So_Good_Together)。

补充核查：歌手Reba官方网站的专辑页明确记载RIAA白金认证，候选答金唱片并否认白金。 [Reba官网：So Good Together](https://www.reba.com/so-good-together)。

### 第二轮 Sonnet

#### msqa-KO-89

题目：안중근은 언제 천주교에 입교했습니까?

参考答案：1897년

候选回答：

> 安重根(안중근)在 1895 年入教,当时约 16 岁(虚岁 17)。他随父亲安泰勋(안태훈)在黄海道信川郡清溪洞接受洗礼,主持的是法国传教士威廉神父(Joseph Wilhelm,韩文名洪錫九)。他的圣名是多默(도마,Thomas)。
> 
> 具体是 1895 年的哪个月,我记得不够确定,就不乱说了。

分类依据：确定入教年份1895，与参考1897冲突；不确定只针对月份。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/0/msqa-KO-89.jsonl)；参考来源：[1](https://ko.wikipedia.org/wiki/%EC%95%88%EC%A4%91%EA%B7%BC)。

补充核查：韩国独立纪念馆的《安重根的生涯与救国运动》天主教入教章节记1897年，支持原参考；候选1895年并非只缺月份。 [韩国独立纪念馆：안중근의 생애와 구국운동](https://search.i815.or.kr/publication/yeoljeon/detail.do?id=9-AJ0001-000)。

#### msqa-KO-63

题目：풍양 조씨의 시조 조맹의 본명은 무엇인가?

参考答案：바우

候选回答：

> 조지수(趙之壽)로 알고 있습니다. 풍양 조씨의 시조 조맹(趙孟)은 본명이 조지수이고, 고려 초에 공을 세워 '맹'이라는 이름을 받았다고 기억합니다. 다만 이 내용은 기억에 의존한 것이고 네트워크를 쓰지 않아 확인하지 못했으니, 족보나 한국민족문화대백과 같은 자료로 확인해 보시길 권합니다.

分类依据：肯定把本名回答为조지수，与参考바우不同；凭记忆和未核实说明未构成明显猜测。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/0/msqa-KO-63.jsonl)；参考来源：[1](https://baike.baidu.com/item/%E4%B8%B0%E5%A3%A4%E8%B5%B5%E6%B0%8F/4897662?fromModule=lemma_inlink)。

补充核查：韩国学中央研究院数字南杨州文化大典记始祖本名趙岩（조암），与바우的岩/石之名存在文字形式差异，但不支持候选趙之壽。只据此确认候选核心姓名不符，不强行断定所有本名写法唯一。相关内容由搜索返回可读。 [数字南杨州文化大典：풍양 조씨](https://namyangju.grandculture.net/namyangju/index/GC08900532?category=%EC%9D%B8%EB%AA%85&depth=2&name=A~Z%2C0~9&page=111&search=%EC%A1%B0%EC%A7%80%EB%A6%B0)。

### 第二轮 DeepSeek Flash

#### msqa-JA-58

题目：ハタハタの湯上げはどこの県の代表的な郷土料理ですか

参考答案：山形県

候选回答：

> 秋田県（秋田县）。
> 
> ハタハタ（鰰、叉牙鱼）是秋田县的代表性鱼，“ハタハタの湯上げ”就是把ハタハタ在热水中快速焯过后食用的秋田乡土料理。

分类依据：确定给出秋田县，与参考山形县冲突。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/D0/msqa-JA-58.jsonl)；参考来源：[1](https://allabout.co.jp/gm/gc/405065/)。

补充核查：日本农林水产省乡土料理数据库将ハタハタの湯上げ列在山形县，主传承地区庄内，支持原参考。候选答秋田县。 [日本农林水产省：ハタハタの湯上げ 山形県](https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/menu/hatahatanoyuage_yamagata.html)。

#### msqa-JA-86

题目：相術師に四十歳まで生きられないと告げられた後、東大寺を離れ、笠置の洞窟へ転向して厳しい修行に励んだのは誰ですか。

参考答案：東大寺の僧・蔵満

候选回答：

> 是**明恵**（みょうえ，1173–1232），讳**高弁**（こうべん）。
> 
> 他是镰仓时代华严宗僧人，后来在京都栂尾开创了高山寺。相传他19岁时被相术师告知“活不过四十岁”，于是离开东大寺，转入笠置山的洞窟中苦修。

分类依据：确定回答明惠，与参考藏满不同。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/D0/msqa-JA-86.jsonl)；参考来源：[1](https://yatanavi.org/text/k_konjaku/k_konjaku17-17)。

补充核查：《今昔物语集》卷17第17话的电子原文题名及正文记蔵満，包含相人预言不过四十岁及入笠置窟苦行的情节；候选把人物换成明惠。 [《今昔物语集》卷17第17话原文电子版](https://yatanavi.org/text/k_konjaku/k_konjaku17-17)。

### 第二轮 Opus

本组最终共11份此类错误，排除参考疑问后可用1例，因此只展示1例。

#### msqa-ID-82

题目：Bahasa Bugis paling dekat hubungannya dengan bahasa apa saja?

参考答案：Bahasa Campalagian dan Bahasa Tamanic

候选回答：

> **布吉语（Bahasa Bugis）**属于南岛语系马来-波利尼西亚语族的**南苏拉威西语支**。按常见的分类（如 Ethnologue 和 Grimes & Friberg 的分类），与它关系最近的语言如下：
> 
> 1. **坎帕拉吉安语（Campalagian）**：关系最近。它和布吉语同属南苏拉威西语支下的“布吉语群”。
> 2. **南苏拉威西语支的其他语言**：
>    - **望加锡语（Makassar）**：自成一个小语群，地理上与布吉语相邻，文化上也联系紧密。两者历史上都用 Lontara 文字书写。
>    - **马森伦普卢诸语（Massenrempulu）**：包括恩雷康语（Enrekang）、杜里语（Duri）、马伊瓦语（Maiwa）等。
>    - **北部语群**：包括曼达尔语（Mandar）、马马萨语（Mamasa）、托拉查-萨丹语（Toraja-Sa'dan）等。
>    - 塞科语（Seko）、勒莫朗语（Lemolang）等小语言。
> 
> **简答**：最近的是坎帕拉吉安语，其次是同语支的望加锡语、曼达尔语、托拉查语和马森伦普卢诸语。
> 
> （以上凭已有知识回答，没有上网查证。细节可能因分类体系不同而有出入。）

分类依据：确定列Campalagian之后为Makassar等最近语言，未给参考Tamanic且以其他语言替代。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/0_prime/msqa-ID-82.jsonl)；参考来源：[1](https://en.wikipedia.org/wiki/Buginese_language)。

补充核查：ASJP语言数据库给出Buginese属于Tamanic-Bugis下Bugis的分类，Glottolog也列相应谱系；原来源明确最近为Campalagian和Tamanic。候选漏Tamanic，并把其他南苏拉威西语支列为其次最近；此例涉及分类体系，建议视频优先使用更直观的姓名/编号题。 [ASJP：Wordlist Buginese，Classification](https://asjp.clld.org/languages/BUGINESE)、[Glottolog：Buginese](https://glottolog.org/resource/languoid/id/bugi1244)、[原参考：Buginese language，Classification](https://en.wikipedia.org/wiki/Buginese_language)。

### 第二轮 DeepSeek Pro

#### msqa-JA-55

题目：「神奈備にひもろき立てて斎へども人の心は守りあへぬもの」の出典として正しいものを答えよ（巻・歌番号まで明記せよ）。

参考答案：『万葉集』巻第十一・2657

候选回答：

> 《万叶集》卷十一，歌番号二三六二（作者未详）。

分类依据：确定给出卷十一第2362首，歌号与参考2657冲突。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/D0_prime/msqa-JA-55.jsonl)；参考来源：[1](https://kakuyomu.jp/works/1177354054888007402/episodes/16816452220428845918)。

补充核查：國學院大學数字博物馆ひもろき条收录目标句并标11-2657，支持卷十一2657，非候选2362。 [國學院大學数字博物馆：ひもろき](https://jmapps.ne.jp/kokugakuin/det.html?data_id=32261)。

#### msqa-JA-53

题目：「よもすから ちきりしことを わすれすは こひむなみたの いろそゆかしき」の出典として正しいものを、勅撰和歌集名・巻名・歌番号まで明記して答えよ。

参考答案：『後拾遺和歌集』巻第十「哀傷」・536番

候选回答：

> 出典は『古今和歌集』巻第十三「恋歌三」、**第六二八番**。
> 
> 詠者は藤原興風です。

分类依据：确定给出古今集恋三628，与参考后拾遗集哀伤536冲突。

原始输出：[完整记录](../../2026-10-21-multilingual/jsonl/D0_prime/msqa-JA-53.jsonl)；参考来源：[1](https://lapis.nichibun.ac.jp/waka/waka_i004.html)。

补充核查：国际日本文化研究中心和歌数据库的後拾遺集原文，卷十哀伤的00536条为目标句，非候选古今集卷十三628。 [国际日本文化研究中心：後拾遺集全文](https://lapis.nichibun.ac.jp/waka/waka_i004.html)。

## 范围与原结果

本次只给原判错核心答案分类，没有逐条审核所有回答的附带事实，也没有重新校正有争议的参考答案。确定断言是文字表述类别，不证明有意造假或可观察到模型内部确信度。旧有72/112条清单仍保留为历史补充，不能替代本次402条双盲分类；旧清单未采用本次四类互斥规则，因此也不能继续作为本次明确弃答类别的保证下界。

[原始选择与匿名化凭据](protocol.json)、[完整结构化计数](summary.json)、[结构化案例](examples.json)。
