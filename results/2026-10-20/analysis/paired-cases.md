# 同题搜索对照

包含两种搜索评分不同或单方未决的全部同题案例，避免只挑一方获胜。以下评分均按本次参考答案和AI多数票；质量标记保留，尚未逐一作独立来源裁决。

## A / B：simpleqa_verified-1674

题目：In what country did Richard Serra create his first outdoor sculptures?

参考答案：Japan

题意质量标记：未标记

### Sonnet + Claude搜索：错误

查询：Richard Serra first outdoor sculptures country；Richard Serra Shift King City Ontario first outdoor sculpture Canada；"Richard Serra" "first outdoor sculptures" 

耗时33.150秒，可见返回8147字节。

回答：

**答案：美国（不完全确定）。**

搜到的资料里，早期户外作品都在美国：

- 布朗克斯（纽约）的《To Encircle Base Plate Hexagon, Right Angles Inverted》，1970 年，被称为他的第一件大型户外作品。
- 圣路易斯附近的《Pulitzer Piece》，古根海姆毕尔巴鄂的年表称它是他最早的大型户外雕塑，也是他第一件场域特定作品。

两种说法的标准不同（"主要户外展出"和"大型户外雕塑"），所以没有哪一个被直接确认为"第一件"。

加拿大安大略省的《Shift》（1970–72）只被称为早期作品，没有资料说它是第一件。有一个播客来源说 1968 年他在长岛海滩做过户外作品，但它与其他来源矛盾，我没有采信。

我没有找到一份注明年份的美术馆或专著来源来定论。

Sources:
- [Untapped Cities：布朗克斯的第一件大型户外作品](https://untappedcities.com/richard-serras-first-major-outdoor-installation-was-located-at-183rd-street-in-the-bronx-nyc)
- [Guggenheim Bilbao：Serra 年表](https://guggenheim-bilbao.eus/en/the-collection/artists/richard-serra)
- [Wikipedia：Shift (sculpture)](https://en.wikipedia.org/wiki/Shift_(sculpture))

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：Richard Serra first outdoor sculptures country；Richard Serra "first outdoor" sculptures Japan 1970 Tokyo Biennale Shift

耗时13.217秒，可见返回36336字节。

回答：

**答案:日本。**

理查德·塞拉(Richard Serra)最早的户外雕塑是 1970 年在东京上野公园创作的《To Encircle Base Plate (Hexagram)》和《Sugi Tree》。这两件作品是为第 10 届东京双年展(Tokyo Biennale)做的。

依据:
- 维基百科的说法是:"His first outdoor sculptures, To Encircle Base Plate (Hexagram) (1970) and Sugi Tree (1970), were both installed in Ueno Park as part of the 'Tokyo Biennale.'" 我看到的是镜像页:https://browse.library.kiwix.org/content/wikipedia_en_all_maxi/A/Richard_Serra
- Fergus McCaffrey 刊载的峰村敏明(Minemura Toshiaki)文章,讲了这两件作品在东京双年展的情况:https://forward.fergusmccaffrey.com/when-the-world-was-half-visible-half-invisible-by-minemura-toshiaki/
- 高松宫殿下纪念世界文化奖的介绍,也提到他 1970 年受邀参加东京双年展,在上野公园种了杉树、埋了铁环:https://www.praemiumimperiale.org/laureate/serra/

说明:"首批户外雕塑"这一说法,我只在维基百科上看到明确表述。其他两个来源只证实了 1970 年东京双年展上的作品,没有写"首批"。

搜索用了 2 次。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：simpleqa_verified-2095

题目：How many times has the Pakistan People's Party emerged as the leading opposition party in Pakistan on a national level until 2022?

参考答案：4

题意质量标记：未标记

### Sonnet + Claude搜索：错误

查询：Pakistan People's Party emerged as the leading opposition party times national level；Pakistan Peoples Party Wikipedia "opposition" 1990 1997 2013 2018 leader of the opposition National Assembly PPP times

耗时33.658秒，可见返回5801字节。

回答：

**Short answer: 3 times, in 1990, 1997 and 2013.** This is my reading of the sources. None of them states the count directly.

- **1990:** The IJI won and Nawaz Sharif became prime minister. Benazir Bhutto then led the opposition.
- **1997:** The PML-N won 137 seats and the PPP came second with 18.
- **2013:** The PPP became the largest opposition party in the National Assembly, and Khurshid Shah was opposition leader from 2013 to 2018.

I left out two cases:
- **2002:** The PPP came second, but the sources don't show it held the main opposition role. From memory, the MMA's Maulana Fazlur Rehman became opposition leader, though that part is not from the sources.
- **2018:** The PPP opposed the PTI government but was not the lead opposition party. From memory, the PML-N's Shehbaz Sharif was opposition leader, though that part is not from the sources.

Sources:
- [Dawn – Pakistan Peoples Party](https://www.dawn.com/news/1404648)
- [Carnegie – The peculiar case of the PPP as an opposition party](https://carnegieendowment.org/research/2022/03/the-peculiar-case-of-the-pakistan-peoples-party-as-an-opposition-party)
- [ARY News – Syed Khurshid Shah](https://arynews.tv/syed-khurshid-shah)
- [The News – PPP returns to the Centre stage](https://www.thenews.pk/tns/detail/963114-ppp-returns-to-the-centre-stage)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：Pakistan People's Party emerged as the leading opposition party national level times；Pakistan Peoples Party Wikipedia "opposition" "times" 1977 1990 1997 2002 2013 2018 largest opposition party National Assembly

耗时12.498秒，可见返回61745字节。

回答：

**答案:4 次**,分别是 1990、1997、2002 和 2013 年的大选。

依据是一篇论文摘要的原话:PPP 五次上台执政(1970、1977、1988、1993、2008),另外四次成为主要反对党(1990、1997、2002、2013)。

- 论文摘要:https://www.webology.org/abstract.php?id=4292

另一个来源是 Dawn 的 PPP 专题,它也提到 PPP 在 2002 年排第二(81 席),在 1997 年也排第二(18 席)。其中 1997 年是我根据席位排名推断的:当年 PML-N 大胜,PPP 席位第二。
- https://www.dawn.com/news/1806791

这个数字只有一个来源直接给出,我没找到第二个来源能独立核实。

另外,这个"4 次"没有把 1970 年算进去。1970 年 PPP 是国民议会第二大党,但当时它没有成为反对党。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：chinese_simpleqa-4bbc0cb7b62340869edc384db4813a9e

题目：[CHINESE_SIMPLEQA_QUESTION_WITHHELD]

参考答案：1984

题意质量标记：有（独立AI标记，仍需核实）

### Sonnet + Claude搜索：待核

查询：菲律宾圣若瑟教区 设立 天主教 Diocese of San Jose Philippines established

耗时21.869秒，可见返回2492字节。

回答：

有两个菲律宾教区都叫"圣若瑟教区"。你问的没写明是哪一个,所以我两个都列出来。

- **新埃西哈圣若瑟教区(Diocese of San Jose, Nueva Ecija):1984 年设立。** 它是教宗若望保禄二世从卡巴纳图安教区划出来设立的。来源之间的具体日期不一致:一处写 1984 年 7 月 14 日,维基百科信息框写 1984 年 2 月 16 日。
- **安蒂克圣若瑟教区(Diocese of San Jose de Antique):1962 年设立,1982 年升格。** 1962 年 6 月 18 日先设为区域监督区(Territorial Prelature),1982 年 11 月 15 日升格为正式教区。

如果你问的是新埃西哈那个,答案就是 **1984 年**。如果是安蒂克那个,设立是 **1962 年**,升格为教区是 1982 年。

这些年份我只看了搜索结果的摘要,没有打开原网页逐条核对。

Sources:
- [Diocese of San Jose (Nueva Ecija) – Wikipedia](https://en.wikipedia.org/wiki/Diocese_of_San_Jose_(Nueva_Ecija))
- [Diocese of San Jose de Antique – Wikipedia](https://en.wikipedia.org/wiki/Diocese_of_San_Jose_de_Antique)
- [Catholic-Hierarchy: Diocese of San Jose de Antique](https://mail.catholic-hierarchy.org/diocese/dsjda.html)
- [GCatholic](https://gcatholic.org/churches/local/zjos1)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：天主教菲律宾圣若瑟教区 设立 年；Diocese of San Jose in Nueva Ecija established

耗时20.686秒，可见返回19692字节。

回答：

**答案:1984 年。** 教皇若望·保禄二世在 1984 年 2 月 16 日设立该教区,辖区从卡巴纳图安教区划出。同年 7 月 14 日举行了正式的教区成立礼(canonical erection)。

依据的网址:
- https://zh.wikipedia-on-ipfs.org/wiki/%E5%A4%A9%E4%B8%BB%E6%95%99%E8%8F%B2%E5%BE%8B%E5%AE%BE%E5%9C%A3%E8%8B%A5%E7%91%9F%E6%95%99%E5%8C%BA(中文维基百科:1984 年 2 月 16 日设立教区)
- https://www.catholic-hierarchy.org/diocese/dsjos.html(Catholic-Hierarchy:1984 年 2 月 16 日 erected)
- https://en.wikipedia.org/wiki/Diocese_of_San_Jose_%28Nueva_Ecija%29(英文维基百科:1984 年 2 月 16 日设立,同年 7 月 14 日正式成立)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：chinese_simpleqa-1bc3c50e553846dfb9279f08dc440fe0

题目：[CHINESE_SIMPLEQA_QUESTION_WITHHELD]

参考答案：2008

题意质量标记：未标记

### Sonnet + Claude搜索：错误

查询：小冷水堆填区 具特殊科学价值地点 渔农自然护理署 鉴定；Siu Lang Shui Landfill Site of Special Scientific Interest AFCD year identified；小冷水 蝴蝶 越冬 具特殊科学价值地点 年 渔护署 鉴定 屯门；"Siu Lang Shui" SSSI butterfly overwintering site designated Tuen Mun "SSSI" since；小冷水 斑蝶越冬 具特殊科學價值地點 於 年 劃定 維基百科

耗时54.838秒，可见返回13256字节。

回答：

**答案:2009 年**(证据较弱,见下)。

绿色力量(Green Power)的「越冬斑蝶」网页写道,小冷水这个已修复的堆填区在 2009 年被指定为具特殊科学价值地点(SSSI)。它是香港最大的斑蝶越冬地,也是本港唯一为保护越冬斑蝶而设的 SSSI。

- **来源不是官方**:这个年份只有绿色力量(环保团体)这一个出处。我没有找到渔农自然护理署或规划署的原始记录来核实。
- **没有逐字对上提问**:该页说的是「被指定」。我没有查到哪个来源写明是渔护署「鉴定」的。
- **搜索次数**:5 次搜索已用完。

依据网址:
- [Butterfly ‧ Overwintering(绿色力量)](https://butterfly.greenpower.org.hk/eng/butterfly-overwintering)
- [20160301 Danaids c(绿色力量新闻稿,证明小冷水是唯一为越冬斑蝶而设的 SSSI)](https://butterfly.greenpower.org.hk/download/press/20160301_Danaids_c.pdf)
- [LCQ3(政府新闻公报,提到该蝴蝶保护区已列为 SSSI,未给年份)](https://www.info.gov.hk/gia/general/201605/25/P201605250480_print.htm)

Sources:
- [Butterfly ‧ Overwintering](https://butterfly.greenpower.org.hk/eng/butterfly-overwintering)
- [20160301 Danaids c](https://butterfly.greenpower.org.hk/download/press/20160301_Danaids_c.pdf)
- [LCQ3: Setting aside a site at Siu Lang Shui](https://www.info.gov.hk/gia/general/201605/25/P201605250480_print.htm)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：小冷水堆填区 具特殊科学价值地点 渔农自然护理署

耗时14.806秒，可见返回11198字节。

回答：

**答案：2008年。**

小冷水堆填区内约2公顷的土地有斑蝶在此越冬，因此在2008年被渔农自然护理署鉴定为「具特殊科学价值地点」(SSSI)。

依据的网址：
- 维基百科「小冷水堆填区」：https://zh.wikipedia.org/wiki?oldid=77502854&title=%e5%b0%8f%e5%86%b7%e6%b0%b4%e5%a0%86%e5%a1%ab%e5%8d%80
- 明报 Our Lifestyle 报道（2022年7月）：https://ol.mingpao.com/ldy/cultureleisure/culture/20220705/1656958662775/%e5%b0%8f%e5%86%b7%e6%b0%b4%e5%a0%86%e5%a1%ab%e5%8d%80%e8%9b%bb%e8%ae%8a-%e5%b1%af%e9%96%80%e4%bf%9d%e8%82%b2%e6%a8%82%e5%9c%92%e8%aa%98%e8%9d%b4%e8%9d%b6%e9%96%8b%e9%a4%90

这两个来源都写的是2008年。我只搜了1次。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：chinese_simpleqa-419bdcaba9f54bacb8e1323cbfc665d9

题目：[CHINESE_SIMPLEQA_QUESTION_WITHHELD]

参考答案：冲浦启之

题意质量标记：未标记

### Sonnet + Claude搜索：错误

查询：电影《给小桃的信》导演；《给小桃的信》 电影 导演 主演 上映

耗时22.365秒，可见返回3309字节。

回答：

我没能查到《给小桃的信》的导演。搜了两次,结果里都没有这部片子的资料。

- 搜出来的都是别的作品,比如岩井俊二执导的《情书》(Love Letter,1995)和 2026 年的《给阿嬷的情书》。这些与你问的片名无关,我不能拿它们当答案。
- 片名可能不准确,也可能是冷门片,或者是别的译名。

如果你能补充上映年份、主演或原名,我可以再搜。也可以直接到豆瓣或猫眼查。

Sources:
- [Love Letter – Variety](https://variety.com/1995/film/reviews/love-letter-1200442983)
- [中国日报:《给阿嬷的情书》相关报道](https://cn.chinadaily.com.cn/a/202607/25/WS6a6498bda310d709c2fbfaa9.html)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：电影《给小桃的信》导演

耗时9.332秒，可见返回9723字节。

回答：

导演是冲浦启之(沖浦啓之,Hiroyuki Okiura)。他同时是这部片的原案、编剧和分镜。这部片是 Production I.G 制作的日本动画电影,他此前的代表作是《人狼 JIN-ROH》。

依据的网址:
- https://zh.wikipedia.org/zh-sg/%E7%B5%A6%E5%B0%8F%E6%A1%83%E7%9A%84%E4%BF%A1
- https://baike.baidu.com/item/%E7%BB%99%E5%B0%8F%E6%A1%83%E7%9A%84%E4%BF%A1/5689641
- http://www.81.cn/jsdm/2011-07/14/content_5501255.htm

我只搜了 1 次。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：chinese_simpleqa-c095afa6590448e4ba0c31d8b33513e0

题目：[CHINESE_SIMPLEQA_QUESTION_WITHHELD]

参考答案：628

题意质量标记：有（独立AI标记，仍需核实）

### Sonnet + Claude搜索：错误

查询：El Tomatal 2010年人口普查 人口 聚居地；El Tomatal locality population 2010 census；El Tomatal localidad Censo 2010 habitantes；"El Tomatal" Wikipedia census 2010 population；El Tomatal pueblo población 2010 INEGI Guerrero OR Sinaloa OR Nayarit OR "Baja California"

耗时34.688秒，可见返回10648字节。

回答：

我没能确定唯一的答案，因为墨西哥有不止一个叫“埃尔托马塔尔”（El Tomatal）的聚居地。2010年人口普查的数据有两个：

- **格雷罗州 Benito Juárez 市的 El Tomatal：186人**（女86、男100）。
- **瓦哈卡州 Santa María Colotepec 市的 El Tomatal：628人**（女302、男326）。

如果题目指的是 Wikipedia 上的条目，我倾向于格雷罗州的 186 人，但这只是猜测，我没有查到那个条目。这两个数字来自 PueblosAmérica，该站称数据取自 INEGI。我没有对照 INEGI 的原始表格核实。

请告诉我是哪个州，我可以再核对。

Sources:
- [El Tomatal (Benito Juárez, Guerrero)](https://mexico.pueblosamerica.com/i/el-tomatal-2/)
- [El Tomatal (Santa María Colotepec, Oaxaca)](https://mexico.pueblosamerica.com/i/el-tomatal-3/)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：埃尔托马塔尔 聚居地 2010年人口普查 人口；El Tomatal census 2010 population

耗时9.547秒，可见返回34614字节。

回答：

**628 人。**

埃尔托马塔尔（El Tomatal）在墨西哥瓦哈卡州圣玛丽亚科洛特佩克。2010 年人口普查显示总人口为 628 人，其中男性 326 人，女性 302 人，另有 64 人讲土著语言。

依据的网址：
- https://zh.wikipedia.org/zh-sg/%E5%9F%83%E5%B0%94%E6%89%98%E9%A9%AC%E5%A1%94%E5%B0%94（中文维基百科，数据来自墨西哥 INEGI 的 2010 年人口普查）
- https://es.m.wikipedia.org/wiki/El_Tomatal（西班牙语维基百科，同样是 628）
- http://www.citypopulation.de/de/mexico/oaxaca/santa_mar%c3%ada_colotepec/204010018__el_tomatal/（citypopulation.de 引用 INEGI 数据，2010-05-31 的普查数也是 628）

墨西哥还有其他几个也叫 El Tomatal 的地方，比如恰帕斯州的只有 12 人。我这里取的是题目所指的瓦哈卡州那个。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：frames-394

题目：What was the average launch mass of Apollo 11, Apollo 12, and Apollo 13 in kilograms, rounded to the nearest integer?

参考答案：The average launch mass in kilograms rounded to the nearest integer of Apollo 11, Apollo 12, and Apollo 13 is 47,906 kilograms.

题意质量标记：有（独立AI标记，仍需核实）

### Sonnet + Claude搜索：正确

查询：Apollo 11 Apollo 12 Apollo 13 launch mass kg；Apollo 11 wikipedia spacecraft properties launch mass kg；Apollo 13 spacecraft properties "launch mass" lb kg infobox

耗时42.461秒，可见返回6497字节。

回答：

**答案:约 47,906 kg**

依据维基百科各任务信息框里的发射质量:

| 任务 | 发射质量 |
|---|---|
| Apollo 11 | 49,735 kg(109,646 lb) |
| Apollo 12 | 49,915 kg(110,044 lb) |
| Apollo 13 | 44,069 kg(指令服务舱 28,881 kg + 登月舱 15,188 kg) |

计算:(49,735 + 49,915 + 44,069) ÷ 3 = 143,719 ÷ 3 ≈ 47,906.3,四舍五入为 **47,906 kg**。

**口径不一致**:Apollo 13 的 44,069 kg 只是指令服务舱加登月舱之和。Apollo 11 和 12 的数值更高,可能还包含适配器、逃逸塔等部件,不过这是我的推测,来源里没有明说。如果三个任务都按指令服务舱加登月舱计算,结果会不同。Apollo 11 的这两部分合计约 43,947 kg,Apollo 12 我没有查到对应分项。

Sources:
- [Apollo 11 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_11)
- [Apollo 12 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_12)
- [Apollo 13 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_13)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：错误

查询：Apollo 11 Apollo 12 Apollo 13 launch mass kg total liftoff mass spacecraft；Apollo 13 launch mass kg Wikipedia；Apollo 11 Saturn V SA-506 "including the spacecraft" rocket weighed kilograms; Apollo 12 SA-507 weighed kilograms

耗时22.205秒，可见返回47030字节。

回答：

**约 2,944,534 kg**,这是整个 Saturn V 加飞船的点火质量。这个数是我按下面的数据算的,精确到个位可能差 1 kg 左右。

依据 Boeing 整理的 Saturn V 点火质量表(磅):

| 任务 | 点火质量 |
|---|---|
| Apollo 11 | 6,484,280 lb |
| Apollo 12 | 6,484,620 lb |
| Apollo 13 | 6,505,857 lb |

三者平均约 6,491,586 lb,按 1 lb = 0.45359237 kg 换算,得 2,944,534 kg。

数据来源:
- http://www.boeing.com/defense-space/space/apollo11/docs/50th_Anniversary.pdf

有两点会影响结果:
- **Apollo 13 的数值有出入**:英文维基写 6,501,733 lb(2,949,136 kg),比 Boeing 的表低一点。如果用维基的数,平均值约为 2,943,000 kg 出头。维基的出处是 https://en.wikipedia.org/wiki/Apollo_13
- **“launch mass”可能指别的东西**:如果题目指的是飞船本身(CSM 加 LM,不含火箭),Boeing 表里的飞船重量是 96,715、96,812 和 96,964 lb,平均约 43,922 kg。这个数我只算了大概,没有细核。

我没有找到题目所指的确切口径,上面的答案按整个发射台上的火箭加飞船来算。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A / B：news-007

题目：Who authored Google’s October 15, 2026 post titled “More ways to connect with the web from Search”?

参考答案：Hema Budaraju

题意质量标记：未标记

### Sonnet + Claude搜索：错误

查询：Google "More ways to connect with the web from Search" October 15, 2026；blog.google "More ways to connect with the web from Search"；"AI Mode and AI Overviews updates to explore the web" Google blog author

耗时28.188秒，可见返回7911字节。

回答：

我没能查到作者。3 次搜索都没找到标题为 “More ways to connect with the web from Search”、日期为 2026 年 10 月 15 日的那篇文章,也没有任何页面给出它的署名。

- 搜索结果里,这个标题看起来更像 Google Search 博客的系列栏目名,有好几篇文章都挂在这个名下,不是某一篇文章的标题。
- 最接近的一篇是 [AI Mode and AI Overviews updates to explore the web](https://blog.google/products-and-platforms/products/search/updates-ai-mode-overviews-explore-web/)。搜索摘要说它大约发布于 4 天前,时间上与 10 月 15 日吻合,但我没打开原页面,所以无法确认它就是你要找的文章,也看不到署名。
- 搜索结果里出现过 Robby Stein(Google Search 产品副总裁),但没有任何一条把他和这篇文章联系起来。我不能把他当作答案。

要确认作者,最直接的办法是打开上面那篇文章,看页面顶部的署名。你也可以到 [Google Search 官方博客](https://blog.google/products/search/)里按日期找。

Sources:
- [AI Mode and AI Overviews updates to explore the web](https://blog.google/products-and-platforms/products/search/updates-ai-mode-overviews-explore-web/)
- [Official Google Search news and updates](https://blog.google/products/search/)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Sonnet + DeepSeek搜索：正确

查询：Google "More ways to connect with the web from Search" October 15, 2026；Hema Budaraju "More ways to connect with the web from Search" blog.google

耗时18.364秒，可见返回86358字节。

回答：

作者是 **Hema Budaraju**,Google 产品管理副总裁(VP, Product Management)。

依据:
- Google 官方博客原文,署名为 Hema Budaraju:https://blog.google/products-and-platforms/products/search/updates-ai-mode-overviews-explore-web/
- Search Engine Journal 的报道也写明由她撰写:https://www.searchenginejournal.com/google-inline-links-higher-ai-search-responses/593089/
- PPC Land 的分析文章也一致:https://ppc.land/google-pushes-links-higher-in-ai-answers-as-preferred-sources-use-rises-7x/

补充一点:博客页面本身标注的发布时间是 10 月 14 日(UTC),多家媒体按 10 月 15 日报道。这不影响作者是谁。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A_prime / B_prime：simpleqa_verified-1129

题目：What is the length in meters of the TCG Yavuz (F240) ship of the Turkish Navy?

参考答案：110.50 m (acceptable range: anything between 109.39 and 111.61 m)

题意质量标记：未标记

### Opus + Claude搜索：正确

查询：TCG Yavuz F240 length meters

耗时12.097秒，可见返回1804字节。

回答：

答案：TCG Yavuz (F240) 全长约 **110.5 米**（362.5 英尺）。

只搜了 1 次。维基百科的数据框和 Navypedia 给的都是全长 110.5 米。Navypedia 另外列了垂线间长 102.2 米，口径不同。Seaforces 写的是 115.5 米，和其他来源对不上，应该是写错了，或者用的是别的量法。

来源：
- [TCG Yavuz (F 240) – Wikipedia](https://en.wikipedia.org/wiki/TCG_Yavuz_(F_240))
- [Yavuz class – Navypedia](https://navypedia.org/ships/turkey/tu_es_yavuz.htm)
- [Yavuz class – Seaforces](https://www.seaforces.org/marint/Turkish-Navy/Frigates/Yavuz-class.htm)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Opus + DeepSeek搜索：错误

查询：TCG Yavuz F240 frigate length meters

耗时15.478秒，可见返回9776字节。

回答：

**答案：115.5 米**，这是维基百科和 Wikidata 给出的数字。

不同来源说法不一：

- **115.5 m**：土耳其语维基百科（Yavuz 级护卫舰）、维基共享资源 TCG Yavuz (F-240) 分类页（数据来自 Wikidata）、shipshub.com。shipshub 还写了水线长 110.5 m。
- **111 m（全长）**：TRB 收录的 1995 年设计论文《THE MEKO 200 T FRIGATE TCG YAVUZ》和 GlobalSecurity 的规格表。这两处的水线长分别是 102.2 m 和 102 m。
- **110.5 m**：devrimyaylali.com 和 shipspotting.com。

这道题很可能以维基百科为准，所以答 115.5 m。如果按造船方的设计资料算全长，是 111 m。

依据网址：
- https://tr.wikipedia.org/wiki/Yavuz_s%C4%B1n%C4%B1f%C4%B1_f%C4%B1rkateyn?oldid=17907140
- https://commons.wikimedia.org/wiki/Category:TCG_Yavuz_(F-240)
- https://shipshub.com/ships/113-1.html
- https://trid.trb.org/view/431765 （111 m 的出处）

只搜了 1 次。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

## A_prime / B_prime：frames-394

题目：What was the average launch mass of Apollo 11, Apollo 12, and Apollo 13 in kilograms, rounded to the nearest integer?

参考答案：The average launch mass in kilograms rounded to the nearest integer of Apollo 11, Apollo 12, and Apollo 13 is 47,906 kilograms.

题意质量标记：有（独立AI标记，仍需核实）

### Opus + Claude搜索：正确

查询：Apollo 11 launch mass kg Wikipedia；Apollo 12 launch mass kg Wikipedia；Apollo 13 launch mass kg Wikipedia

耗时22.474秒，可见返回6320字节。

回答：

**答案：约 47,906 kg**

我用的是英文维基百科信息框里每次任务飞船的"launch mass"（发射质量）。这个数字是飞船本身（指令服务舱加登月舱）的质量，不含土星五号火箭：

- Apollo 11：49,735 kg
- Apollo 12：49,915 kg
- Apollo 13：44,069 kg（指令服务舱 28,881 kg + 登月舱 15,188 kg）

(49,735 + 49,915 + 44,069) / 3 = 143,719 / 3 ≈ 47,906.33，四舍五入是 **47,906 kg**。

各来源的数字对不上，所以这个答案不太确定：
- Apollo 13 的数字比另外两次低了约 5,700 kg，统计口径可能不一样，但维基百科没说是不是。
- 简明英文维基和一些旧镜像给的是另一组数：45,702 / 45,870 / 45,931 kg。用这组算，平均是 **45,834 kg**。
- 如果题目问的是整枚土星五号火箭加满燃料的质量，那是另一个量，大约 290 万 kg。

我搜了 3 次。

Sources:
- [Apollo 11 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_11)
- [Apollo 12 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_12)
- [Apollo 13 – Wikipedia](https://en.wikipedia.org/wiki/Apollo_13)
- [Apollo 11 – Simple Wikipedia](https://simple.wikipedia.com/wiki/Apollo_11)
- [Apollo 13 – Simple Wikipedia](https://simple.wikipedia.com/wiki/Apollo_13)
- [Next Spaceflight – Apollo 12](https://api.nextspaceflight.com/launches/details/194)
- [NASA Apollo 13 Flight Journal](https://www.nasa.gov/history/afj/ap13fj/01launch_ascent.html)

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。

### Opus + DeepSeek搜索：错误

查询：Apollo 11 launch mass kg Wikipedia spacecraft；Apollo 12 launch mass kg Wikipedia；Apollo 13 launch mass kg Wikipedia；Apollo 13 "launch mass" pounds kg infobox 45,931；Apollo 11 "launch mass" "100,756 pounds" 45,702 kg

耗时31.982秒，可见返回121344字节。

回答：

大约 **49,886 kg**。Apollo 13 那个数没在搜索结果里查到，所以这个答案不算完全确认。

**每次任务的数**（整艘飞船在发射时的质量，含发射逃逸系统和登月舱适配器，不含土星五号火箭）：

| 任务 | 发射质量 | 出处 |
|---|---|---|
| Apollo 11 | 109,646 lb（49,735 kg） | Apollo 12 词条里有一句对比（见下）；Wikimedia Commons 给的是 49,734.6 kg |
| Apollo 12 | 110,044 lb（49,915 kg） | 英文 Wikipedia Apollo 12 词条；Commons 给的是 49,915.12 kg |
| Apollo 13 | 110,252 lb（约 50,009 kg） | **没查到**。这是我凭记忆写的，来自英文 Wikipedia 信息框和 Orloff 的 NASA 统计表 |

**算法**：三次合计 329,942 lb，平均 109,980.7 lb，换算成 **49,886 kg**。如果先把每个数四舍五入到整千克再平均，得 49,887 kg。

**要注意两点**：
- Apollo 13 的数我没核实。它变一点，平均值就跟着变。
- 还有一种算法不把发射逃逸系统和适配器算进去，旧版 Wikipedia 用的就是这种。按它算，Apollo 11 是 45,702 kg，Apollo 12 是 45,870 kg，平均值会低大约 4 吨。Apollo 13 按这种算法的数也没查到。

**依据的网址**：
- https://browse.library.kiwix.org/content/wikipedia_en_all_maxi/Apollo_12 （原文："the spacecraft weighed 110,044 pounds (49,915 kg), up from 109,646 pounds (49,735 kg) on Apollo 11"）
- https://commons.wikimedia.org/wiki/Category:Apollo_11 （49,734.6 kg）
- https://commons.m.wikimedia.org/wiki/Category:Apollo_12 （49,915.12 kg）
- 另一种算法的数：https://web.archive.org/web/20230226161855/https://simple.wikipedia.org/wiki/Apollo_11 （Apollo 11 是 45,702 kg）；https://si.wikipedia.org/wiki/Apollo_12 （Apollo 12 是 45,870 kg）

5 次搜索已经用完。

原始记录（材料保留于本地）；工具审计目录（材料保留于本地）。
