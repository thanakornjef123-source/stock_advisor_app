# รายงานคุณภาพข้อมูล — SET Raw Data Cleaning

จัดทำจากไฟล์ดิบ 13 ไฟล์ (~145 MB) สำหรับโปรเจกต์แนะนำหุ้นตาม TSI Risk Profile

---

## 1. ผลลัพธ์หลังทำความสะอาด

| ตาราง | จำนวนแถว | จำนวนหลักทรัพย์ | ช่วงข้อมูล |
|---|---|---|---|
| `stock_prices` ราคารายวัน | 1,000,518 | 917 | 2021-01-04 – 2025-12-30 |
| `financials` งบรายไตรมาส | 15,160 | 866 | 2021 – 2026 |
| `news` ข่าว | 284,666 | 25,326 | 2021-01-02 – 2026-05-01 |
| `companies` บริษัทจดทะเบียน | 931 | 931 | ณ 2 ก.พ. 2026 |
| `risk_metrics` สรุปความเสี่ยงรายหุ้น | 914 | 914 | คำนวณจากทั้งช่วง |

ปฏิทินการซื้อขายตรวจแล้วได้ 241–244 วันทำการต่อปี ซึ่งตรงกับความเป็นจริงของ SET

---

## 2. ปัญหาที่พบในข้อมูลดิบ และวิธีจัดการ

### 2.1 ราคาหุ้น — วันที่ไม่มีการซื้อขายถูกบันทึกเป็นราคา 0

พบ **38,676 แถว** (3.9% ของทั้งหมด) ที่ OHLC เป็น 0 ทั้งแถว หรือปริมาณซื้อขายเป็น 0
ซึ่งหมายถึงหุ้นไม่มีการซื้อขายในวันนั้น ไม่ใช่ราคาหุ้นเท่ากับศูนย์

ถ้าปล่อยไว้จะทำให้การคำนวณผลตอบแทนรายวันพังทันที — ราคาจาก 5 บาทลงไป 0 คือ −100% แล้ววันถัดไปจะกลายเป็น +infinity
จึงตั้งราคาในแถวเหล่านี้เป็นค่าว่าง และเพิ่มคอลัมน์ `is_traded` เพื่อให้กรองออกได้ตอนวิเคราะห์
**เวลาคำนวณผลตอบแทนหรือความผันผวน ต้องใส่เงื่อนไข `WHERE is_traded = 1` เสมอ**

### 2.2 วันที่ถูกเก็บเป็นตัวเลข serial ของ Excel

ทุกคอลัมน์วันที่ในไฟล์ดิบเก็บเป็นตัวเลข เช่น `44200` ไม่ใช่วันที่จริง
แปลงกลับด้วยฐานวันที่ 1899-12-30 ตามมาตรฐาน Excel ทั้ง `date`, `dateAsof` และ `Date/Time`

### 2.3 หัวข้อข่าว 18,408 รายการหายไปตั้งแต่ไฟล์ต้นฉบับ

Excel แปลงหัวข้อข่าวที่ขึ้นต้นด้วยรูปแบบวันที่ให้กลายเป็นค่าวันที่ตอน export
ข้อความจริงหายไปแล้วตั้งแต่ไฟล์ดิบ กู้คืนไม่ได้ จึงแปลงเป็นข้อความ `[date] YYYY-MM-DD`
และทำเครื่องหมายไว้ที่คอลัมน์ `subject_is_date = 1` **ข้อจำกัดนี้แก้ได้ทางเดียวคือ export ข้อมูลใหม่จาก SET โดยตั้งคอลัมน์เป็น Text**

### 2.4 ข่าว 37% ไม่ใช่ข่าวของหุ้นสามัญ

คอลัมน์ Symbol ในไฟล์ข่าวปนหลักทรัพย์หลายชนิดเข้าด้วยกัน เพิ่มคอลัมน์ `security_type` เพื่อแยก

| security_type | n |
|---|---|
| common_stock | 148749 |
| derivative_warrant | 105704 |
| fund_etf_or_other | 30089 |
| unknown | 124 |

**ตอนแนะนำหุ้นต้องกรอง `security_type = 'common_stock'`** ไม่งั้นข่าวใบสำคัญแสดงสิทธิอนุพันธ์จะกลบข่าวจริงของบริษัท

### 2.5 ไฟล์รายชื่อบริษัทใช้สองการเข้ารหัสปนกัน

`listedCompanies_en_US(in).csv` เป็น ASCII เกือบทั้งไฟล์ แต่ที่อยู่บางแถวเป็น TIS-620 ทำให้อ่านด้วย UTF-8 ไม่ผ่าน
แก้โดยไล่ลองเข้ารหัสตามลำดับ utf-8 → cp874 → latin-1

### 2.6 ข่าวซ้ำและวันที่อ่านไม่ได้

ตัดข่าวซ้ำ 180 รายการ (คีย์: เวลา + สัญลักษณ์ + หัวข้อ) และแถวที่ parse วันที่ไม่ได้ 176 รายการ
อีก 124 แถวเป็นข่าวภาพรวมตลาดที่ไม่ผูกกับหุ้นตัวใด — เก็บไว้แต่ `symbol` ว่าง

### 2.7 งบการเงิน

ตัดแถวที่ไม่มีปี/ไตรมาส 3 แถว, แถวที่ไม่มีตัวเลขเลย 0 แถว, และงวดซ้ำ 0 แถว
ตรวจสมการงบดุล (สินทรัพย์ = หนี้สิน + ส่วนของผู้ถือหุ้น) พบไม่ตรงเกิน 1% จำนวน 0 แถว
อัตราส่วนที่หลุดช่วงสมเหตุสมผล เช่น ROE นอกช่วง ±500% ถูกตั้งเป็นค่าว่างแทนการทิ้งทั้งแถว

---

## 3. ความครบถ้วนของข้อมูล — เรื่องที่กระทบการแนะนำหุ้นโดยตรง

| มีใน | แต่ไม่มีใน | จำนวนหลักทรัพย์ |
|---|---|---|
| prices | financials | 61 |
| prices | news | 1 |
| prices | companies | 2 |
| financials | prices | 10 |
| financials | news | 1 |
| financials | companies | 2 |
| news | prices | 24411 |
| news | financials | 24462 |
| news | companies | 24397 |
| companies | prices | 16 |
| companies | financials | 67 |
| companies | news | 1 |

ประเด็นที่ต้องรู้ก่อนสร้างระบบแนะนำ:

- **917 หลักทรัพย์มีราคา แต่มีงบการเงินแค่ 866** — ส่วนต่างคือกองทุนรวมอสังหาฯ REIT กองทุนโครงสร้างพื้นฐาน และ ETF ซึ่งไม่มีงบแบบบริษัท ถ้าระบบบังคับใช้ ROE/D-E จะคัดกลุ่มนี้ออกทั้งหมดโดยไม่ตั้งใจ
- **227 หุ้นใน `risk_metrics` ไม่มีข้อมูล sector** เพราะไม่อยู่ในไฟล์รายชื่อบริษัท (เพิกถอนไปแล้ว หรือเปลี่ยนชื่อย่อ) — กระทบการกระจายพอร์ตตามกลุ่มอุตสาหกรรม
- **22 หุ้นมีข้อมูลราคาน้อยกว่า 250 วัน** (IPO ใหม่หรือหยุดพักการซื้อขายนาน) ตัวเลขความผันผวนของกลุ่มนี้เชื่อถือได้น้อย
- ข้อมูล ณ วันที่ล่าสุดคือ 2025-12-30 **ไม่ใช่ข้อมูล real-time** ถ้าจะใช้จริงต้องบอกผู้ใช้ว่าเป็นข้อมูลย้อนหลัง

สัดส่วนค่าว่างในคอลัมน์ที่ใช้บ่อย: P/E 30.5%, P/BV 1.5%, อัตราปันผล 33.6%, มูลค่าตลาด 0.7%
P/E ว่างส่วนใหญ่แปลว่าบริษัทขาดทุน ไม่ใช่ข้อมูลหาย — **อย่าเติมค่าเฉลี่ยแทน** เพราะจะกลายเป็นการซ่อนบริษัทที่ขาดทุน

---

## 4. ตาราง `risk_metrics` — ตัวเชื่อมไปยัง TSI Risk Profile

คำนวณจากหุ้นที่มีข้อมูลอย่างน้อย 20 วันทำการ ได้ 914 หลักทรัพย์
แบ่งกลุ่มความเสี่ยง 1–5 จากความผันผวนต่อปี ให้แมปกับผลประเมิน TSI Risk Profile ได้โดยตรง

| กลุ่มความเสี่ยง | จำนวนหุ้น | ผันผวนเฉลี่ย % | ขาดทุนสูงสุดเฉลี่ย % | ปันผลเฉลี่ย % |
|---|---|---|---|---|
| 1_very_low | 61 | 16.3 | -39.0 | 6.37 |
| 2_low | 157 | 25.3 | -51.1 | 4.84 |
| 3_moderate | 312 | 37.5 | -67.6 | 3.87 |
| 4_high | 254 | 53.2 | -77.1 | 3.51 |
| 5_very_high | 130 | 99.3 | -84.2 | 3.49 |

ค่าที่มีในตาราง: ความผันผวนต่อปี, ขาดทุนสูงสุดจากจุดสูงสุด (max drawdown), CAGR, ผลตอบแทนรวม,
มูลค่าซื้อขายเฉลี่ยต่อวัน, มูลค่าตลาด, P/E, P/BV, อัตราปันผล, ROE/ROA/D-E งวดล่าสุด,
จำนวนข่าวและจำนวนข่าวเชิงลบใน 2 ปีล่าสุด, `risk_bucket`, `liquidity_tier`, `news_red_flag`

### ระดับสภาพคล่อง

| ระดับสภาพคล่อง | จำนวนหุ้น |
|---|---|
| normal | 351 |
| thin | 343 |
| illiquid | 120 |
| liquid | 100 |

สภาพคล่องสำคัญไม่แพ้ความผันผวน หุ้นที่ซื้อขายวันละไม่ถึงล้านบาทอาจมีความผันผวนต่ำเพราะแทบไม่มีคนซื้อขาย
ไม่ใช่เพราะราคานิ่งจริง **ผู้ใช้ที่รับความเสี่ยงต่ำไม่ควรได้หุ้นกลุ่ม `illiquid` หรือ `thin` แม้ตัวเลขความผันผวนจะดูดี**

---

## 5. การจัดหมวดข่าวและสัญญาณความเสี่ยง

หมวดข่าวมาจากการจับรูปแบบข้อความในหัวข้อ หมวดที่ทำเครื่องหมาย `is_risk_signal = 1`
คือข่าวที่โดยธรรมชาติเป็นสัญญาณลบ เช่น ขึ้นเครื่องหมายห้ามซื้อขาย เข้าข่ายเพิกถอน SET ขอคำชี้แจง
ผู้สอบบัญชีไม่แสดงความเห็น ฟ้องร้อง ผิดนัดชำระหนี้ ลดทุน กรรมการลาออก

| หมวด | จำนวน | เป็นสัญญาณเสี่ยง |
|---|---|---|
| other | 80655 | 0 |
| dw_notice | 46208 | 0 |
| financial_statement | 40715 | 0 |
| book_closure | 23653 | 0 |
| mdna | 13880 | 0 |
| board_change | 12545 | 0 |
| shareholder_meeting | 11606 | 0 |
| nav_report | 11517 | 0 |
| dividend | 9678 | 0 |
| share_repurchase | 6756 | 0 |
| capital_increase | 4609 | 0 |
| warrant | 4163 | 0 |
| corporate_admin | 3706 | 0 |
| resignation | 3599 | 1 |
| mna | 3357 | 0 |
| set_clarification | 1564 | 1 |
| connected_txn | 1525 | 0 |
| market_surveillance | 1314 | 1 |
| public_presentation | 1295 | 0 |
| capital_reduction | 875 | 1 |
| delisting | 672 | 1 |
| litigation | 234 | 1 |
| ipo_listing | 224 | 0 |
| trading_sign_halt | 164 | 1 |
| default_debt | 120 | 1 |
| net_loss | 30 | 1 |
| auditor_issue | 2 | 1 |

รวมข่าวที่เป็นสัญญาณความเสี่ยง 8,574 รายการ

**ข้อจำกัดที่ต้องรู้:** หมวดมาจากคำในหัวข้อเท่านั้น ไม่ได้อ่านเนื้อข่าว จึงบอกได้แค่ว่า
*เป็นข่าวประเภทไหน* ไม่ได้บอกว่า *ข่าวนั้นดีหรือร้าย*
ตัวอย่างเช่น ข่าวเพิ่มทุนอาจเป็นบวก (ขยายกิจการ) หรือลบ (ขาดสภาพคล่อง) ก็ได้
หัวข้อข่าว 80,655 รายการยังจัดหมวดไม่ได้ (28%)
ซึ่งส่วนใหญ่คือหัวข้อที่หายไปตามข้อ 2.3 กับหัวข้อเฉพาะทางที่ไม่ซ้ำใคร
ถ้าต้องการ sentiment จริงจังต้องใช้โมเดลภาษาอ่านหัวข้อ ไม่ใช่การจับคำ

หุ้นที่มีข่าวเชิงลบถี่ผิดปกติใน 2 ปีล่าสุดถูกทำเครื่องหมาย `news_red_flag = 1` จำนวน 49 ตัว
ตรวจสอบแล้วสอดคล้องกับความเป็นจริง — หุ้นที่ติดธงมีความผันผวนสูงและขาดทุนหนักกว่าค่าเฉลี่ยชัดเจน

---

## 6. การตรวจสอบความถูกต้อง

- สุ่มเทียบราคาปิดและปริมาณซื้อขาย 8 จุดจากไฟล์ต้นฉบับ 2 ไฟล์ ตรงกันทั้งหมด
- เทียบงบการเงิน EASTW ไตรมาส 2/2021 (สินทรัพย์รวม กำไรสุทธิ ROE) ตรงกับต้นฉบับทุกตัว
- เทียบข่าวแถวแรกของปี 2022 ตรงกับต้นฉบับ และจัดหมวดถูกต้อง
- ตรวจค่าที่เป็นไปไม่ได้: ราคาปิด ≤ 0, high < low, ผลตอบแทนวันเดียวเกิน 100%, คีย์ซ้ำในทุกตาราง — เป็น 0 ทั้งหมด
- จำนวนวันทำการต่อปี 241–244 วัน ตรงกับปฏิทิน SET

---

## 7. ข้อควรระวังก่อนนำไปสร้างระบบแนะนำหุ้น

**ความผันผวนในอดีตไม่ใช่ความเสี่ยงในอนาคต** `risk_bucket` คำนวณจากข้อมูลปี 2021–2025 ซึ่งครอบคลุมช่วงโควิดและช่วงดอกเบี้ยขาขึ้น หุ้นที่เคยนิ่งอาจผันผวนขึ้นได้เมื่อสถานการณ์เปลี่ยน ควรแสดงให้ผู้ใช้เห็นว่าตัวเลขมาจากช่วงเวลาไหน

**ระวัง survivorship bias** ชุดข้อมูลนี้เป็นหุ้นที่ยังอยู่ในระบบ ณ วันที่ export หุ้นที่เพิกถอนไประหว่างทางอาจหายไปบางส่วน ทำให้ผลตอบแทนย้อนหลังของทั้งตลาดดูดีเกินจริง

**ข้อมูลราคาไม่ได้ปรับด้วย corporate action** ไม่พบผลตอบแทนวันเดียวเกิน 100% ก็จริง แต่ไม่ได้แปลว่าราคาถูกปรับย้อนหลังตามการแตกพาร์หรือจ่ายปันผลแล้ว CAGR ที่คำนวณได้จึงเป็นผลตอบแทนจากราคาอย่างเดียว ไม่รวมเงินปันผล

**ข้อมูลนี้เป็นข้อมูลย้อนหลังไม่ใช่คำแนะนำการลงทุน** ระบบควรแสดงข้อความกำกับให้ชัดเจน และไม่ควรใช้ตัดสินใจลงทุนจริงโดยไม่มีข้อมูลปัจจุบันประกอบ

---

## 8. ไฟล์ที่ได้

| ไฟล์ | คำอธิบาย |
|---|---|
| `set_clean.sqlite` | ฐานข้อมูลหลัก 6 ตาราง มี index ครบ query ได้ทันที |
| `stock_prices.csv.gz` | ราคารายวัน |
| `financials.csv.gz` | งบการเงินรายไตรมาส |
| `news.csv.gz` | ข่าว + หมวด + สัญญาณความเสี่ยง + ประเภทหลักทรัพย์ |
| `companies.csv.gz` | ข้อมูลบริษัทจดทะเบียน |
| `risk_metrics.csv.gz` | สรุปความเสี่ยงรายหุ้น |
| `symbol_coverage.csv` | ตารางความครบถ้วนของสัญลักษณ์ข้ามชุดข้อมูล |
| `data_quality_audit.csv` | บันทึกทุกการตัด/แก้ไข พร้อมจำนวนแถว |
| `pipeline.py`, `enrich.py`, `fastxlsx.py` | โค้ดทั้งหมด รันซ้ำได้ |

## Post-build audit (September 2026)

The factor table was rebuilt correctly from the exchange files, but building a
number correctly is not the same as the number meaning something. A range check
over all 94 derived columns found six cases where a value was arithmetically
valid and economically empty. Each is now voided or flagged in
`core/corrections.py`, which runs inside `data.factors()` — no page, score or
recommendation sees the uncorrected table. The in-app record is on the News
Intelligence page under "What the audit removed".

**The trailing yield trap.** RS reported a 48.22% dividend yield and an income
score of 84.8 while its price fell 96.33% over the year. A trailing yield is
dividends already paid over today's price; when the denominator collapses the
ratio explodes without anything good having happened. Seventeen securities met
the pattern of a yield above 12% together with a fall of more than 30%. The raw
yield is still displayed, because hiding it would hide the warning, but the
income score is now built from a yield capped at 10% with trapped names set to
zero, and those names are excluded from recommendations outright. Genuine payers
were unaffected or improved: 3BBIF moved 78.4 to 84.3.

**Securities that had stopped trading.** Seventeen names carried a full set of
factors computed from their final prices. WELL last traded on 25 October 2021,
1,527 days before the end of the data, and still scored 53.6 overall — above the
median of the live universe. Every analysis surface now reads `active_factors()`
instead of `factors()`. The exception is Security Detail, which still opens them
so the record can be read, with a warning stating the last trade date. Holdings
also keeps the full table, since a real position can sit in a halted name.

**Horizons the security never lived through.** 88TH has 59 trading days of
history and reported a three-year return of -46.34%, identical to its one-year
return, because both were "return since listing" wearing different labels. 123
securities reported a three-year return without three years of history. Any
horizon longer than the available history is now blank rather than misleading.

**Margins that invert.** FNS reported revenue of -1,111,710 and profit of
-2,798,880; dividing one negative by the other produced a +251.8% net margin for
a loss-making company. ACAP showed 2,245% from a profit 22x its revenue.
Margins are voided when revenue is not positive or the result falls outside
±150%.

**Ratios with no upper bound.** ASIA reported a P/E of 12,664 and one security
carried exactly -100000, a sentinel that had leaked into a numeric column. Above
roughly 150x a P/E describes earnings near zero rather than an expensive stock,
so those are blanked and flagged.

**An untradeable default universe.** 503 of 914 securities turn over less than
1M THB a day and 162 did not move at all over a week. The screener now opens on
names above 1M THB a day, with a visible checkbox to include the rest. A
`days_to_exit_500k` column reports how many sessions it takes to leave a 500,000
THB position at 20% of normal turnover.

### Checked and found sound

The cap-weighted index proxy returned -9.61% for 2025 against the SET Index's
actual -10.57%, and reproduces the shape of every other year in the window.
Beta spans -0.72 to 2.80 and RSI 16 to 86, both unremarkable. The
advance-decline line uses raw closes while the return factors use adjusted
closes; the up/down verdict differs on 7 of 961,842 daily observations, which is
immaterial and was left alone rather than fixed for its own sake.

## Found after the first deployment (October 2026)

**140 disclosures dated in the future.** The live site showed "1 May 2026"
headlines at the top of Latest disclosures, beside a market dated 30 December
2025. Every one of the 140 rows carried that single date. The export itself was
produced on 13 January 2026, so a May 2026 filing cannot exist. 1 May 2025 holds
zero headlines in the data while 1 May in 2022, 2023 and 2024 holds 71, 69 and
66 — one day whose year was misread on the way in.

The correct date is a reasonable inference but not a certainty, so the rows are
dropped rather than rewritten. `data.news()` now discards anything dated more
than a day after the last trading day and records the count in
`attrs["dropped_future_dated"]`. 148,593 headlines remain of 148,733.

This one only became visible once the app was hosted and the landing page put
the newest headline on screen. A defect can sit in a table for weeks and still
be invisible until something sorts by it.
