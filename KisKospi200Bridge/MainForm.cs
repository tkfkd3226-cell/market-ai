using System;
using System.ComponentModel;
using System.Drawing;
using System.Globalization;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using AxITGExpertCtlLib;

namespace KisKospi200Bridge
{
    public sealed class MainForm : Form
    {
        private const string MarketAiBaseUrl = "http://127.0.0.1:8001";
        private const int ForwardIntervalSeconds = 5;
        private const int HeartbeatIntervalSeconds = 10;
        private const int RouteResolveIntervalSeconds = 5;

        private readonly HttpClient httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
        private readonly System.Windows.Forms.Timer sessionTimer = new System.Windows.Forms.Timer();

        private AxITGExpertCtl axTrade;
        private TextBox txtCode;
        private ComboBox cmbService;
        private Button btnStart;
        private Button btnStop;
        private Label lblStatus;
        private Label lblResolvedService;
        private Label lblTime;
        private Label lblPrice;
        private Label lblChangeRate;
        private Label lblVolume;
        private Label lblAsk;
        private Label lblBid;
        private Label lblTickCount;
        private Label lblMarketAi;
        private TextBox txtLog;

        private string activeService = "";
        private string activeCode = "";
        private bool monitoringRequested;
        private long tickCount;
        private long forwardSuccessCount;
        private int forwardInFlight;
        private int routeResolveInFlight;
        private DateTime lastForwardAttemptUtc = DateTime.MinValue;
        private DateTime lastHeartbeatAttemptUtc = DateTime.MinValue;
        private DateTime lastRouteResolveAttemptUtc = DateTime.MinValue;
        private DateTime? lastTickUtc;
        private string lastForwardError = "";
        private string autoResolvedCode = "";
        private string autoResolvedService = "";
        private string autoResolvedSession = "closed";
        private bool autoRouteResolved;
        private DateTime lastForwardErrorLogUtc = DateTime.MinValue;

        public MainForm()
        {
            InitializeComponent();
            cmbService.SelectedIndex = 0;
            sessionTimer.Interval = 5000;
            sessionTimer.Tick += SessionTimer_Tick;
            sessionTimer.Start();
            AppendLog("Bridge ready. eFriend Expert 로그인 상태에서 실시간 수신이 자동 시작됩니다.");
        }

        private void InitializeComponent()
        {
            var resources = new ComponentResourceManager(typeof(MainForm));
            axTrade = new AxITGExpertCtl();
            txtCode = new TextBox();
            cmbService = new ComboBox();
            btnStart = new Button();
            btnStop = new Button();
            lblStatus = new Label();
            lblResolvedService = new Label();
            lblTime = new Label();
            lblPrice = new Label();
            lblChangeRate = new Label();
            lblVolume = new Label();
            lblAsk = new Label();
            lblBid = new Label();
            lblTickCount = new Label();
            lblMarketAi = new Label();
            txtLog = new TextBox();

            ((ISupportInitialize)axTrade).BeginInit();
            SuspendLayout();

            Text = "KIS eFriend KOSPI200 Futures Bridge - Stage 2";
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(760, 520);
            MinimumSize = new Size(780, 560);
            Font = new Font("Malgun Gothic", 9F, FontStyle.Regular, GraphicsUnit.Point, 129);

            var title = NewLabel("KOSPI200 선물 → Market AI 실시간 Bridge", 18, 18, 560, 28, 14F, true);
            var note = NewLabel("주문 기능 없음 · eFriend Expert 실시간 수신 · Market AI localhost:8001 전송", 18, 50, 680, 22, 9F, false);
            note.ForeColor = Color.DimGray;

            Controls.Add(NewLabel("종목코드", 18, 88, 80, 24, 9F, true));
            txtCode.Location = new Point(102, 86);
            txtCode.Size = new Size(130, 25);
            txtCode.Text = "AUTO";
            txtCode.CharacterCasing = CharacterCasing.Upper;
            Controls.Add(txtCode);

            Controls.Add(NewLabel("서비스", 260, 88, 65, 24, 9F, true));
            cmbService.Location = new Point(326, 86);
            cmbService.Size = new Size(160, 25);
            cmbService.DropDownStyle = ComboBoxStyle.DropDownList;
            cmbService.Items.AddRange(new object[] { "AUTO", "FC_R (주간)", "CMEC_R (야간)" });
            Controls.Add(cmbService);

            btnStart.Location = new Point(510, 84);
            btnStart.Size = new Size(105, 29);
            btnStart.Text = "실시간 시작";
            btnStart.Click += BtnStart_Click;
            Controls.Add(btnStart);

            btnStop.Location = new Point(625, 84);
            btnStop.Size = new Size(105, 29);
            btnStop.Text = "중지";
            btnStop.Enabled = false;
            btnStop.Click += BtnStop_Click;
            Controls.Add(btnStop);

            var box = new GroupBox();
            box.Text = "실시간 상태";
            box.Location = new Point(18, 128);
            box.Size = new Size(712, 210);
            Controls.Add(box);

            box.Controls.Add(NewLabel("상태", 18, 30, 80, 24, 9F, true));
            lblStatus = NewValueLabel("대기", 110, 30, 220, 24);
            box.Controls.Add(lblStatus);
            box.Controls.Add(NewLabel("구독 서비스", 360, 30, 100, 24, 9F, true));
            lblResolvedService = NewValueLabel("-", 470, 30, 210, 24);
            box.Controls.Add(lblResolvedService);

            box.Controls.Add(NewLabel("영업시간", 18, 68, 80, 24, 9F, true));
            lblTime = NewValueLabel("-", 110, 68, 220, 24);
            box.Controls.Add(lblTime);
            box.Controls.Add(NewLabel("현재가", 360, 68, 80, 24, 9F, true));
            lblPrice = NewValueLabel("-", 470, 68, 210, 24, 13F, true);
            box.Controls.Add(lblPrice);

            box.Controls.Add(NewLabel("전일대비율", 18, 106, 90, 24, 9F, true));
            lblChangeRate = NewValueLabel("-", 110, 106, 220, 24);
            box.Controls.Add(lblChangeRate);
            box.Controls.Add(NewLabel("누적거래량", 360, 106, 90, 24, 9F, true));
            lblVolume = NewValueLabel("-", 470, 106, 210, 24);
            box.Controls.Add(lblVolume);

            box.Controls.Add(NewLabel("매도1", 18, 144, 80, 24, 9F, true));
            lblAsk = NewValueLabel("-", 110, 144, 220, 24);
            box.Controls.Add(lblAsk);
            box.Controls.Add(NewLabel("매수1", 360, 144, 80, 24, 9F, true));
            lblBid = NewValueLabel("-", 470, 144, 210, 24);
            box.Controls.Add(lblBid);

            box.Controls.Add(NewLabel("수신 Tick", 18, 176, 80, 24, 9F, true));
            lblTickCount = NewValueLabel("0", 110, 176, 220, 24);
            box.Controls.Add(lblTickCount);
            box.Controls.Add(NewLabel("Market AI", 360, 176, 90, 24, 9F, true));
            lblMarketAi = NewValueLabel("대기", 470, 176, 210, 24);
            box.Controls.Add(lblMarketAi);

            txtLog.Location = new Point(18, 354);
            txtLog.Size = new Size(712, 145);
            txtLog.Multiline = true;
            txtLog.ScrollBars = ScrollBars.Vertical;
            txtLog.ReadOnly = true;
            txtLog.Font = new Font("Consolas", 9F);
            Controls.Add(txtLog);

            axTrade.Enabled = true;
            axTrade.Location = new Point(736, 502);
            axTrade.Name = "axTrade";
            axTrade.OcxState = (AxHost.State)resources.GetObject("axTrade.OcxState");
            axTrade.Size = new Size(12, 12);
            axTrade.TabIndex = 99;
            axTrade.ReceiveRealData += AxTrade_ReceiveRealData;
            Controls.Add(axTrade);

            Controls.Add(title);
            Controls.Add(note);
            Shown += MainForm_Shown;
            FormClosing += MainForm_FormClosing;

            ((ISupportInitialize)axTrade).EndInit();
            ResumeLayout(false);
            PerformLayout();
        }

        private static Label NewLabel(string text, int x, int y, int w, int h, float size, bool bold)
        {
            return new Label
            {
                AutoSize = false,
                Text = text,
                Location = new Point(x, y),
                Size = new Size(w, h),
                Font = new Font("Malgun Gothic", size, bold ? FontStyle.Bold : FontStyle.Regular, GraphicsUnit.Point, 129),
                TextAlign = ContentAlignment.MiddleLeft
            };
        }

        private static Label NewValueLabel(string text, int x, int y, int w, int h, float size = 9F, bool bold = false)
        {
            var label = NewLabel(text, x, y, w, h, size, bold);
            label.BorderStyle = BorderStyle.FixedSingle;
            label.BackColor = Color.WhiteSmoke;
            label.Padding = new Padding(5, 0, 0, 0);
            return label;
        }

        private async void MainForm_Shown(object sender, EventArgs e)
        {
            await Task.Delay(800);
            if (IsDisposed || Disposing || monitoringRequested || !btnStart.Enabled) return;
            AppendLog("AUTO START - 실시간 수신을 자동으로 시작합니다.");
            StartMonitoring(false);
        }

        private void BtnStart_Click(object sender, EventArgs e)
        {
            StartMonitoring(true);
        }

        private void StartMonitoring(bool showValidationMessage)
        {
            if (monitoringRequested) return;

            var code = (txtCode.Text ?? "").Trim().ToUpperInvariant();
            if (code.Length == 0)
            {
                if (showValidationMessage)
                    MessageBox.Show("AUTO 또는 선물 종목코드를 입력해 주세요.", "KIS Bridge", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                else
                    AppendLog("AUTO START SKIP - 종목코드가 비어 있습니다.");
                return;
            }

            monitoringRequested = true;
            activeCode = "";
            tickCount = 0;
            forwardSuccessCount = 0;
            lblTickCount.Text = "0";
            lblMarketAi.Text = "연결 대기";
            btnStart.Enabled = false;
            btnStop.Enabled = true;
            txtCode.Enabled = false;
            cmbService.Enabled = false;

            autoRouteResolved = false;
            if (NeedsAutoRoute())
                _ = RefreshAutoRouteAsync(true);
            else
            {
                EnsureSubscription();
                _ = SendHeartbeatAsync();
            }
        }

        private void BtnStop_Click(object sender, EventArgs e)
        {
            monitoringRequested = false;
            StopSubscription(true, true);
            lblMarketAi.Text = "중지";
        }

        private void SessionTimer_Tick(object sender, EventArgs e)
        {
            if (!monitoringRequested) return;

            if (NeedsAutoRoute() &&
                (DateTime.UtcNow - lastRouteResolveAttemptUtc).TotalSeconds >= RouteResolveIntervalSeconds)
                _ = RefreshAutoRouteAsync(false);

            EnsureSubscription();
            if ((DateTime.UtcNow - lastHeartbeatAttemptUtc).TotalSeconds >= HeartbeatIntervalSeconds)
                _ = SendHeartbeatAsync();
        }

        private void EnsureSubscription()
        {
            var desired = ResolveService();
            var desiredCode = ResolveInstrumentCode();

            if ((IsAutoInstrumentRequested() && string.IsNullOrWhiteSpace(desiredCode)) ||
                (IsAutoServiceRequested() && !autoRouteResolved))
            {
                if (!string.IsNullOrEmpty(activeService))
                    StopSubscription(false, false);
                lblStatus.Text = "시장 정책 확인 중";
                lblResolvedService.Text = "- / AUTO";
                return;
            }

            if (desired == null)
            {
                if (!string.IsNullOrEmpty(activeService))
                    StopSubscription(false, false);
                activeCode = desiredCode;
                lblStatus.Text = "장외 대기";
                lblResolvedService.Text = "- / " + desiredCode;
                return;
            }

            if (string.Equals(activeService, desired, StringComparison.Ordinal) &&
                string.Equals(activeCode, desiredCode, StringComparison.Ordinal)) return;

            if (!string.IsNullOrEmpty(activeService))
                StopSubscription(false, false);

            Subscribe(desired, desiredCode);
        }

        private void Subscribe(string service, string code)
        {
            try
            {
                activeService = service;
                activeCode = code;
                lblResolvedService.Text = service + " / " + code;
                lblStatus.Text = "구독 요청됨";
                axTrade.RequestRealData(service, code);
                AppendLog("SUBSCRIBE " + service + " / " + code + " - ReceiveRealData 대기");
            }
            catch (Exception ex)
            {
                activeService = "";
                lblStatus.Text = "구독 실패";
                AppendLog("ERROR RequestRealData: " + ex.GetType().Name + " - " + ex.Message);
            }
        }

        private string ResolveService()
        {
            var selected = Convert.ToString(cmbService.SelectedItem) ?? "AUTO";
            if (selected.StartsWith("FC_R", StringComparison.Ordinal)) return "FC_R";
            if (selected.StartsWith("CMEC_R", StringComparison.Ordinal)) return "CMEC_R";
            if (!autoRouteResolved || string.Equals(autoResolvedSession, "closed", StringComparison.Ordinal)) return null;
            return autoResolvedService;
        }

        private bool IsAutoServiceRequested()
        {
            var selected = Convert.ToString(cmbService.SelectedItem) ?? "AUTO";
            return string.Equals(selected, "AUTO", StringComparison.Ordinal);
        }

        private bool NeedsAutoRoute()
        {
            return IsAutoInstrumentRequested() || IsAutoServiceRequested();
        }

        private bool IsAutoInstrumentRequested()
        {
            var requested = (txtCode.Text ?? "AUTO").Trim().ToUpperInvariant();
            return string.Equals(requested, "AUTO", StringComparison.Ordinal);
        }

        private string ResolveInstrumentCode()
        {
            var requested = (txtCode.Text ?? "AUTO").Trim().ToUpperInvariant();
            if (!string.Equals(requested, "AUTO", StringComparison.Ordinal))
                return requested;
            return autoResolvedCode;
        }

        private async Task RefreshAutoRouteAsync(bool force)
        {
            if (!NeedsAutoRoute()) return;
            if (!force && (DateTime.UtcNow - lastRouteResolveAttemptUtc).TotalSeconds < RouteResolveIntervalSeconds) return;
            if (Interlocked.CompareExchange(ref routeResolveInFlight, 1, 0) != 0) return;
            lastRouteResolveAttemptUtc = DateTime.UtcNow;

            try
            {
                using (var response = await httpClient.GetAsync(MarketAiBaseUrl + "/api/bridge/kis-efriend/route-code"))
                {
                    if (!response.IsSuccessStatusCode)
                    {
                        var body = await response.Content.ReadAsStringAsync();
                        InvalidateAutoRoute("route HTTP " + (int)response.StatusCode + " " + body);
                        return;
                    }

                    var raw = (await response.Content.ReadAsStringAsync()).Trim();
                    var parts = raw.Split('|');
                    if (parts.Length != 3)
                    {
                        InvalidateAutoRoute("route invalid payload: " + raw);
                        return;
                    }

                    var code = parts[0].Trim().ToUpperInvariant();
                    var serviceToken = parts[1].Trim().ToUpperInvariant();
                    var session = parts[2].Trim().ToLowerInvariant();
                    var service = serviceToken == "CLOSED" ? "" : serviceToken;
                    var validService =
                        (service == "FC_R" && session == "day") ||
                        (service == "CMEC_R" && session == "night") ||
                        (service.Length == 0 && session == "closed");

                    if (string.IsNullOrWhiteSpace(code) || code.Length > 9 || !validService)
                    {
                        InvalidateAutoRoute("route invalid policy: " + raw);
                        return;
                    }

                    var previousCode = autoResolvedCode;
                    var previousService = autoResolvedService;
                    var previousSession = autoResolvedSession;
                    var changed =
                        !autoRouteResolved ||
                        !string.Equals(previousCode, code, StringComparison.Ordinal) ||
                        !string.Equals(previousService, service, StringComparison.Ordinal) ||
                        !string.Equals(previousSession, session, StringComparison.Ordinal);

                    autoResolvedCode = code;
                    autoResolvedService = service;
                    autoResolvedSession = session;
                    autoRouteResolved = true;
                    lastForwardError = "";

                    SafeUi(() =>
                    {
                        if (changed)
                        {
                            var routeLabel = service.Length == 0 ? "CLOSED" : service;
                            AppendLog("ROUTE " + code + " / " + routeLabel + " / " + session + " (Market AI policy)");
                        }
                        EnsureSubscription();
                        _ = SendHeartbeatAsync();
                    });
                }
            }
            catch (Exception ex)
            {
                InvalidateAutoRoute("route " + ex.GetType().Name + " - " + ex.Message);
            }
            finally
            {
                Interlocked.Exchange(ref routeResolveInFlight, 0);
            }
        }

        private void InvalidateAutoRoute(string message)
        {
            autoRouteResolved = false;
            autoResolvedCode = "";
            autoResolvedService = "";
            autoResolvedSession = "closed";
            MarkForwardError(message);
            SafeUi(() =>
            {
                if (!string.IsNullOrEmpty(activeService))
                    StopSubscription(false, false);
                lblStatus.Text = "시장 정책 확인 중";
                lblResolvedService.Text = "- / AUTO";
            });
        }

        private void AxTrade_ReceiveRealData(object sender, EventArgs e)
        {
            try
            {
                // FC_R / CMEC_R are intentionally parsed with the same indexes confirmed in Expert Viewer.
                var code = Read(0);
                var time = Read(1);
                var rate = Read(4);
                var price = Read(5);
                var volume = Read(10);
                var ask = Read(34);
                var bid = Read(35);

                tickCount++;
                lastTickUtc = DateTime.UtcNow;
                lblStatus.Text = "수신 중";
                lblTime.Text = FormatBusinessTime(time);
                lblPrice.Text = FormatNumber(price, 2);
                lblChangeRate.Text = FormatSignedPercent(rate);
                lblVolume.Text = FormatInteger(volume);
                lblAsk.Text = FormatNumber(ask, 2);
                lblBid.Text = FormatNumber(bid, 2);
                lblTickCount.Text = tickCount.ToString("N0", CultureInfo.InvariantCulture);

                if (tickCount <= 5 || tickCount % 100 == 0)
                    AppendLog("TICK " + tickCount + " " + code + " " + time + " price=" + price + " rate=" + rate + "% vol=" + volume + " ask=" + ask + " bid=" + bid);

                if ((DateTime.UtcNow - lastForwardAttemptUtc).TotalSeconds >= ForwardIntervalSeconds)
                {
                    var snapshot = BuildTickSnapshot(code, time, price, rate, volume, ask, bid);
                    if (snapshot != null)
                        _ = SendTickAsync(snapshot);
                }
            }
            catch (Exception ex)
            {
                lblStatus.Text = "수신 파싱 오류";
                AppendLog("ERROR ReceiveRealData: " + ex.GetType().Name + " - " + ex.Message);
            }
        }

        private TickSnapshot BuildTickSnapshot(string code, string businessTime, string price, string rate, string volume, string ask, string bid)
        {
            double numericPrice;
            if (!double.TryParse(price, NumberStyles.Any, CultureInfo.InvariantCulture, out numericPrice) || numericPrice <= 0)
                return null;

            return new TickSnapshot
            {
                Code = string.IsNullOrWhiteSpace(code) ? activeCode : code.Trim().ToUpperInvariant(),
                Service = activeService,
                Session = string.Equals(activeService, "FC_R", StringComparison.Ordinal) ? "day" : "night",
                BusinessTime = businessTime,
                Price = numericPrice,
                ChangePct = ParseNullableDouble(rate),
                Volume = ParseNullableLong(volume),
                Ask1 = ParseNullableDouble(ask),
                Bid1 = ParseNullableDouble(bid),
                TickCount = tickCount,
                SentAtUtc = DateTime.UtcNow
            };
        }

        private async Task SendTickAsync(TickSnapshot tick)
        {
            if (Interlocked.CompareExchange(ref forwardInFlight, 1, 0) != 0) return;
            lastForwardAttemptUtc = DateTime.UtcNow;

            try
            {
                var json = BuildTickJson(tick);
                using (var content = new StringContent(json, Encoding.UTF8, "application/json"))
                using (var response = await httpClient.PostAsync(MarketAiBaseUrl + "/api/bridge/kis-efriend/tick", content))
                {
                    if (!response.IsSuccessStatusCode)
                    {
                        var body = await response.Content.ReadAsStringAsync();
                        MarkForwardError("HTTP " + (int)response.StatusCode + " " + body);
                        return;
                    }
                }

                forwardSuccessCount++;
                lastForwardError = "";
                SafeUi(() => lblMarketAi.Text = "연결됨 · " + forwardSuccessCount.ToString("N0", CultureInfo.InvariantCulture) + "건");
                if (forwardSuccessCount <= 3 || forwardSuccessCount % 50 == 0)
                    SafeUi(() => AppendLog("MARKET AI OK tick=" + tick.TickCount + " price=" + tick.Price.ToString("0.00", CultureInfo.InvariantCulture)));
            }
            catch (Exception ex)
            {
                MarkForwardError(ex.GetType().Name + " - " + ex.Message);
            }
            finally
            {
                Interlocked.Exchange(ref forwardInFlight, 0);
            }
        }

        private async Task SendHeartbeatAsync()
        {
            lastHeartbeatAttemptUtc = DateTime.UtcNow;
            var desired = ResolveService();
            var service = string.IsNullOrEmpty(activeService) ? desired : activeService;
            var session = service == "FC_R" ? "day" : service == "CMEC_R" ? "night" : "closed";
            if (IsAutoServiceRequested() && autoRouteResolved && string.IsNullOrEmpty(activeService))
                session = autoResolvedSession;

            var heartbeatCode = string.IsNullOrWhiteSpace(activeCode) ? ResolveInstrumentCode() : activeCode;
            if (string.IsNullOrWhiteSpace(heartbeatCode)) return;
            var json = BuildHeartbeatJson(
                heartbeatCode,
                service,
                session,
                tickCount,
                lastTickUtc
            );

            try
            {
                using (var content = new StringContent(json, Encoding.UTF8, "application/json"))
                using (var response = await httpClient.PostAsync(MarketAiBaseUrl + "/api/bridge/kis-efriend/heartbeat", content))
                {
                    if (!response.IsSuccessStatusCode)
                    {
                        var body = await response.Content.ReadAsStringAsync();
                        MarkForwardError("heartbeat HTTP " + (int)response.StatusCode + " " + body);
                    }
                }
            }
            catch (Exception ex)
            {
                MarkForwardError("heartbeat " + ex.GetType().Name + " - " + ex.Message);
            }
        }

        private void MarkForwardError(string message)
        {
            SafeUi(() => lblMarketAi.Text = "연결 오류");
            var now = DateTime.UtcNow;
            if (!string.Equals(lastForwardError, message, StringComparison.Ordinal) || (now - lastForwardErrorLogUtc).TotalSeconds >= 30)
            {
                lastForwardError = message;
                lastForwardErrorLogUtc = now;
                SafeUi(() => AppendLog("MARKET AI ERROR " + message));
            }
        }

        private static string BuildTickJson(TickSnapshot tick)
        {
            return "{" +
                   "\"instrument_code\":\"" + JsonEscape(tick.Code) + "\"," +
                   "\"service\":\"" + JsonEscape(tick.Service) + "\"," +
                   "\"session\":\"" + JsonEscape(tick.Session) + "\"," +
                   "\"business_time\":\"" + JsonEscape(tick.BusinessTime) + "\"," +
                   "\"price\":" + tick.Price.ToString("R", CultureInfo.InvariantCulture) + "," +
                   "\"change_pct\":" + JsonNullable(tick.ChangePct) + "," +
                   "\"cumulative_volume\":" + JsonNullable(tick.Volume) + "," +
                   "\"ask1\":" + JsonNullable(tick.Ask1) + "," +
                   "\"bid1\":" + JsonNullable(tick.Bid1) + "," +
                   "\"sent_at\":\"" + tick.SentAtUtc.ToString("o", CultureInfo.InvariantCulture) + "\"," +
                   "\"tick_count\":" + tick.TickCount.ToString(CultureInfo.InvariantCulture) +
                   "}";
        }

        private static string BuildHeartbeatJson(string code, string service, string session, long ticks, DateTime? lastTick)
        {
            return "{" +
                   "\"instrument_code\":\"" + JsonEscape(code) + "\"," +
                   "\"service\":" + (service == null ? "null" : "\"" + JsonEscape(service) + "\"") + "," +
                   "\"session\":\"" + JsonEscape(session) + "\"," +
                   "\"bridge_time\":\"" + DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture) + "\"," +
                   "\"last_tick_at\":" + (lastTick.HasValue ? "\"" + lastTick.Value.ToString("o", CultureInfo.InvariantCulture) + "\"" : "null") + "," +
                   "\"tick_count\":" + ticks.ToString(CultureInfo.InvariantCulture) +
                   "}";
        }

        private static string JsonEscape(string value)
        {
            return (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
        }

        private static string JsonNullable(double? value)
        {
            return value.HasValue ? value.Value.ToString("R", CultureInfo.InvariantCulture) : "null";
        }

        private static string JsonNullable(long? value)
        {
            return value.HasValue ? value.Value.ToString(CultureInfo.InvariantCulture) : "null";
        }

        private static double? ParseNullableDouble(string value)
        {
            double parsed;
            return double.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out parsed) ? parsed : (double?)null;
        }

        private static long? ParseNullableLong(string value)
        {
            long parsed;
            return long.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out parsed) ? parsed : (long?)null;
        }

        private void SafeUi(Action action)
        {
            if (IsDisposed || Disposing) return;
            if (InvokeRequired)
            {
                try { BeginInvoke(action); } catch { }
                return;
            }
            action();
        }

        private string Read(short index)
        {
            return Convert.ToString(axTrade.GetSingleData(index, 0), CultureInfo.InvariantCulture)?.Trim() ?? "";
        }

        private void StopSubscription(bool writeLog, bool resetControls)
        {
            if (!string.IsNullOrEmpty(activeService) && !string.IsNullOrEmpty(activeCode))
            {
                try
                {
                    axTrade.UnRequestRealData(activeService, activeCode);
                    if (writeLog) AppendLog("UNSUBSCRIBE " + activeService + " / " + activeCode);
                }
                catch (Exception ex)
                {
                    if (writeLog) AppendLog("WARN UnRequestRealData: " + ex.Message);
                }
            }

            activeService = "";
            if (resetControls)
            {
                lblStatus.Text = "중지";
                lblResolvedService.Text = "-";
                btnStart.Enabled = true;
                btnStop.Enabled = false;
                txtCode.Enabled = true;
                cmbService.Enabled = true;
            }
        }

        private void MainForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            monitoringRequested = false;
            sessionTimer.Stop();
            try { axTrade.UnRequestAllRealData(); } catch { }
            httpClient.Dispose();
        }

        private void AppendLog(string text)
        {
            var line = DateTime.Now.ToString("HH:mm:ss.fff", CultureInfo.InvariantCulture) + "  " + text + Environment.NewLine;
            txtLog.AppendText(line);
            txtLog.SelectionStart = txtLog.TextLength;
            txtLog.ScrollToCaret();
        }

        private static string FormatBusinessTime(string value)
        {
            if (value.Length == 6)
                return value.Substring(0, 2) + ":" + value.Substring(2, 2) + ":" + value.Substring(4, 2);
            return string.IsNullOrWhiteSpace(value) ? "-" : value;
        }

        private static string FormatSignedPercent(string value)
        {
            double number;
            if (double.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out number))
                return (number > 0 ? "+" : "") + number.ToString("N2", CultureInfo.InvariantCulture) + "%";
            return string.IsNullOrWhiteSpace(value) ? "-" : value;
        }

        private static string FormatNumber(string value, int decimals)
        {
            double number;
            if (double.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out number))
                return number.ToString("N" + decimals, CultureInfo.InvariantCulture);
            return string.IsNullOrWhiteSpace(value) ? "-" : value;
        }

        private static string FormatInteger(string value)
        {
            long number;
            if (long.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out number))
                return number.ToString("N0", CultureInfo.InvariantCulture);
            return string.IsNullOrWhiteSpace(value) ? "-" : value;
        }

        private sealed class TickSnapshot
        {
            public string Code { get; set; }
            public string Service { get; set; }
            public string Session { get; set; }
            public string BusinessTime { get; set; }
            public double Price { get; set; }
            public double? ChangePct { get; set; }
            public long? Volume { get; set; }
            public double? Ask1 { get; set; }
            public double? Bid1 { get; set; }
            public long TickCount { get; set; }
            public DateTime SentAtUtc { get; set; }
        }
    }
}
