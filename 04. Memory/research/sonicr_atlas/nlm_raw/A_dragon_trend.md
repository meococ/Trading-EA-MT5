{
  "answer": "### (1) Exact Computations of the Dragon and the Trend\n\nIn the source file **SonicR_Filled_Dragon_White.txt**, the parameters and calculations are defined as follows:\n\n*   **The Dragon**:\n    *   **Period**: `34` (`Dragon_Period = 34;`) [1]\n    *   **MA Type**: Exponential Moving Average (`Dragon_Type = 1;` where `1` = `EMA`) [1, 2]\n    *   **Applied Prices & Code Computation**:\n        *   **High Price** (`PRICE_HIGH`) for the upper boundary:\n            ```mql4\n            DragonHigh[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift);\n            DragonTop[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift);\n            ``` [3]\n        *   **Low Price** (`PRICE_LOW`) for the lower boundary:\n            ```mql4\n            DragonLow[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift);\n            DragonBot[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift);\n            ``` [3]\n        *   **Close Price** (`PRICE_CLOSE`) for the center line:\n            ```mql4\n            DragonCntrArea[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift);\n            DragonCntrLine[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift);\n            ``` [3]\n    *   *Summary*: The Dragon is a color-filled band constructed from a 34 EMA of Close prices for its center line, bounded by 34 EMAs of High and Low prices [3, 4].\n\n*   **The Trend**:\n    *   **Period**: `89` (`Trend_Period = 89;`) [2]\n    *   **MA Type**: Exponential Moving Average (`Trend_Type = 1;` where `1` = `EMA`) [2]\n    *   **Applied Price**: Close Price (`PRICE_CLOSE`) [3]\n    *   **Code Computation**:\n        ```mql4\n        Trend1[i] = iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift);\n        Trend2[i] = iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift);\n        ``` [3]\n\n**Source Title**: *SonicR_Filled_Dragon_White.txt* [1-4]\n\n---\n\n### (2) Computation of Slope / Angle in Code\n\n**No slope or angle is computed in the code** [3]. The script only calculates raw `iMA` values for each bar without any mathematical slope, delta, or arctangent angle calculations [3]. Therefore, the \"angle\" of the Dragon or Trend is **purely visual** for the trader examining the chart [3, 5].\n\n**Source Title**: *SonicR_Filled_Dragon_White.txt* [3]\n\n---\n\n### (3) Purpose of Dragon Angle and Price Position in Text Sources\n\nAccording to the Sonic R text documentation, traders use the Dragon's angle and price position for two core purposes:\n\n1.  **Trend & Bias Confirmation**:\n    *   The Dragon must be **angled up** with Price Action (PA) **above** it to confirm long setups/uptrends [5].\n    *   The Dragon must be **angled down** with Price Action **below** it to confirm short setups/downtrends [5].\n2.  **Selecting Trade Entries**:\n    *   The Dragon is used for **picking trade entries** (e.g., waiting for a Wave leg #3 candle to break out of the Dragon or entering on price pullbacks/re-entries around the Dragon band) [6-10].\n\n**Source Titles**:\n*   *Th3-Pro-Forex: Sonic R. System 2013* [5, 9, 10]\n*   *Sonic R là gì? Cách vào lệnh cực nhanh với chỉ báo Sonic R* [6-8, 11]\n*   *Sonic R System: Sonic R. System - Kyaw Trader Sonic Deejay* [12]\n\n---\n\n### (4) Buffers Holding Trend Values\n\nIn the indicator file `SonicR_Filled_Dragon_White.txt`, the 89 EMA Trend line values are assigned to **Buffer 6** and **Buffer 7**:\n*   `SetIndexBuffer(6, Trend1);` [13]\n*   `SetIndexBuffer(7, Trend2);` [13]\n\n*(Note: In third-party software integration code references, buffer index 5 or 6 may be queried via `iCustom()` depending on the specific wrapper implementation) [14].*\n\n**Source Titles**:\n*   *SonicR_Filled_Dragon_White.txt* [3, 13]\n*   *Giao dịch thuật toán Forex: Một câu chuyện thực tế cho các kỹ sư phần mềm! | TraderViet | Cộng Đồng Trader Việt Nam* [14]\n\n---\n\n💡 **Next Step**: Would you like to explore how the Dragon and Trend interact with the **PVSRA** (Price, Volume, Support & Resistance Analysis) volume colors to confirm re-entry setups?",
  "question": "GROUP A - Dragon and Trend. From the uploaded MQ4 source files (SonicR_Filled_Dragon_White.txt) and the Sonic R text sources: (1) What exactly is the Dragon and the Trend — quote the exact computation (periods, MA type, applied price) from the code. (2) Is any slope or angle computed in the code, or is 'angle' purely visual? (3) What do the text sources say the trader uses the Dragon angle and price position for? (4) Which buffers in the code hold the Trend values? Cite the source title for each answer.",
  "conversation_id": "eb37ddfc-2f95-4960-a5f6-b439df074a2c",
  "sources_used": [
    "9499c9a0-2cf8-401e-b63a-e53744214434",
    "158fb243-89e5-4829-a45e-bd50d01066ec",
    "6c5ed85f-870f-4866-b229-74bef283738e",
    "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
    "ef17e6e4-86ed-4596-8c71-f669d624cbd6"
  ],
  "citations": {
    "1": "9499c9a0-2cf8-401e-b63a-e53744214434",
    "2": "9499c9a0-2cf8-401e-b63a-e53744214434",
    "3": "9499c9a0-2cf8-401e-b63a-e53744214434",
    "4": "9499c9a0-2cf8-401e-b63a-e53744214434",
    "5": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "6": "6c5ed85f-870f-4866-b229-74bef283738e",
    "7": "6c5ed85f-870f-4866-b229-74bef283738e",
    "8": "6c5ed85f-870f-4866-b229-74bef283738e",
    "9": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "10": "158fb243-89e5-4829-a45e-bd50d01066ec",
    "11": "6c5ed85f-870f-4866-b229-74bef283738e",
    "12": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
    "13": "9499c9a0-2cf8-401e-b63a-e53744214434",
    "14": "ef17e6e4-86ed-4596-8c71-f669d624cbd6"
  },
  "references": [
    {
      "source_id": "9499c9a0-2cf8-401e-b63a-e53744214434",
      "citation_number": 1,
      "cited_text": "//global external inputs extern bool   Indicator_On                    = true; extern int    Chart_Zoom_123456               = 3; extern bool   Trend_On                        = true; extern int    Display_Max_TF                  = 43200; extern string TF_Choices_H1_H4_D_W_M          = \"60   240  1440  10080  43200\"; //Global Buffers and Variables bool   Deinitialized; int    i,BarShift,counted_bars,limit; string ShortName; //Dragon- int    Bar_Width,Bands; double DragonHigh[],DragonLow[],DragonTop[],DragonBot[],DragonCntrArea[],DragonCntrLine[]; string Dragontype                      = \"ema\"; int    Dragon_Period                   = 34; int    Dragon_Type                     = 1;"
    },
    {
      "source_id": "9499c9a0-2cf8-401e-b63a-e53744214434",
      "citation_number": 2,
      "cited_text": "//Trend- double Trend1[],Trend2[]; string Trendtype                       = \"ema\"; int    Trend_Off_Std_Dragon_012        = 1; int    Trend_Period                    = 89; int    Trend_Type                      = 1; //Global Variable Controlling Bar Widths string Zoom = \"Zoom_Setting\"; double B; string Bar = \"Bar_Setting\"; /*General notes: MAType  = 0=SMA,1=EMA,2=SMMA,3=LWMA MAPrice = 0=CLOSE,1=OPEN,2=HIGH,3=LOW,4=MEDIAN,5=PP,6=WEIGHT */ //+-------------------------------------------------------------------------------------------+ //| Indicator Initialization                                                                  | //+-------------------------------------------------------------------------------------------+ int init() { Deinitialized = false;"
    },
    {
      "source_id": "9499c9a0-2cf8-401e-b63a-e53744214434",
      "citation_number": 3,
      "cited_text": "//Otherwise indicator is \"On\" & chart TF is in display range, so proceed. Deinitialized = false; //Confirm range of chart bars for calculations //check for possible errors counted_bars = IndicatorCounted(); if(counted_bars < 0)  return(-1); //last counted bar will be recounted if(counted_bars > 0) counted_bars--; limit = Bars - counted_bars; //Begin the loop of calculations for the range of chart bars. for(i = limit - 1; i >= 0; i--) { //Dragon BarShift = iBarShift(NULL,NULL,Time[i],true); DragonHigh[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift); DragonLow[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift); DragonTop[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift); DragonBot[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift); DragonCntrArea[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift); DragonCntrLine[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift); //Trend if(Trend_On) { BarShift = iBarShift(NULL,NULL,Time[i],true); Trend1[i]= iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift); Trend2[i]= iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift); } }"
    },
    {
      "source_id": "9499c9a0-2cf8-401e-b63a-e53744214434",
      "citation_number": 4,
      "cited_text": "/*--------------------------------------------------------------------------------------------- Overview, _v1: This indicator displays both the SonicR Dragon and the SonicR Trend.  The SonicR Dragon is color filled and is based upon 34 EMA averaging of close prices with high/low prices defining outer edges.  The SonicR Trend is based upon 89 EMA averaging of close prices. About color filling the Dragon - Histogram bars and MA Edge_Widths are used in the construction of the color fill.  Zooming in on a chart requires these components be made wider to prevent spaces appearing between them.  Zooming out on a chart requires these components be made narrower to prevent the Dragon from being too wide.  Use the \"Chart_Zoom_123456\" inputs to control adjustments to the Dragon as you zoom in/out on charts.  Apply \"1\" to \"6\" depending on the zoom setting the chart has been set to.  If the setting for \"Chart_Zoom_123456\" is not between 1-6 it defaults to \"3\". Setting the Zoom - MT4 has six chart zoom settings, referred to in this indicator from narrowest bars to widest bars as number selections 1 thru 6.  Use the \"Chart_Zoom_123456\" input to set the widths of the bars.  Use \"1 or 2\" for zoomed out charts (thinner bars).   Use \"3\" for the Mt4 default chart chart zoom.  Use \"4,5, or 6\" for zoomed in charts (wider bars)."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 5,
      "cited_text": "DRAGON Must be angled up with PA above it for longs, and angled down with PA below it for shorts. TREND This is a market bias indicator and it is best if PA is above it for longs and below it for shorts. TIMING Prefer not to open trade during asian session. Recommend London session for best momentum. Trade can be closed anytime. PAIRS Prefer to trade the pair EUR/USD. Lowest spread. Usually a wide range. Most important is it is most traded pair, which means better volume and better momentum for the trade."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 6,
      "cited_text": "Wave là giá tạo sóng. Sóng L – H – HL bắt đầu ở phía dưới dải Dragon, sau đó chuyển sang HH cho lệnh mua và chuyển sang LL thì cho lệnh bán. Dragon (dải EMA34) sẽ được dùng để chọn điểm vào lệnh (trong trường hợp xu hướng của thị trường mạnh). Trend (đường EMA89) được sử dụng để xác định phương hướng giao dịch đúng. Song cũng có một số trường hợp đường Trend được dùng để tìm kiếm điểm vào lệnh chính xác hơn so với dải Dragon. Phiên giao dịch được khuyến nghị là phiên Âu để có xung lực tốt nhất, không nên giao dịch ở phiên Á. Cặp tiền tệ có thể là bất cứ cặp tiền nào, chẳng hạn như EUR/USD, GBP/USD hoặc cũng có thể là XXX/JPY nhưng nhà đầu tư cần đổi Trailing Stop và đặt Stop Loss ít nhất 80 pip đối với cặp tiền này. Khung thời gian giao dịch chính là M15, khung H4 hoặc D4 cũng có thể được sử dụng với mục đích kết hợp, phát hiện các mô hình nến cho khung M15."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 7,
      "cited_text": "Nguyên tắc khi giao dịch với Sonic R là gì? Cách sử dụng hệ thống Sonic R Forex Sử dụng điểm đặt Entry Nhà giao dịch chờ đợi cho nến tại chân của sóng thứ 3 bứt phá ra khỏi dải Dragon. Sau đó đặt điểm Entry tối thiểu vài pips bên ngoài, sẽ an toàn hơn nếu không có vùng hỗ trợ kháng cự nào được hình thành gần điểm Entry. Nhà giao dịch cũng có thể đặt điểm Entry ở mức giá trên Trend cho các lệnh mua và dưới Trend cho các lệnh bán."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 8,
      "cited_text": "Nguyên tắc thiết lập điểm Stop Loss Giao dịch theo phương pháp đảo chiều Khi thị trường có xu hướng mạnh, trader giao dịch với dải EMA34 (có thể kết hợp với các chỉ báo hỗ trợ các định độ mạnh yếu của xu hướng như ADX, BB). Trong xu hướng tăng , đường giá nằm trên dải EMA, trader vào lệnh BUY khi giá hồi về dải EMA. Trong xu hướng giảm , đường giá nằm dưới dải EMA, trader vào lệnh SELL khi giá hồi lên trên dải EMA."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 9,
      "cited_text": "The latest Sonic R. System Manual (in brief) **The Sonic R. System is a method of trading price movements between areas of support and resistance. It trades on the M15 chart. It uses a price activity WAVE at an S&R area to validate a trade setup, and technical indicators called the DRAGON and the TREND. The DRAGON is used for picking the trade entry. The TREND is used to confirm the correct trade direction. Historic S&R is used for picking the trade exit. WAVE L-H-HL starting below Dragon for longs, H-L-LH starting above Dragon for shorts, showing \"bounce\" or “breakthrough” at S&R. Best if WAVE leg #1 crosses thru the Dragon."
    },
    {
      "source_id": "158fb243-89e5-4829-a45e-bd50d01066ec",
      "citation_number": 10,
      "cited_text": "Placement of EP Wait for a WAVE leg #3 candle to break out of the DRAGON, and place your entry order at least several pips beyond it. It is better if there is no strong S&R area just beyond the entry. Remember also, it is best if PA is above TREND for longs, below TREND for shorts. Placement of Re-entry It is best to let PA clear the most recent high, or low, and if there is no strong S&R area just beyond this re-entry. Placement Of TP Select a historic S&R level. Such levels can include whole/half/quarter numbers and the middle of consolidation areas."
    },
    {
      "source_id": "6c5ed85f-870f-4866-b229-74bef283738e",
      "citation_number": 11,
      "cited_text": "Sonic R là gì? Sonic R là chỉ báo tương tự như một vùng hỗ trợ kháng cự kết hợp với các đường EMA, bao gồm EMA34, EMA89 và EMA200. Đây là chỉ báo được phát triển bởi một nhà giao dịch người Singapore có tên là Sonicdeejay. Thế nên, hệ thống Sonic R sẽ có các tính chất giống với đường EMA: Đường giá nằm trên đường Sonic R thể hiện cho xu hướng tăng và đường giá nằm dưới đường Sonic R thể hiện cho xu hướng giảm. (Trend) Giá dịch chuyển ra xa chỉ báo Sonic R sẽ có xu hướng hội tụ lại với đường EMA. Khi đường giá phá qua đường EMA có hành động quay lại test. (Hỗ trợ và kháng cự)"
    },
    {
      "source_id": "3e353cb4-2ae2-4d42-acde-161f23b5f49e",
      "citation_number": 12,
      "cited_text": "Trade Levels This replaces the need for MT4 trade level lines. Based on manually input values, the indicator provides lines for EPs, average of EPs, TPs and SLs. The lines are color coded, include price labels, and make for a cleaner chart. The placement of lines and labels is determined by the chart zoom setting used in either the Filled Dragon indicator or the PVA Candles indicator. Sonic R. System Trades and PVSRA Sonic R. System Trades The entry for the Sonic R. System setup is called a “Classic” entry. After the initial Classic entry, there are sometimes pullbacks which set up the opportunity for “re-entries”. There are at times early in a price reversal that a Classic setup has not yet formed but price action alone suggests an entry opportunity. Such an early entry to a reversal is called a “Scout” entry, and two examples of pure price action that support a Scout entry are: 1) a suitable pattern of H/Ls, and 2) a break out from a consolidation area. The least risky application of the Sonic R. System is to use PVSRA to determine if the price moving entities are bulls or bears and have turned the price to start making profits, and then trade Classics and Scouts only in that appropriate direction."
    },
    {
      "source_id": "9499c9a0-2cf8-401e-b63a-e53744214434",
      "citation_number": 13,
      "cited_text": "//Indicators- Trend if(Trend_On) { SetIndexBuffer(6, Trend1); SetIndexStyle(6, DRAW_LINE); SetIndexBuffer(7, Trend2); SetIndexStyle(7, DRAW_LINE); } //Indicator ShortName ShortName = \"SonicR Filled Dragon\"; if(!Trend_On) { ShortName = ShortName + \" [\"+Dragon_Period+Dragontype +\" - Trend is off]  \"; } else { ShortName = ShortName + \" [\"+Dragon_Period+Dragontype +\" - \"+Trend_Period+Trendtype+\"]  \"; } IndicatorShortName (ShortName); return(0); } //+-------------------------------------------------------------------------------------------+ //| Indicator De-initialization                                                               | //+-------------------------------------------------------------------------------------------+ int deinit() { return(0); }"
    },
    {
      "source_id": "ef17e6e4-86ed-4596-8c71-f669d624cbd6",
      "citation_number": 14,
      "cited_text": "…. string actInfoIndicadores() { dragon_max=iCustom(NULL, 0, indName, 0, 1); dragon_min=iCustom(NULL, 0, indName, 1, 1); dragon=iCustom(NULL, 0, indName, 4, 1); trend=iCustom(NULL, 0, indName, 5, 1); } [TBODY] [/TBODY] Logic quyết định, bao gồm giao điểm của các chỉ báo và góc giao cắt của chúng: int start() { … if(ticket==0) { if (dragon_min > trend && (ordAbierta== \"OP_SELL\" || primeraOP == true) && anguloCorrecto(\"BUY\") == true && DiffPrecioActual(\"BUY\")== true ) { primeraOP = false;"
    }
  ]
}
