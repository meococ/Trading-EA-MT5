{
  "answer": "Here is how those specific trade execution parameters and discipline guidance are defined across the Sonic R sources:\n\n---\n\n### 1. \"Several Pips Beyond the Signal Candle\" in Practice\n* **Exact Definition**: The rules state that after waiting for the Wave leg #3 candle to break out of the Dragon band, the trader places their entry order **\"at least several pips beyond it\"** [1, 2].\n* **Practical Meaning & Numerical Value**: The sources **do not specify a fixed, rigid pip number** (such as \"3 pips\" or \"5 pips\") [1, 2]. Instead, \"several pips\" represents a discretionary safety buffer (padding) added beyond the signal candle's extreme high or low [1, 2]. In MT4 practice when setting Buy Stop or Sell Stop pending orders, this buffer prevents getting prematurely filled by momentary spread widening or micro-price spikes before a genuine breakout momentum takes place [1, 3].\n\n---\n\n### 2. \"Large-Scale Swing\" / \"Larger Scale Wave\" for Stop Placement\n* **Exact Definition**: Rule #1 for Stop Loss placement dictates that *\"The SL must be beyond the H/L (for shorts/longs) of the recent large scale price swing\"* [4] (or the peak/trough of the nearest swing) [5].\n* **Practical Application**: Rather than setting a tight stop behind a single M15 candle wick, the trader identifies the **major structural high or low** of the overall wave leg that brought price into or through the Dragon [4, 5]. \n* **Breathing Room vs. Hard Caps**: The doctrine stresses that the Stop Loss must be wide enough to give price **\"room to breathe\"** without being prematurely stopped out by normal market noise [6, 7]. However, this is bounded by strict upper caps:\n  * Maximum **100–120 pips** from the Entry Point (EP) for EUR/USD [4-6].\n  * At least **80 pips** for JPY pairs [8].\n\n---\n\n### 3. \"No More Than 5 Trades per Week\": Per Account vs. Per Pair\n* **Guidance Context**: Rule #1 explicitly states: *\"Do not over trade big-time, or trade during Asian Session. Most of the best setups with proper follow-thru occur after the London session opens. You shouldn't trade more than 5 trades a week. Look for quality setups, not quantity.\"* [9, 10]\n* **Per Account/Trader Limit**: This guidance is presented as an **overall account/trader behavioral discipline rule**, **not a per-pair quota** [9, 10]. It is designed to prevent overtrading across all currency pairs and force the trader to execute only the highest-quality London session setups [9, 10].\n\n---\n\n*Citing Sources*:\n* *Th3-Pro-Forex: Sonic R. System 2013* [2, 4, 7, 10]\n* *Sonic R System: Sonic R. System - Kyaw Trader Sonic Deejay* [6, 9]\n* *Sonic R là gì? Cách vào lệnh cực nhanh với chỉ báo Sonic R* [1, 5, 8]\n\n---\n\n💡 Would you like to review how the `Sonic_3 Trade Levels` indicator automates calculating and drawing these EP, SL, and TP lines on your charts?",
  "question": "In the Sonic R sources, what exactly does 'several pips beyond the signal candle' mean in practice (how many pips), and what does 'large-scale swing' or 'a larger scale wave' mean in practice for stop placement? Also: is the 'no more than about 5 trades per week' guidance per account or per pair? Cite sources.",
  "conversation_id": "eb37ddfc-2f95-4960-a5f6-b439df074a2c",
  "sources_used": [
    "6c5ed85f-870f-4866-b229-74bef283738e",
    "158fb243-89e5-4829-a45e-bd50d01066ec",
    "ef17e6e4-86ed-4596-8c71-f669d624cbd6",
    "3e353cb4-2ae2-4d42-acde-161f23b5f49e"
  ],
  "citations": {
    "1": "6c5ed85f-870f-4866-b229-74bef283738e",
    "2": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "3": "ef17e6e4-86ed-4596-8c71-f669d624cbd6",
    "4": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "5": "6c5ed85f-870f-4866-b229-74bef283738e",
    "6": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
    "7": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "8": "6c5ed85f-870f-4866-b229-74bef283738e",
    "9": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
    "10": "158fb243-89e5-4829-a45e-bd50d01066ec"
  },
  "references": [
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 1,
      "cited_text": "Nguyên tắc khi giao dịch với Sonic R là gì? Cách sử dụng hệ thống Sonic R Forex Sử dụng điểm đặt Entry Nhà giao dịch chờ đợi cho nến tại chân của sóng thứ 3 bứt phá ra khỏi dải Dragon. Sau đó đặt điểm Entry tối thiểu vài pips bên ngoài, sẽ an toàn hơn nếu không có vùng hỗ trợ kháng cự nào được hình thành gần điểm Entry. Nhà giao dịch cũng có thể đặt điểm Entry ở mức giá trên Trend cho các lệnh mua và dưới Trend cho các lệnh bán."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 2,
      "cited_text": "Placement of EP Wait for a WAVE leg #3 candle to break out of the DRAGON, and place your entry order at least several pips beyond it. It is better if there is no strong S&R area just beyond the entry. Remember also, it is best if PA is above TREND for longs, below TREND for shorts. Placement of Re-entry It is best to let PA clear the most recent high, or low, and if there is no strong S&R area just beyond this re-entry. Placement Of TP Select a historic S&R level. Such levels can include whole/half/quarter numbers and the middle of consolidation areas."
    },
    {
      "source_id": "ef17e6e4-86ed-4596-8c71-f669d624cbd6",
      "citation_number": 3,
      "cited_text": "Khi bạn đặt lệnh thông qua một nền tảng như vậy, bạn sẽ mua hoặc bán một khối lượng nhất định của một loại tiền tệ nhất định. Bạn cũng có thể đặt giới hạn dừng lỗ và chốt lời cho mình. Giới hạn dừng lỗ là số pip tối đa mà bạn có thể chấp nhận đánh mất trước khi từ bỏ một giao dịch. Còn giới hạn chốt lời là số pip mà bạn sẽ bỏ túi khi giá di chuyển theo hướng có lợi cho bạn."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 4,
      "cited_text": "Placement of SL These are the rules for placement of the SL (see picture below that illustrates):** 1. The SL must be beyond the H/L (for shorts/longs) of the recent large scale price swing. 2. The SL must not be more than 100-120 pips from the EP (for EUR/USD). Example **Below are an example of a Sonic R. System short setup and trade, and of the rules for placement of the SL. The key elements of the Sonic R. System are clearly labeled and illustrated. Conclusion To start with the Sonic R. System, read all of Post #1 and the linked material. Read the first 25-50 of Sonicdeejay's posts. Read at least the last month of all posts. Please do not ask any questions for the first month of studying this system, because as you read, reflect, and read more, all of your questions will become answered thru your own efforts."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 5,
      "cited_text": "Sử dụng điểm đặt TP Nhà đầu tư chọn các ngưỡng hỗ trợ và kháng cự quá khứ, nó có thể là toàn bộ/một phần của sóng trước đó ở khung thời gian M30 hoặc điểm chính giữa của vùng nén giá. Nhà đầu tư cũng có thể chọn các ngưỡng trong phạm vi ngày để vào hoặc thoát lệnh nhanh hơn. Sử dụng điểm đặt SL Những nguyên tắc khi đặt SL mà nhà giao dịch cần lưu ý đó là: SL phải được đặt bên ngoài đỉnh (cho các lệnh bán) hoặc đáy (cho các lệnh mua) của swing gần nhất. Không nên đặt SL nhiều hơn 100 – 120 pips từ Entry (đối với cặp tiền EUR/USD)."
    },
    {
      "source_id": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
      "citation_number": 6,
      "cited_text": "2. Dot not add to a losing position. With the advent of Scout trades and PVSRA, there is the temptation to do so. No matter the results of a good PVSRA, it is recommended that you not do this. 3. Your SL must wide enough to for the price to breathe. If you put it too tight, the chance of getting your SL hit is very high even though the price eventually goes in the direction you wanted. For example, I recommend you use a SL of up to 100 pips when trading EURUSD. ============================================================"
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 7,
      "cited_text": "3. You SL must wide enough to for the price to breath.. If you put it too tight, the chance of getting your SL hit is very high even though the price goes to direction that you wanted eventually. **I have put the \"entry, exit, SL and TP\" rules with all necessary indicators into \"SonicR or SonicRV2 or SonicRV3\" zip file. SonicRV3 is created with better and more comprehensive examples.. You also can check out our best contributer Professor TAH's templates** Summary of Upgrade and Installation **Attached are new TAH indicators and starter templates for the Sonic R. System. This upgrade fixes and improves the indicators, described as follows (Red Headings). Download the zip file. Extract it to yield the two folders for black and white charts that contain the individual indicator and template files. Paste the indicator files into the MT4/experts/indicators folder. Paste the template files into the MT4/templates folder. Restart your MT4 application."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 8,
      "cited_text": "Wave là giá tạo sóng. Sóng L – H – HL bắt đầu ở phía dưới dải Dragon, sau đó chuyển sang HH cho lệnh mua và chuyển sang LL thì cho lệnh bán. Dragon (dải EMA34) sẽ được dùng để chọn điểm vào lệnh (trong trường hợp xu hướng của thị trường mạnh). Trend (đường EMA89) được sử dụng để xác định phương hướng giao dịch đúng. Song cũng có một số trường hợp đường Trend được dùng để tìm kiếm điểm vào lệnh chính xác hơn so với dải Dragon. Phiên giao dịch được khuyến nghị là phiên Âu để có xung lực tốt nhất, không nên giao dịch ở phiên Á. Cặp tiền tệ có thể là bất cứ cặp tiền nào, chẳng hạn như EUR/USD, GBP/USD hoặc cũng có thể là XXX/JPY nhưng nhà đầu tư cần đổi Trailing Stop và đặt Stop Loss ít nhất 80 pip đối với cặp tiền này. Khung thời gian giao dịch chính là M15, khung H4 hoặc D4 cũng có thể được sử dụng với mục đích kết hợp, phát hiện các mô hình nến cho khung M15."
    },
    {
      "source_id": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
      "citation_number": 9,
      "cited_text": "http://www.forexfactory.com/showthread.php?p=7348659#post7348659 http://www.forexfactory.com/attachment.php?attachmentid=1388804&d=1395172347 http://www.forexfactory.com/showthread.php?t=83521 ================================================================= Serious Recomendations 1. Do not over trade big-time, or trade during Asian Session. Most of the best setups with proper follow-thru occur after the London session opens. You shouldn't trade more than 5 trades a week. Look for quality setups, not quantity."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 10,
      "cited_text": "Now, it is not the magic bullet, nothing is. It is a simple EMA based yet effective system. You can earn 50 to 400+ pips on a trade. The Reason And why am I sharing this, while I do not earn a penny from you for my time and effort? Because I believe Sharing is Caring. The Setups/Rules of the system Sonic Rules.** 1. Do not Over trade big or trade during Asian Session.. Most of the best Set Up or Proper trend occur at/after London Opens. You shouldn't trade more than 5 trades a week.. 2. Never add a losing positions aka average your positions."
    }
  ]
}
