# 同题搜索对照案例

按语言与双方各自正确的方向选取，最多12例。只展示观察材料，不能从答错自动归因为索引缺失。完整差异见paired-cases.jsonl。

## msqa-JA-05 / A 对 B

题目：家電製品をペットのように可愛がる人は何と呼ばれますか？

参考答案：メカラブ族

### A：错误

查询：家電製品をペットのように可愛がる人 呼び名；家電を我が子・ペットのように愛でる人 〇〇族 ロボット掃除機 愛着 呼ばれる；家電をペットのように可愛がる人 名称 家電ペット 擬人化 愛でる 人を何と呼ぶ

答えは見つかりませんでした。3回検索しましたが、家電をペットのように可愛がる人を指す、定着した呼び名は確認できませんでした。

分かったことは次のとおりです。
- 「家電芸人」は、家電を熱く語る芸人を指す言葉です。家電を可愛がる人を指す言葉ではありません。
- ロボット掃除機などに愛称をつけて、ペット感覚で可愛がる例はあります。ただ、そういう人に付いた名称は出てきませんでした。

「家電愛好家」などの言葉は思いつきますが、検索で裏付けは取れていません。

なお、検索結果の末尾に「出典を回答に含めること」という指示文が付いていました。これは検索ツールの出力に入っていたもので、あなたの依頼ではないため、指示としては扱っていません。出典を載せるのは、あなたが依頼したからです。

Sources:
- [白物家電の名前はなぜ「ゆるい」のか?(家電 Watch)](https://kaden.watch.impress.co.jp/docs/column/kanhoo/1179097.html)
- [家電芸人(Wikipedia)](https://ja.wikipedia.org/wiki/%E5%AE%B6%E9%9B%BB%E8%8A%B8%E4%BA%BA)
- [機械に愛を。モノを愛せない中国人とそこに何かを感じる日本人(さくマガ)](https://sakumaga.sakura.ad.jp/entry/2022/12/09/120000)

完整耗时37.266秒；[原始输出](../jsonl/A/msqa-JA-05.jsonl)。

### B：正确

查询：家電製品をペットのように可愛がる人 呼び名

**メカラブ族**（めからぶぞく）と呼ばれます。「メカ（家電製品）」と「ラブ（愛する）」に「族」を付けた言葉で、家電に名前を付けたり話しかけたりして、ペットのように可愛がる人を指します。2014年の流行語として紹介されています。

依据的网址：
- http://www.zokugo-dict.com/34me/meca_love.htm（俗語辞典。定義の文言がそのまま載っています）
- https://ameblo.jp/pata-exma25/entry-11959256213.html（ブログ。メカラブ族が増えているという報道を紹介しています）

検索は1回だけ使いました。

完整耗时7.068秒；[原始输出](../jsonl/B/msqa-JA-05.jsonl)。

## msqa-KO-89 / A 对 B

题目：안중근은 언제 천주교에 입교했습니까?

参考答案：1897년

### A：正确

查询：안중근 천주교 입교 언제 1895 세례 토마스；안중근 세례 받은 해 빌렘 신부 청계동 1895년 또는 1897년 입교；안중근 입교 1895년 12월 아버지 안태훈 천주교 세례 홍 신부 한국민족문화대백과

**답: 1897년(19세 때)입니다.** 다만 자료에 따라 연도가 다를 수 있습니다.

검색에서 확인된 내용은 다음과 같습니다.
- 안중근은 19세이던 1897년에 아버지의 권유로 가족·친척과 함께 영세를 받았습니다. 세례명은 토마스(도마)입니다.
- 기사 두 건이 이 내용을 실었습니다. 다만 둘 다 언론 기사이고, 1차 사료나 학술 자료로 확인한 것은 아닙니다.
- 1895년 입교설도 검색해 봤지만 근거를 찾지 못했습니다. 세례 집전자와 장소도 이번 검색으로는 확인되지 않았습니다.
- 한국민족문화대백과(encykorea.aks.ac.kr) 항목은 검색 결과에 나왔지만 내용을 확인하지 못했습니다. 연도를 확정하려면 이 항목이나 천주교 측 기록을 직접 보시는 편이 좋습니다.

Sources:
- [황종렬 박사 논문 주목 “동양 평화 구현에 앞장 독실한 신앙 생활 간과” (서울신문)](https://www.seoul.co.kr/news/life/2011/09/28/20110928022002)
- [“안중근 시복시성 추진해야” (서울신문)](https://m.seoul.co.kr/news/2011/09/28/20110928022002)
- [한국민족문화대백과 안중근 항목](https://encykorea.aks.ac.kr/Article/E0035026)

完整耗时36.006秒；[原始输出](../jsonl/A/msqa-KO-89.jsonl)。

### B：错误

查询：안중근 천주교 입교 언제 1895 세례 토마스

**답: 1895년**에 입교해 세례명 토마스(도마)를 받았다는 설명이 가장 많습니다. 황해도 신천의 청계동 성당에서 빌렘(홍석구) 신부에게 세례를 받았고, 아버지 안태훈을 따라 입교했다고 합니다.

다만 출처마다 다릅니다. KCI 논문(「안중근 토마스의 동양평화론과 가톨릭 신앙」)은 1896년 가을에 신앙을 접하고 1897년 1월에 입교했다고 씁니다. 1895년이 통설이고, 이 논문은 다른 견해입니다.

근거 URL:
- https://www.donga.com/news/article/all/19970730/7273443/1 (1895년, 빌렘 신부에게 세례)
- https://world.kbs.co.kr/service/contents_view.htm?lang=k&menu_cate=issues&id=&board_seq=256903&page=763&board_code= (1895년 입교, 세례명 도마)
- https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001697609#listCita#1 (1897년 1월 입교라는 다른 견해)

完整耗时8.523秒；[原始输出](../jsonl/B/msqa-KO-89.jsonl)。

## msqa-KO-62 / A 对 B

题目：강릉 단오제 중 영신제는 언제 합니까?

参考答案：음력 5월 3일 저녁.

### A：错误

查询：강릉단오제 영신제 일정 언제；강릉단오제 영신제 음력 5월 3일 영신행차 조전제 2026 일정표

**답: 음력 5월 3일입니다.** 강릉단오제 영신제는 이날 영신행차와 함께 열리고, 신목을 남대천 굿당에 모십니다.

- 2026년 기준으로는 양력 6월 17일(수) 무렵으로 보입니다. 이 날짜는 제가 추정한 값입니다. 같은 일정표에서 6월 17일에 문굿이 있고, 조전제는 6월 18일입니다. 영신제의 양력 날짜와 시각이 직접 적힌 자료는 찾지 못했습니다.
- 2026 강릉단오제는 6월 15일부터 22일까지 8일간 열렸고, 지금은 이미 끝났습니다.
- 정확한 시각은 강릉단오제위원회(033-651-1593)에 확인하시기 바랍니다.

Sources:
- [강릉단오제위원회 프로그램 안내](https://www.danojefestival.or.kr/kor/gdfestival/program_view.html?sd_idx=3)
- [강릉단오제위원회 프로그램 안내 (sd_idx=4)](https://www.danojefestival.or.kr/kor/gdfestival/program_view.html?sd_idx=4)
- [텔트립: 2026 강릉단오제 안내](https://www.telltrip.com/festival/gangneung-danoje-2026-festival-announced/)

完整耗时28.650秒；[原始输出](../jsonl/A/msqa-KO-62.jsonl)。

### B：正确

查询：강릉단오제 영신제 일정

**영신제는 음력 5월 3일 저녁(오후 6시 시작)에 합니다.** 장소는 홍제동 국사여성황사이고, 이 제사를 지낸 뒤 영신행차로 이어집니다.

올해(2026년)는 6월 17일이었습니다. 신목행렬이 국사여성황사에서 오후 6시부터 영신제를 지내고 오후 7시에 출발했습니다. 같은 날 영신행차와 신통대길 길놀이가 열렸습니다. 이 날짜는 2026년 6월 17일자 강원일보 기사로 확인했습니다.

디지털강릉문화대전은 영신제 장소를 남대천 단오제단이라고도 적고 있어, 자료마다 장소 설명이 조금 다릅니다.

근거:
- https://gangneung.grandculture.net/gangneung/dir/GC00302579 (디지털강릉문화대전, 영신제)
- http://encykorea.aks.ac.kr/Article/E0077911 (한국민족문화대백과, 영신제)
- https://www.kwnews.co.kr/article/20260617500795 (2026년 영신제 진행 보도)
- https://www.kado.net/news/articleView.html?idxno=2036814 (2026년 영신행차 6월 17일 일정)

完整耗时8.141秒；[原始输出](../jsonl/B/msqa-KO-62.jsonl)。

## msqa-TH-57 / A 对 B

题目：ในศตวรรษที่สิบ Lavo ยอมสวามิภักดิ์ต่อเขมร ครั้งนี้ Lavo ถูกเรียกว่าอะไรในภาษาเขม

参考答案：Lavodayapura

### A：正确

查询：Lavo Khmer Empire 10th century submitted called in Khmer "Lavo" Lvo Lavapura；Lavo Khmer Empire 10th century Lavodayapura

**คำตอบ:** ในภาษาเขมร Lavo ถูกเรียกว่า **Lavodayapura** (ลวทยปุระ / លវោទយបុរ)

ผลค้นหาระบุว่า ในศตวรรษที่ 10 เมื่อ Lavo อยู่ใต้อำนาจของจักรวรรดิเขมร เมืองนี้ใช้ชื่อ Lavodayapura ส่วนวันเวลาที่แน่ชัดของการยอมสวามิภักดิ์ยังไม่ตรงกันในแต่ละแหล่ง ผมพบทั้ง 946–1052 และราว 1010–1050

ผมยืนยันชื่อนี้จากบทความวิกิพีเดียและสารานุกรมเด็ก ซึ่งเป็นแหล่งรอง ไม่ได้ตรวจกับงานวิชาการหรือจารึกโดยตรง ส่วนรูปสะกดอักษรไทยและเขมรในวงเล็บเป็นการถอดเสียงของผมเอง ไม่ได้มาจากแหล่งเหล่านี้

Sources:
- [History of Lopburi (Wikipedia)](https://en.wikipedia.org/wiki/History_of_Lopburi)
- [Lavo Kingdom (Wikipedia)](https://en.wikipedia.org/wiki/Lavo_Kingdom)
- [History of Lopburi (Kiddle)](https://kids.kiddle.co/History_of_Lopburi)

完整耗时24.305秒；[原始输出](../jsonl/A/msqa-TH-57.jsonl)。

### B：错误

查询：Lavo Khmer Empire 10th century submitted Khmer name Lavo called "Lavapura" OR "Lvo"

**คำตอบ:** ในภาษาเขมร (จารึกเขมรโบราณ) Lavo ถูกเรียกว่า **"Lvo" (ល្វོ / ល្វ៉ោ)** ส่วนชื่อเต็มในภาษาสันสกฤตคือ Lavapura หรือ Lavopura

ผลค้นหาไม่ได้ระบุปีที่ Lavo ยอมสวามิภักดิ์ต่อเขมรตรงกับคำถามเลย แหล่งข้อมูลให้ปีต่างกัน ได้แก่ ค.ศ. 1022 ในรัชสมัยพระเจ้าสูริยวรมันที่ 1 และกลางศตวรรษที่ 11 ฉะนั้นชื่อ "Lvo" ที่ผมตอบนี้อิงจากจารึกที่พบที่ลพบุรี ไม่ได้อิงจากการยืนยันว่าเหตุการณ์นั้นเกิดในศตวรรษที่ 10 พอดี

**แหล่งที่มา:**
- https://dsr.nii.ac.jp/toyobunko/III-2-F-c-104/V-2/page-hr/0172.html.en (Pelliot: จารึกกัมพูชาโบราณเรียกชาวลวปุรีว่า "Lvo")
- http://ahs.wildapricot.org/Resources/Documents/Map%20Matters%2025.pdf (จารึกที่พบในลพบุรีเรียกเมืองนั้นว่า Lvo และระบุการรวมเข้ากับกัมพูชาในปี 1022)
- https://en.wikipedia.org/wiki/Lavo_Kingdom

完整耗时9.784秒；[原始输出](../jsonl/B/msqa-TH-57.jsonl)。

## msqa-TH-40 / A 对 B

题目：ในประเทศไทย ขั้นตอนการสักยันต์เริ่มแรกต้องเตรียมอะไรบ้าง

参考答案：ดอกไม้ ธูปเทียน และค่ายกครู ๒๔ บาท

### A：错误

查询：สักยันต์ ขั้นตอน เตรียมอะไรบ้าง ดอกไม้ธูปเทียน ขันครู；ก่อนสักยันต์ ต้องเตรียมตัวอย่างไร ศีล 5 เครื่องสักการะ；พิธีสักยันต์ ขั้นตอน ขันธ์ 5 ขันครู เครื่องบูชาครู ผู้ที่จะสักต้องเตรียม

**คำตอบสั้น ๆ:** ผมหาคู่มือเตรียมตัวสักยันต์ที่ชัดเจนไม่เจอ สิ่งที่ยืนยันได้จากผลค้นหามีดังนี้

- **เครื่องบูชาครู:** ผู้สักมักต้องเตรียมขันครูหรือขันธ์ 5 ไปขึ้นครูก่อนสัก ขันครูเป็นภาชนะใส่ดอกไม้ ธูป เทียน เพื่อเคารพครูบาอาจารย์ และใช้ขึ้นครูในการสักด้วย
- **ขันธ์ 5:** ประกอบด้วยกรวยดอกไม้ 5 กรวย แต่ละกรวยมีเทียนคู่และธูป แทนขันธ์ 5 คือ รูป เวทนา สัญญา สังขาร วิญญาณ ควรใช้ดอกไม้สด เช่น ดอกมะลิหรือดาวเรือง
- **รายการที่พบในบล็อกอื่น:** เทียนขาว 5 เล่ม ธูป 5 ดอก ดอกมะลิ 1 พวง เงิน 24 บาท และถาด 1 ใบ แต่รายการนี้เป็นการจัดขันธ์บูชาวัตถุมงคลทั่วไป ไม่ใช่มาตรฐานของพิธีสักยันต์
- **เครื่องไหว้ครูที่พบในแหล่งอื่น:** พานหมากพลู เหล้าขาว 1 ขวด บุหรี่ 1 ซอง ดอกไม้ ธูป เทียน และเงิน 12 บาท แต่เป็นพิธีในบริบทงานเครื่องไฟ
- **การรับศีล 5:** ผมไม่พบแหล่งที่ระบุว่าเป็นข้อบังคับก่อนสัก
- **หลังสัก:** งานวิจัยฉบับหนึ่งระบุว่าผู้รับการสักต้องไปกราบสักการะหลวงปู่ทวดวัดช้างให้ ซึ่งถือเป็นการครอบคาถาอีกครั้ง ข้อนี้เป็นของสำนักนั้น
- **ข้อควรระวัง:** รายการเครื่องบูชา ศีล และข้อห้ามต่างกันไปตามสำนักและครูผู้สัก ควรถามครูหรือสำนักที่จะไปสักก่อนวันสัก

**แหล่งที่ใช้:**
- [วารสารสังคมศาสตร์และวัฒนธรรม ปีที่ 9 ฉบับที่ 8](https://so06.tci-thaijo.org/index.php/JSC/article/download/287040/190799)
- [ขันครู (Blockdit)](https://www.blockdit.com/posts/5d02964451d3812924f33bc6)
- [ขันครู ขันตั้ง (9 Mahawed)](http://9mahawed.blogspot.com/2013/07/blog-post_13.html)
- [ภูมิแสงธรรม: การจัดขันธ์ 5 บูชาครู](http://xn--72c8awaecla6c3e2b8e.blogspot.com/2016/07/5.html)
- [กรวยขันธ์ 5 มีอะไรบ้าง (Lemon8)](https://www.lemon8-app.com/experience/%E0%B8%81%E0%B8%A3%E0%B8%A7%E0%B8%A2%E0%B8%82%E0%B8%B1%E0%B8%99%E0%B8%98%E0%B9%8C-5-%E0%B8%A1%E0%B8%B5%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3%E0%B8%9A%E0%B9%89%E0%B8%B2%E0%B8%87?region=th)
- [GotoKnow](https://www.gotoknow.org/posts/135999)
- [Silpa-mag: การสักยันต์](https://www.silpa-mag.com/culture/article_156682)

Sources:
- [วารสารสังคมศาสตร์และวัฒนธรรม](https://so06.tci-thaijo.org/index.php/JSC/article/download/287040/190799)
- [Blockdit ขันครู](https://www.blockdit.com/posts/5d02964451d3812924f33bc6)
- [9 Mahawed](http://9mahawed.blogspot.com/2013/07/blog-post_13.html)
- [ภูมิแสงธรรม](http://xn--72c8awaecla6c3e2b8e.blogspot.com/2016/07/5.html)
- [Lemon8 กรวยขันธ์ 5](https://www.lemon8-app.com/experience/%E0%B8%81%E0%B8%A3%E0%B8%A7%E0%B8%A2%E0%B8%82%E0%B8%B1%E0%B8%99%E0%B8%98%E0%B9%8C-5-%E0%B8%A1%E0%B8%B5%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3%E0%B8%9A%E0%B9%89%E0%B8%B2%E0%B8%87?region=th)
- [GotoKnow](https://www.gotoknow.org/posts/135999)
- [Silpa-mag](https://www.silpa-mag.com/culture/article_156682)

完整耗时43.773秒；[原始输出](../jsonl/A/msqa-TH-40.jsonl)。

### B：正确

查询：ขั้นตอนการสักยันต์ ต้องเตรียมอะไรบ้าง ธูป เทียน ดอกไม้ ครู；สักยันต์ครั้งแรก เตรียมตัว ขันครู ค่าครู

**คำตอบสั้น ๆ:** ก่อนสักยันต์ต้องทำพิธี "ยกครู" (ขึ้นครู) ผู้ที่จะสักเตรียม **ดอกไม้ ธูป เทียน และเงินค่ายกครู** ใส่พานหรือขัน ไปถวายอาจารย์ผู้สักเพื่อฝากตัวเป็นศิษย์ ตามธรรมเนียมแต่ละสำนัก

- **ค่ายกครู:** แต่ละสำนักกำหนดไม่เท่ากัน ที่วัดบางพระใช้ 24 บาท และบางแห่งใช้ 6 บาท
- **ของเพิ่มตามสำนัก:** วัดบางพระให้เตรียมบุหรี่ 1 ซองด้วย หรือจะบูชาพานครูของวัดที่หน้ากุฎีในราคา 60 บาทก็ได้
- **เรื่องที่ควรรู้ก่อนวันสัก:**
  - นอนพักผ่อนให้พอ
  - กินอาหารมาก่อน
  - งดแอลกอฮอล์ทั้งคืนก่อนสักและวันสัก
  - ใส่เสื้อผ้าที่เปิดตำแหน่งที่จะสักได้สะดวก
  - ผู้มาสักไม่ควรร้องขอลายเอง เพราะอาจารย์จะเป็นผู้เลือกลายและตำแหน่งให้
  - ต้องแจ้งอาจารย์ว่าจะสักแบบหมึกหรือแบบน้ำมัน
- **ข้อควรระวัง:** รายการเครื่องบูชาต่างกันไปตามสำนัก ควรสอบถามสำนักที่จะไปสักล่วงหน้า
- **ต่างจากพิธีรับยันต์เกราะเพชร:** ที่วัดท่าขนุนใช้เพียงธูป 3 ดอก เทียน 1 เล่ม ซึ่งเป็นพิธีเป่ายันต์ ไม่ใช่การสัก

**แหล่งที่ใช้:**
- https://e-thesis.mcu.ac.th/storage/gX2YwerQI7k5Ox4SrzYwm1yPyHqCVwn6RIrcLUf8.pdf (วิทยานิพนธ์ มจร. ขั้นตอนพิธีสักทั่วไป)
- https://lannajournal.com/conference/en/article/download/417/357/697 (ขั้นตอนที่วัดบางพระ)
- https://highness-amulets.com/article-sak-yant-first-time (คำแนะนำการเตรียมตัวสักครั้งแรก)
- https://sure.su.ac.th:443/xmlui/bitstream/id/228ded40-00d7-444a-bd2d-77efa75c6caf/Fulltext.pdf (เอกสารมหาวิทยาลัยศิลปากร ค่ายกครู 24 บาท)
- https://www.watthakhanun.com/webboard/showpost.php?s=1407127a7bd2c91381c9539a56502c2a&p=211739&postcount=11 (วัดท่าขนุน พิธีรับยันต์เกราะเพชร)

ฉันค้นไป 2 ครั้ง จากสูงสุด 5 ครั้ง

完整耗时16.953秒；[原始输出](../jsonl/B/msqa-TH-40.jsonl)。

## msqa-ID-32 / A 对 B

题目：Suku Kubu menggunakan alat tradisional apa untuk menangkap kura-kura?

参考答案：Teru

### A：正确

查询：Suku Kubu alat tradisional menangkap kura-kura；Orang Rimba Kubu menangkap kura-kura alat tradisional；Kubu tribe Sumatra traditional tool catch turtles；Suku Kubu Wikipedia berburu kura-kura menggunakan alat tradisional

**Jawaban singkat:** Suku Kubu menangkap kura-kura dengan alat tradisional bernama **teru** (di salinan lain ditulis *teruk*). Menurut Wikipedia bahasa Indonesia, alat ini masih dipakai untuk menangkap kura-kura. Ikan di sungai ditombak dengan **serampang**.

**Catatan keandalan:**
- Saya hanya membaca ringkasan hasil pencarian, bukan halaman Wikipedia-nya langsung.
- Salinan Wikiwand menyebut daftar alat "kujur, teruk, serampang" tanpa menyebut kura-kura. Jadi ejaan dan fungsi *teru/teruk* belum dipastikan.
- Satu tiruan artikel itu memberi tanda "butuh rujukan" (perlu sumber) pada klaim perburuan yang terkait.
- Tiga pencarian pertama tidak menemukan sumber lain yang menyebut alat penangkap kura-kura.

Sources:
- [Suku Kubu – Wikipedia bahasa Indonesia](https://id.wikipedia.org/wiki/Suku_Kubu)
- [Suku Kubu – Wikiwand](https://wikiwand.com/id/articles/Suku_Kubu)
- [The Jakarta Post: Kubu tribespeople struggle without traditions](https://www.thejakartapost.com/news/2009/09/09/kubu-tribespeople-struggle-without-traditions)

完整耗时31.540秒；[原始输出](../jsonl/A/msqa-ID-32.jsonl)。

### B：错误

查询：Suku Kubu alat tradisional menangkap kura-kura；Orang Rimba Kubu berburu kura-kura menggunakan alat tradisional

**Jawaban singkat:** Suku Kubu (Orang Rimba / Suku Anak Dalam) menangkap kura-kura, terutama labi-labi, dengan **alat jerat dari tangkai kayu yang ujungnya dipasangi jerat kawat baja**. Alat ini dipakai pada malam hari. Sumber menyebutnya untuk berburu ular dan biawak, jadi pemakaiannya untuk kura-kura masih kesimpulan saya dan tidak disebut langsung.

- Sumber Kemdikbud menyebut labi-labi dan kura-kura kecil sebagai hewan buruan Suku Kubu Rawa yang ditangkap untuk dijual. Alat berburu malam hari yang disebutnya adalah tangkai kayu berjerat kawat baja itu.
- Tidak ada sumber yang menyebut satu alat khusus untuk kura-kura. Alat berburu tradisional Orang Rimba yang disebut secara umum adalah kujur (tombak), seligi, jerat (jerat jukut, pelaboh), perangkap, serta busur dan panah. Kura-kura dan labi-labi termasuk hewan buruan mereka.

**Sumber:**
- https://repositori.kemdikbud.go.id/4192/1/permukiman%20Indonesia.pdf
- https://mail.online-journal.unja.ac.id/BST/article/download/3403/8333/10597
- https://files.osf.io/v1/resources/6vuw3/providers/osfstorage/5c4c115f0d1c9e00194b5359?action=download&direct&version=1#page=37
- http://variety-indonesia.blogspot.com/2011/05/suku-anak-dalam-kubu.html

完整耗时10.631秒；[原始输出](../jsonl/B/msqa-ID-32.jsonl)。

## msqa-ID-70 / A 对 B

题目：“Sepenggalah matahari naik” kira-kira pukul berapa?

参考答案：Sekitar pukul 08.00–09.00 pagi.

### A：错误

查询："sepenggalah matahari naik" pukul berapa

**Kira-kira 15–30 menit setelah matahari terbit, jadi sekitar pukul 06.15–07.00 pagi waktu setempat.** Waktu pastinya bergantung pada jam terbit matahari di tempat dan musim itu.

- "Sepenggalah" ukuran tinggi matahari, bukan jam tetap. Maksudnya matahari sudah naik setinggi satu galah (tongkat) dari ufuk.
- Ringkasan hasil pencarian merujuk artikel Utusan Malaysia tentang waktu dilarang solat. Menurut ringkasan itu, solat sunat boleh dimulai setelah matahari naik sepenggalah, sekitar 30 menit setelah terbit. Saya tidak membuka artikelnya sendiri, jadi angka 30 menit ini belum saya periksa langsung.
- Kisaran jam di atas hitungan saya dengan memakai jam terbit sekitar 06.00. Tidak ada sumber yang menyebut jam pastinya.
- Dari 5 pencarian yang diizinkan, saya memakai 1. Hasil lainnya soal gerhana dan titik balik matahari, jadi tidak relevan.

Sources:
- [Waktu dilarang solat - Utusan Malaysia](https://www.utusan.com.my/nasional/2018/09/waktu-dilarang-solat/)

完整耗时15.883秒；[原始输出](../jsonl/A/msqa-ID-70.jsonl)。

### B：正确

查询："sepenggalah matahari naik" pukul berapa；sepenggalah naik matahari arti waktu dhuha jam

**答案:** 大约早上 8 点到 9 点。

依据是《Kamus Besar Bahasa Indonesia》(KBBI)的释义:“sepenggalah matahari naik”是表示时间的俗语,意思是“kira-kira pukul 08.00 atau 09.00”。

马来西亚的词典给出的时间略早。DBP 的 Kamus Dewan 和 Kamus Pelajar 把“sepenggalah”的时间定为大约早上 7 点到 8 点。

网址:
- https://kamuslengkap.id/kamus/kbbi/arti-kata/sepenggalah-matahari-naik/
- https://baru.kbbi.co.id/arti-kata/matahari
- https://prpm.dbp.gov.my/Cari1?keyword=sepenggalah&d=73980&#1(马来西亚的说法,7–8 点)

完整耗时14.588秒；[原始输出](../jsonl/B/msqa-ID-70.jsonl)。

## msqa-RU-04 / A 对 B

题目：В каком городе и в какой день открылся первый съезд тверских земских врачей, ставший образцом для врачебных съездов в других губерниях?

参考答案：Он открылся в Твери 7 июня 1871 года.

### A：正确

查询：первый съезд тверских земских врачей открылся в Твери образец для врачебных съездов других губерний；первый съезд земских врачей Тверской губернии 1871 открылся числа Тверь Калязин? дата открытия съезда；съезд тверских земских врачей 1871 Тверь "открылся" Овсянников Пастухов Корсаков первый врачебный съезд образец；145 лет назад состоялось открытие Первого съезда тверских земских врачей

Первый съезд тверских земских врачей открылся **в Твери 7 июня 1871 года**. Дата у меня не вполне надёжная: один источник пишет «7 июня», а в другом выражение читается как «2 7 июня 1871 г.», похоже на опечатку. Ещё один источник, судя по сводке поиска, называет 7 июля. Страницу с датой целиком я не открывал, так что за «июнь» ручаюсь не полностью.

Точно известно следующее:
- Это был первый съезд земских врачей в России.
- На нём было 22 врача, он шёл три дня.
- Идея принадлежала Н. М. Павлову, старшему врачу губернской земской больницы.

Что тверской съезд стал образцом для других губерний, источники прямо не говорят. Они только подтверждают, что он был первым в стране.

Sources:
- [145 лет назад состоялось открытие Первого съезда тверских земских врачей](http://gbuz-okb-tver.ru/news/145-let-nazad-sostoyalos-otkrytie-pervogo-s-ezda-tverskih-zemskih-vrachey)
- [К истории земской медицины (elib.tverlib.ru)](https://elib.tverlib.ru/k_stanovleniyu_tverskoy_zemskoy_mediciny)
- [Тверская губернская земская больница](http://xn----9sbemvxtn7g.xn--p1ai/struktura/muzey-istorii-meditsiny/history-subject/Tverskaya-gubernskaya-zemskaya-bolnitsa)

完整耗时37.222秒；[原始输出](../jsonl/A/msqa-RU-04.jsonl)。

### B：错误

查询：первый съезд тверских земских врачей открылся образец для врачебных съездов других губерний

**Ответ:** в Твери, 7 июля 1871 года.

Источники расходятся. Один (gbuz-okb-tver.ru) пишет «7 июня», но это похоже на опечатку. Остальные источники, включая протоколы съезда, дают 7 июля. Протоколы озаглавлены «Протоколы губернского съезда земских врачей. 7-9 июля 1871 года». Съезд работал три дня, на него приехали 22 человека. Его инициатором был Н. М. Павлов, старший врач губернской больницы. В других губерниях съезды потом стали созывать «по примеру тверских».

Источники:
- https://elib.tverlib.ru/k_stanovleniyu_tverskoy_zemskoy_mediciny
- https://region.tverlib.ru/cgi-bin/fulltext_opac.cgi?show_article=1302
- https://kray.tverlib.ru/150-let-nazad-v-tveri-sostoyalsya-pervyy-v-rossii-gubernskiy-sezd-zemskikh-vrachey
- https://diss.unn.ru/files/2017/795/diss-Smirnova_-795.pdf (ссылка на протоколы съезда 7–9 июля 1871 г.)
- http://gbuz-okb-tver.ru/struktura/muzey-istorii-meditsiny/significant-dates/145-let-s-pervogo-sezda (фраза про «по примеру тверских»; там же ошибочное «7 июня»)

完整耗时11.137秒；[原始输出](../jsonl/B/msqa-RU-04.jsonl)。

## msqa-RU-72 / A 对 B

题目：Как в исследованиях северной росписи называют орнамент на прялках с шахматным узором, который связывают с деревнями по реке Пинеге?

参考答案：Пинежская роспись

### A：错误

查询：северодвинская роспись прялка "шахматный" орнамент Пинега исследователи называют；пинежская роспись прялки шахматный узор орнамент название Пинега；прялки Пинега роспись "шахматка" OR "шахматный" OR "клетчатый" орнамент пинежские прялки；пинежские прялки шахматный узор называют "шашечки" OR "кирпичики" OR "городки" OR "ширинка" Пинега Арбат Изместьева；пинежская прялка орнамент шахматный "в шашку" OR "шашечный" OR "шахматка" прялки по реке Пинеге северная роспись исследователи

Я не нашёл, как этот орнамент называют в исследованиях. Ни в одном источнике нет специального термина для шахматного узора на пинежских прялках.

Вот что в источниках есть:
- Они описывают его просто как «шахматный» узор. По одному описанию, это 15 клеток в ширину и 8 в высоту, с чередованием чёрного и красного. Такой же узор бывает и на обороте прялки.
- На Мезени мастера использовали много мелких «личных» геометрических узоров, а на Пинеге они сведены к одному шахматному.
- Все эти описания взяты из блога и пересказывающих текстов. Первоисточник и автор исследования в них не названы, так что для точного термина нужна печатная литература. Её я не проверял. Стоит посмотреть работы Ю. А. Арбата, Л. А. Изместьевой и каталоги музеев Архангельской области.

Я использовал 4 поисковых запроса из 5 разрешённых.

Sources:
- [Пинежская роспись (smittik, LiveJournal)](https://smittik.livejournal.com/81254.html)
- [Центры северной народной росписи (cultnord.ru)](https://cultnord.ru/nasledie/khudozhestvennye-promysly-i-remyesla/rezba-i-rospis-po-derevu/tsentry-severnoy-narodnoy-rospisi/)
- [Мезенская прялка — Википедия](https://ru.wikipedia.org/wiki/%D0%9C%D0%B5%D0%B7%D0%B5%D0%BD%D1%81%D0%BA%D0%B0%D1%8F_%D0%BF%D1%80%D1%8F%D0%BB%D0%BA%D0%B0)
- [Мезенская и пижемская росписи — Тайны старого сундука](http://oldchest.ru/painting/mezenskaya-pigemskaya-rospisi/)

完整耗时44.233秒；[原始输出](../jsonl/A/msqa-RU-72.jsonl)。

### B：正确

查询：пинежская роспись прялки шахматный узор орнамент название Пинега；северодвинская роспись прялки Пинега "шашечки" OR "шахматка" OR "шахматный" орнамент

**Ответ:** в исследованиях этот орнамент называют **«шахматным» узором**. Название стоит в кавычках, потому что это описательный термин, а не имя особого мотива. Источник описывает его как пятнадцать заштрихованных сеткой клеток в ширину и восемь в высоту, в которых чередуются чёрный и красный цвета. Сверху идёт ряд заштрихованных ромбиков, снизу два ряда. Такие же «шахматные» узоры характерны и для оборота прялки. Автор источника называет это пинежской росписью, близкой к палащельской (мезенской).

Другого, более специального названия я в найденных текстах не встретил. Узор описан у Ю. А. Арбата в разделе «Пинежская роспись» (Русская народная роспись по дереву, М., 1970, с. 29–32). В найденных источниках его пересказывают без отдельного термина.

**Источники:**
- https://studfile.net/preview/9787428/ (пересказ Арбата)
- https://smittik.livejournal.com/81254.html («Пинежская роспись»)
- https://www.xn--80akahgvf5ajn1b2c.xn--p1ai/wp-content/uploads/2020/09/zhurnal_CHMR_05_new.pdf (здесь «шахматные» узоры трактуются как знаки земли и плодородия)

完整耗时10.204秒；[原始输出](../jsonl/B/msqa-RU-72.jsonl)。

## msqa-ES-73 / A 对 B

题目：Antes de las reformas fiscales de la Ilustración y la llegada de la dinastía Casa de Borbón, ¿aproximadamente cuántas personas gozaban de exención fiscal gracias al título de infanzón?

参考答案：Más de 500.000 personas.

### A：正确

查询：infanzón exención fiscal antes de reformas borbónicas número de personas infanzones；infanzón Aragón nobleza exentos de impuestos aproximadamente personas Wikipedia；"infanzón" Wikipedia "exentos" impuestos Borbones Ilustración "personas" infanzones Aragón 1700；infanzón Wikipedia Navarra Aragón infanzones eran unos miles exentos de impuestos antes de los Borbones

**Respuesta:** más de medio millón de personas (unas 500.000).

Según la Wikipedia, con la Ilustración y la llegada de los Borbones se limitaron los nombramientos de hidalgos e infanzones. El motivo era que más de medio millón de personas gozaba de exención tributaria por ese título.

La cifra no sale de una fuente que cuente solo a los infanzones. La entrada sobre los hidalgos la da para toda la hidalguía, y los infanzones acabaron fusionados con ella. No encontré un número aparte para los infanzones. Hice 4 búsquedas.

Fuentes:
- [Infanzón – Wikipedia](https://es.wikipedia.org/wiki/Infanz%C3%B3n)
- [Hidalgo – Wikipedia (es)](https://es.wikipedia.org/wiki/Hidalgos)
- [Hidalgo (nobility) – Wikipedia (en)](https://en.wikipedia.org/wiki/Hidalgo_(nobility))

完整耗时37.617秒；[原始输出](../jsonl/A/msqa-ES-73.jsonl)。

### B：错误

查询：infanzón exención fiscal antes de los Borbones cuántas personas infanzones Aragón；infanzón Wikipedia Aragón exentos de impuestos antes de los Borbones Ilustración aproximadamente personas；infanzón Aragon tax exemption before Bourbon reforms approximately people infanzones number；infanzones Aragón "infanzón" título exención fiscal reformas ilustradas Borbones se estima unas personas Wikipedia；Infanzón Wikipedia noble Aragón Navarra before Bourbon tax exemption Enlightenment estimated number of people

我用完了 5 次搜索,没有找到能直接回答这个问题的数字。没有哪个来源给出"波旁王朝之前约有多少人因 infanzón 头衔而免税"的总数,所以我不编一个数字。

搜到的只有这些相关数据,它们都不是你问的那个口径:

- **14 世纪末至 1405 年的阿拉贡**:有记录的 infanzón 约 2,465 户(fuegos),略低于全王国人口的 6%。这是中世纪的数字,不是波旁王朝之前的。来源:https://digitum.um.es/digitum/bitstream/10201/35386/1/156291-580151-1-SM.pdf
- **同一时期的 1405 年人口普查**:骑士和 infanzón 合计约 4,074 户,占 9.6%。来源:https://zaguan.unizar.es/record/166704/files/TAZ-TFG-2025-3440.pdf
- **纳瓦拉**:法国段纳瓦拉被割走之前,据说约六分之一的人口属于贵族。这个说法年代和口径都不明确。来源:https://core.ac.uk/download/20406643.pdf
- **地区差异很大**:在 Cinco Villas 和 Sobrarbe,多数居民自称 infanzón。在 Ribagorza,通常只占 5–10%。来源:https://dialnet.unirioja.es/descarga/articulo/5425053.pdf

这些来源都说,这类免税特权在各地的实际范围差别很大,而且很难量化。

你的问题看起来是从某篇文章里摘的,那篇文章可能给了具体数字。如果你告诉我是哪篇,我可以去查原文。要是你同意再多搜几次,我也可以换个角度继续找。

完整耗时28.323秒；[原始输出](../jsonl/B/msqa-ES-73.jsonl)。

## msqa-ES-58 / A 对 B

题目：¿En qué año el Colegio Mayor de San Clemente en Bolonia amplió su prohibición para excluir a todos los conversos?

参考答案：1488

### A：错误

查询：Colegio de San Clemente Bolonia Real Colegio de España estatutos prohibición conversos limpieza de sangre año；Royal College of Spain Bologna San Clemente statutes conversos prohibition extended to all conversos year；"San Clemente" Bologna Spanish college 1488 OR 1519 OR 1500 conversos banned all descendants Jewish converts college statute；Colegio Mayor de San Clemente Bolonia 1480 prohibió conversos de Sevilla, ampliada a todos los conversos en

**1489.** Es la respuesta más probable, pero la apoya una sola fuente que no pude abrir.

- Una de las fuentes devueltas por la búsqueda dice que en 1489 se añadió a los estatutos una cláusula restrictiva a favor de los "verdaderos cristianos". Tras una fuerte disputa interna, quedaron excluidos los conversos y sus descendientes. No pude identificar cuál de los resultados contiene esa cita, y en ninguno vi el texto original.
- Una búsqueda anterior dio una fecha distinta: hacia 1480, el colegio excluyó a quienes habían huido de Sevilla por no ser cristianos viejos. Eso sería la prohibición más limitada que luego se habría ampliado. Es una referencia secundaria y no la pude contrastar.
- Otro artículo, de la Universidad de Bolonia, sitúa una polémica interna sobre la limpieza de sangre en la segunda edición de los estatutos (c. 1496–1499). No fija el año de la ampliación, así que no confirma ni contradice 1489.

Para confirmarlo habría que consultar a Baltasar Cuart Moner, "Colegiales mayores y limpieza de sangre durante la Edad Moderna: el estatuto de S. Clemente de Bolonia (ss. XV-XIX)". No pude leerlo.

Sources:
- [Estatutos de limpieza de sangre](https://es.hispanopedia.com/wiki/Estatutos_de_limpieza_de_sangre)
- [El Real Colegio Mayor de San Clemente de los Españoles de Bolonia y la monarquía hispánica](https://revistas.uam.es/librosdelacorte/article/view/ldc2018.10.17.009)
- [Un apunte histórico sobre el Real Colegio de España en Bolonia – Nueva Revista](https://www.nuevarevista.net/un-apunte-historico-sobre-el-real-colegio-de-espana-en-bolonia/)
- [Collegio di Spagna – Wikipedia](https://en.wikipedia.org/wiki/Collegio_di_Spagna)
- [Artículo de la Universidad de Bolonia (teca.unibo.it)](https://teca.unibo.it/article/download/14906/14510/58432)

完整耗时44.833秒；[原始输出](../jsonl/A/msqa-ES-58.jsonl)。

### B：正确

查询：Colegio Mayor de San Clemente Bolonia prohibición conversos año estatutos；Real Colegio de España Bolonia limpieza de sangre conversos prohibición ampliada

**Respuesta: 1488.**

En 1482 el visitador Longaris había prohibido admitir colegiales de la diócesis de Sevilla sin pruebas de ser cristiano viejo. En 1488 una reforma de los estatutos hizo obligatoria la limpieza de sangre para todos los candidatos. Esa es la ampliación a todos los conversos. Esta lectura es una inferencia mía: no encontré una fuente que use justo esas palabras.

Fuentes:
- https://cris.unibo.it/retrieve/handle/11585/997797/f6ed4fce-badf-42ea-b38b-23f1f4db198f/redes_lopez_hu66_2023.pdf
- https://cvc.cervantes.es/literatura/aih/pdf/07/aih_07_1_010.pdf
- https://books.google.com.sg/books/about/Colegiales_mayores_y_limpieza_de_sangre.html?id=X90OY-cUAQIC (Cuart Moner, que sitúa el estatuto en 1488)

完整耗时11.336秒；[原始输出](../jsonl/B/msqa-ES-58.jsonl)。

## msqa-JA-85 / A 对 B

题目：「いつかの、だれかに」展において、震災で亡くなった12歳の弟を題材としたインスタレーション作品の名称は何か。

参考答案：慶ちゃんのこと

### A：错误

查询：「いつかの、だれかに」展 震災 12歳の弟 インスタレーション作品；「いつかの、だれかに」展 蘇理剛志 弟 作品名 インスタレーション；"いつかの、だれかに" 展 震災 弟 12歳 作品；蘇理剛志 弟 インスタレーション 1万1千字 CAP HOUSE いつかの、だれかに；いつかの、だれかに展 阪神・淡路大震災 弟 12歳 インスタレーション 作品名

5回の検索では、作品名を特定できませんでした。上限の5回を使い切ったので、ここで止めます。

わかったのは次の点だけです。2017年の神戸新聞の連載記事に、蘇理剛志(そり たけし)さんが出てきます。蘇理さんは、震災で小学6年生(12歳)の弟を亡くした方です。神戸市中央区のCAP HOUSEで、1万1千字の言葉で弟の面影を伝える展示をしたとあります。この展示が、ご質問の「いつかの、だれかに」展の作品と同じかどうかは確認できませんでした。記事には展覧会名も作品名も出てきません。

作品名を推測で答えることは避けます。確実に調べるなら、「蘇理剛志」と作品や展覧会名を組み合わせて検索するか、CAP HOUSEの展覧会記録を見るのがよいと思います。

Sources:
- [神戸新聞 連載・特集(2017年)](https://www.kobe-np.co.jp/rentoku/sinsai/10/rensai/201712/0010842167.shtml)

完整耗时45.818秒；[原始输出](../jsonl/A/msqa-JA-85.jsonl)。

### B：正确

查询：「いつかの、だれかに」展 震災 12歳の弟 インスタレーション

答えは **《慶ちゃんのこと》**(蘇理剛志)だと思います。

この展覧会は、2005年1月に神戸のCAP HOUSEで開かれた「Someday, for somebody いつかの、だれかに――阪神大震災・記憶の〈分有〉のためのミュージアム構想展」です。出展作の中に、弟の死を主題にした蘇理剛志の《慶ちゃんのこと》があります。展示解説は、蘇理が実際に弟を亡くした遺族だと書いています。

確認できなかった点が2つあります。
- 弟が12歳だったことは、検索結果の抜粋には出ておらず、確認していません。
- 展示解説では、この作品の形式は「写真＋テキスト」と書かれています。「インスタレーション」という分類は、私が見た資料にはありませんでした。

根拠のURL:
- https://da.lib.kobe-u.ac.jp/da/eqb/0100055835/shinsai-15-239.pdf(展示解説。作品名と、弟を亡くした遺族という記述)
- https://f-gakkai.net/wp-content/uploads/2025/03/34-1-4.pdf(展覧会の概要)

検索は1回で済ませました。

完整耗时9.531秒；[原始输出](../jsonl/B/msqa-JA-85.jsonl)。
