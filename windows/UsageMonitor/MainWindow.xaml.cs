using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using static UsageMonitor.Strings;

namespace UsageMonitor;

/// <summary>The panel: the same sections, tables and behaviour as src/usage_monitor/web/panel.html.</summary>
partial class MainWindow : Window
{
    const double CompactBelow = 620;  // the panel's compact media query
    const double WrapToolsBelow = 1000;  // the header's buttons go to their own line, like its flex-wrap

    readonly Api api;
    readonly DispatcherTimer toastTimer = new() { Interval = TimeSpan.FromSeconds(4.5) };
    bool compact, refreshing;
    double? pctWidth;

    public Payload? Data { get; private set; }
    public bool Online { get; private set; }
    /// <summary>A Strings key that explains why there is no server (not found, could not start).</summary>
    public string? Problem { get; set; }
    /// <summary>Closing only hides the window to the tray, unless the app is quitting.</summary>
    public bool Quitting { get; set; }
    /// <summary>After every load or action: the tray follows it.</summary>
    public event Action? Changed;

    public MainWindow(Api api)
    {
        this.api = api;
        InitializeComponent();
        toastTimer.Tick += (_, _) =>
        {
            toastTimer.Stop();
            ToastBox.BeginAnimation(OpacityProperty, new DoubleAnimation(0, TimeSpan.FromMilliseconds(150)));
        };
        Root.SizeChanged += (_, _) =>
        {
            var now = Root.ActualWidth < CompactBelow;
            ApplyLayout();
            if (now == compact) return;
            compact = now;
            ApplyLayout();
            if (Data != null) Render();
        };
        Language = System.Windows.Markup.XmlLanguage.GetLanguage("en-US");
        RefreshButton.Content = T("refresh");
        SwitchBestButton.Content = T("noBest");
    }

    // ---- data ----

    public async Task<bool> Load()
    {
        try
        {
            Show(await api.Get());
            return true;
        }
        catch (Exception e) when (IsNetwork(e))
        {
            Online = false;
            Status.Visibility = Visibility.Visible;  // in the compact layout too: being offline matters
            Dot.Fill = B("Bad");
            StatusText.Foreground = B("Bad");
            StatusText.Text = T(Problem ?? "offline");
            Changed?.Invoke();
            return false;
        }
    }

    public async Task Act(string path, object body, Func<Payload, string>? done = null)
    {
        try
        {
            var d = await api.Post(path, body);
            Show(d);
            if (done != null) Toast(done(d));
        }
        catch (Exception e) when (IsNetwork(e))
        {
            Toast(e is ApiException ? e.Message : T("offline"));
            if (Data != null) Render();  // undo the toggle a failed option click left behind
        }
    }

    static bool IsNetwork(Exception e) => e is ApiException or HttpRequestException or TaskCanceledException or JsonException;

    void Show(Payload d)
    {
        Data = d;
        Online = true;
        Strings.Lang = d.Lang;
        Render();
        Changed?.Invoke();
    }

    public static string Switched(Payload d) =>
        d.Claude.FirstOrDefault(c => c.Current) is { } c ? T("toastSwitch", ("n", c.N), ("email", c.Email)) : "";

    public Task SwitchTo(int? n) => Act("/api/switch", n is { } v ? new { n = v } : new { }, Switched);

    public async Task Refresh()
    {
        if (refreshing) return;
        refreshing = true;
        RefreshButton.IsEnabled = false;
        RefreshButton.Content = T("refreshing");
        await Act("/api/refresh", new { });
        refreshing = false;
        RefreshButton.IsEnabled = true;
        RefreshButton.Content = T("refresh");
    }

    void OnRefresh(object sender, RoutedEventArgs e) => _ = Refresh();
    void OnSwitchBest(object sender, RoutedEventArgs e) => _ = SwitchTo(null);
    void OnAlertSwitch(object sender, RoutedEventArgs e) => _ = SwitchTo((int)AlertButton.Tag);

    // ---- rendering ----

    void Render()
    {
        var d = Data!;
        Language = System.Windows.Markup.XmlLanguage.GetLanguage(Culture.Name);  // picks CJK fallback fonts for zh
        var best = d.Claude.FirstOrDefault(c => c.N == d.Best);
        var cur = d.Claude.FirstOrDefault(c => c.Current);

        DemoTag.Visibility = d.Demo ? Visibility.Visible : Visibility.Collapsed;
        DemoText.Text = Upper(T("demo"));
        Langs.Children.Clear();
        foreach (var (code, name) in d.Languages)
            Langs.Children.Add(Option(name, code == Strings.Lang, () => Act("/api/prefs", new { language = code })));
        if (!refreshing) RefreshButton.Content = T("refresh");
        AccountsTitle.Text = Upper(T("secAccounts"));
        AccountsHint.Text = T("freeHint");
        ProvidersTitle.Text = Upper(T("secProviders"));
        DefaultsTitle.Text = Upper(T("secDefaults"));
        DefaultsHint.Text = T("defaultsHint");

        AccountsHost.Child = Scrollable(AccountsTable(d));
        ProvidersHost.Child = Scrollable(ProvidersTable(d));
        DefaultsHost.Child = SettingsList(d);

        SwitchBestButton.IsEnabled = best != null;
        SwitchBestButton.Content = best != null ? T("switchBest", ("n", best.N), ("p", R(best.Score))) : T("noBest");

        var hot = cur?.Rows?.Where(r => r.Blocking && r.Used >= d.AlertAt).OrderByDescending(r => r.Used).FirstOrDefault();
        Alert.Visibility = hot != null ? Visibility.Visible : Visibility.Collapsed;
        if (hot != null && cur != null)
        {
            AlertText.Inlines.Clear();
            AlertText.Inlines.Add(new Run(T("alertHead", ("n", cur.N), ("p", R(hot.Used)), ("label", hot.Label)))
            { FontWeight = FontWeights.SemiBold, Foreground = B("Bad") });
            AlertText.Inlines.Add(new Run("  " + (best != null ? T("alertBest", ("n", best.N), ("p", R(best.Score))) : T("alertNone"))));
            AlertButton.Visibility = best != null ? Visibility.Visible : Visibility.Collapsed;
            if (best != null)
            {
                AlertButton.Content = T("alertButton", ("n", best.N));
                AlertButton.Tag = best.N;
            }
        }

        var m = (int)Math.Round((DateTimeOffset.Now - d.Updated).TotalMinutes, MidpointRounding.AwayFromZero);
        Dot.Fill = B("Ok");
        StatusText.Foreground = B("Dim");
        StatusText.Text = $"{T("online")} · " + T("status",
            ("ago", m < 1 ? T("justNow") : T("minAgo", ("m", m))), ("m", d.Every / 60), ("p", d.AlertAt));
        ApplyLayout();
    }

    /// <summary>What the compact media query and the header's flex-wrap do in the web panel.</summary>
    void ApplyLayout()
    {
        var full = compact ? Visibility.Collapsed : Visibility.Visible;
        Main.Margin = compact ? new(12, 12, 12, 24) : new(20, 20, 20, 48);
        Header.Padding = compact ? new(0, 0, 0, 10) : new(0, 0, 0, 14);
        if (Online) Status.Visibility = full;
        Langs.Visibility = RefreshButton.Visibility = Defaults.Visibility = AccountsHint.Visibility = DefaultsHint.Visibility = full;
        AccountsHeading.Margin = ProvidersTitle.Margin = compact ? new(0, 18, 0, 6) : new(0, 30, 0, 8);
        var wrap = !compact && Root.ActualWidth < WrapToolsBelow;
        Grid.SetRow(Tools, wrap ? 1 : 0);
        Grid.SetColumn(Tools, wrap ? 0 : 1);
        Tools.Margin = wrap ? new(0, 12, 0, 0) : new(compact ? 8 : 20, 0, 0, 0);
        Tools.HorizontalAlignment = wrap ? HorizontalAlignment.Left : HorizontalAlignment.Right;
    }

    UIElement AccountsTable(Payload d)
    {
        if (d.Claude.Length == 0) return Empty(T("noSessions"));
        var labels = d.Claude.SelectMany(c => c.Rows ?? []).Select(r => r.Label).Distinct().ToList();
        var limitCols = Math.Max(1, labels.Count);
        var t = compact
            ? new Table(this, new(30), Star, new(112))
            : new Table(this, [GridLength.Auto, GridLength.Auto, GridLength.Auto, .. Enumerable.Repeat(Star, limitCols), GridLength.Auto]);
        t.Head(compact ? ["#", T("colAccount"), T("colFree")] : ["#", T("colAccount"), T("colPlan"), .. labels, ""]);

        foreach (var c in d.Claude)
        {
            var clickable = compact && !c.Current;
            t.Row(wash: c.Current ? B("AccentWash") : null,
                  click: clickable ? () => _ = SwitchTo(c.N) : null,
                  name: $"{T("use")} #{c.N} {c.Email}");
            t.Cell(Txt(c.N.ToString(CultureInfo.InvariantCulture), c.Current ? "Accent" : "Dim", bold: c.Current), 0, pad: t.Pad with { Right = 4 });

            var who = new StackPanel();
            who.Children.Add(NameText(c.Email, compact ? double.PositiveInfinity : 300));
            var tags = new WrapPanel();
            if (c.Current) tags.Children.Add(TagBox(T("tagActive"), true));
            if (c.N == d.Best && !compact) tags.Children.Add(TagBox(T("tagBest"), false));
            if (tags.Children.Count > 0) who.Children.Add(tags);
            t.Cell(who, 1);

            if (compact)
            {
                t.Cell(c.Error != null ? Txt(T("failed"), "Bad") : Free(c.Score), 2);
                continue;
            }
            t.Cell(Txt(c.Plan ?? "", "Dim"), 2);
            if (c.Error != null) t.Cell(Error(c.Error), 3, limitCols);
            else
                for (var i = 0; i < labels.Count; i++)
                    if (c.Rows!.FirstOrDefault(r => r.Label == labels[i]) is { } r) t.Cell(Limit(r), 3 + i);
            if (!c.Current)
            {
                var use = new Button { Content = T("use"), HorizontalAlignment = HorizontalAlignment.Right };
                AutomationProperties.SetName(use, $"{T("use")} #{c.N} {c.Email}");
                use.Click += (_, _) => _ = SwitchTo(c.N);
                t.Cell(use, 3 + limitCols);
            }
        }
        return t.Grid;
    }

    UIElement ProvidersTable(Payload d)
    {
        var t = compact
            ? new Table(this, Star, new(112))
            : new Table(this, GridLength.Auto, Star, GridLength.Auto, Star);
        t.Head(compact ? [T("colLimit"), T("colFree")] : [T("colSource"), T("colLimit"), T("colFree"), T("colResets")]);

        Source(t, "ChatGPT / Codex", d.Codex.Plan ?? "", d.Codex.Error,
            (d.Codex.Rows ?? []).Select(r => (r.Label, Free(r.Free), Countdown(r.Reset))));
        Source(t, "Antigravity", d.Antigravity.Plan ?? "", d.Antigravity.Error,
            (d.Antigravity.Rows ?? []).Select(r => ($"{r.Group} · {r.Label}", Free(r.Free), Countdown(r.Reset))));
        var ds = d.Deepseek;
        Source(t, "DeepSeek API", "", ds.Error, (ds.Balances ?? []).Select(b => (T("balance"),
            (FrameworkElement)Txt($"{Money(b.Total)} {b.Currency}", ds.Available ? "Ok" : "Bad", bold: true),
            ds.Available ? $"{T("toppedUp", ("v", Money(b.ToppedUp)))} · {T("granted", ("v", Money(b.Granted)))}" : T("noBalance"))));
        return t.Grid;
    }

    /// <summary>One row per limit. Full width: the source is a column, named once. Compact: it is a group row.</summary>
    void Source(Table t, string source, string note, string? error, IEnumerable<(string Limit, FrameworkElement Free, string Resets)> rows)
    {
        FrameworkElement Title()
        {
            var p = new StackPanel { Orientation = Orientation.Horizontal, ToolTip = string.IsNullOrEmpty(note) ? null : note };
            p.Children.Add(Txt(source, "Bright"));
            if (!string.IsNullOrEmpty(note) && !compact) p.Children.Add(Txt(note, "Dim", 12, margin: new(10, 0, 0, 0)));
            return p;
        }
        if (compact)
        {
            t.Row(pad: t.Pad with { Bottom = 0 });
            t.Cell(Title(), 0, 2);
        }
        if (error != null)
        {
            t.Row(rule: !compact);
            if (!compact) t.Cell(Title(), 0);
            t.Cell(Error(error), compact ? 0 : 1, compact ? 2 : 3);
            return;
        }
        var i = 0;
        foreach (var (limit, free, resets) in rows)
        {
            t.Row(rule: i == 0 && !compact, pad: i == 0 ? null : t.Pad with { Top = 0 });
            var col = 0;
            if (!compact) t.Cell(i == 0 ? Title() : new Border(), col++);
            t.Cell(Txt(limit), col++);
            t.Cell(free, col++);
            if (!compact) t.Cell(Txt(resets), col);
            i++;
        }
    }

    UIElement SettingsList(Payload d)
    {
        var list = new StackPanel();
        void Line(string term, params UIElement[] body)
        {
            var g = new Grid();
            g.ColumnDefinitions.Add(new() { Width = new(130) });
            g.ColumnDefinitions.Add(new() { Width = Star });
            var dt = Txt(Upper(term), "Dim", 11, margin: new(0, 5, 14, 0));
            dt.TextWrapping = TextWrapping.Wrap;
            var dd = new WrapPanel();
            foreach (var e in body) dd.Children.Add(e);
            Grid.SetColumn(dd, 1);
            g.Children.Add(dt);
            g.Children.Add(dd);
            list.Children.Add(new Border
            {
                Child = g, Padding = new(14, 8, 14, 8), BorderBrush = B("Line"),
                BorderThickness = new(0, list.Children.Count > 0 ? 1 : 0, 0, 0),
            });
        }
        FrameworkElement Hint(string text) => Txt(text, "Dim", 12, margin: new(10, 4, 0, 0), wrap: true);
        WrapPanel Options(IEnumerable<(string Id, string Label)> items, string? active, string key)
        {
            var p = new WrapPanel { Margin = new(0, 0, 6, 0) };
            AutomationProperties.SetName(p, key);
            foreach (var (id, label) in items)
                p.Children.Add(Option(label, id == active, () => Act("/api/settings", key == "model" ? new { model = id } : (object)new { effort = id },
                    p => T("toastSettings", ("model", ModelLabel(p.Settings)), ("effort", p.Settings?.Effort ?? "")))));
            return p;
        }

        var s = d.Settings;
        if (s is null || s.Error != null || s.Models is null || s.Efforts is null)
            Line(T("model"), Error(s?.Error ?? ""));
        else
        {
            Line(T("model"), Options(s.Models.Where(m => !m.More).Select(m => (m.Id, m.Label)), s.Model, "model"));
            Line(T("moreModels"), Options(s.Models.Where(m => m.More).Select(m => (m.Id, m.Label)), s.Model, "model"));
            Line(T("effort"), Options(s.Efforts.Select(e => (e, e)), s.Effort, "effort"), Hint(T("effortHint")));
        }
        var auto = new WrapPanel { Margin = new(0, 0, 6, 0) };
        foreach (var on in new[] { true, false })
            auto.Children.Add(Option(T(on ? "on" : "off"), on == d.AutoSwitch, () => Act("/api/prefs", new { auto_switch = on },
                p => T("toastAuto", ("state", T(p.AutoSwitch ? "on" : "off"))))));
        Line(T("autoSwitch"), auto, Hint(T("autoHint", ("p", d.AlertAt))));
        return list;
    }

    static string ModelLabel(Settings? s) => s?.Models?.FirstOrDefault(m => m.Id == s.Model)?.Label ?? s?.Model ?? "";

    // ---- pieces ----

    static readonly GridLength Star = new(1, GridUnitType.Star);
    public Thickness CellPad => compact ? new(10, 7, 10, 7) : new(14, 9, 14, 9);
    public Thickness HeadPad => compact ? new(10, 7, 10, 7) : new(14, 7, 14, 7);

    public Brush B(string key) => (Brush)FindResource(key);
    static string Upper(string s) => s.ToUpper(Culture);
    static int R(double v) => (int)Math.Round(v, MidpointRounding.AwayFromZero);
    static string Money(double v) => v.ToString("0.00", CultureInfo.InvariantCulture);
    static string Tone(double free) => free > 50 ? "Ok" : free > 20 ? "Warn" : "Bad";

    public TextBlock Txt(string text, string brush = "Text", double size = 13, bool bold = false, Thickness margin = default, bool wrap = false) => new()
    {
        Text = text, Foreground = B(brush), FontSize = size, Margin = margin,
        FontWeight = bold ? FontWeights.SemiBold : FontWeights.Normal,
        TextWrapping = wrap ? TextWrapping.Wrap : TextWrapping.NoWrap,
    };

    TextBlock NameText(string text, double max) => new()
    {
        Text = text, Foreground = B("Bright"), MaxWidth = max, TextTrimming = TextTrimming.CharacterEllipsis, ToolTip = text,
    };

    Border TagBox(string text, bool on) => new()
    {
        Margin = new(0, 3, 6, 0), Padding = new(6, 0, 6, 0), BorderThickness = new(1),
        BorderBrush = B(on ? "Accent" : "LineStrong"),
        Child = Txt(Upper(text), on ? "Accent" : "Dim", 10),
    };

    TextBlock Error(string text) => Txt(text, "Bad", wrap: true);
    TextBlock Empty(string text) => new() { Text = text, Foreground = B("Dim"), Padding = new(14), TextWrapping = TextWrapping.Wrap };

    ToggleButton Option(string label, bool chosen, Func<Task> act)
    {
        var b = new ToggleButton { Content = label, IsChecked = chosen, Style = (Style)FindResource("Option") };
        b.Click += (_, _) => _ = act();
        return b;
    }

    /// <summary>A limit cell: the meter and, under it, when it resets.</summary>
    FrameworkElement Limit(Row r)
    {
        var p = new StackPanel();
        p.Children.Add(Meter(r.Free));
        p.Children.Add(Txt(Countdown(r.Reset), "Dim", 12, margin: new(PctWidth + 10, 2, 0, 0)));
        return p;
    }

    /// <summary>A "Free" column cell: in the compact layout the meter is shorter and right-aligned.</summary>
    FrameworkElement Free(double free) => compact ? Meter(free, 44, right: true) : Meter(free);

    FrameworkElement Meter(double free, double barWidth = 84, bool right = false)
    {
        var tone = B(Tone(free));
        var p = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = right ? HorizontalAlignment.Right : HorizontalAlignment.Left };
        p.Children.Add(new TextBlock
        {
            Text = $"{R(free)}%", Foreground = tone, FontWeight = FontWeights.SemiBold, MinWidth = PctWidth,
            TextAlignment = TextAlignment.Right, Margin = new(0, 0, 10, 0),
        });
        var bar = new Bar(free, tone, barWidth) { VerticalAlignment = VerticalAlignment.Center };
        AutomationProperties.SetName(bar, T("freeAria", ("p", R(free))));
        p.Children.Add(bar);
        return p;
    }

    /// <summary>4ch in the panel: room for "100%".</summary>
    double PctWidth => pctWidth ??= new FormattedText("100%", CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
        new Typeface(FontFamily, FontStyles.Normal, FontWeights.SemiBold, FontStretches.Normal), 13, Brushes.White,
        VisualTreeHelper.GetDpi(this).PixelsPerDip).WidthIncludingTrailingWhitespace;

    public static string Countdown(DateTimeOffset? reset)
    {
        if (reset is not { } d) return "";
        var s = Math.Max(0, (d - DateTimeOffset.Now).TotalSeconds);
        int days = (int)(s / 86400), h = (int)(s % 86400 / 3600), m = (int)(s % 3600 / 60);
        var left = days > 0 ? $"{days}{T("d")} {h}{T("h")}" : h > 0 ? $"{h}{T("h")} {m}{T("min")}" : $"{m}{T("min")}";
        return T("resetsIn", ("left", left), ("when", d.ToLocalTime().ToString("ddd HH:mm", Culture)));
    }

    /// <summary>A wide table scrolls sideways in its frame, as `.scroll` does; the wheel still scrolls the page.</summary>
    UIElement Scrollable(UIElement table)
    {
        if (compact || table is not Grid) return table;
        var sv = new ScrollViewer
        {
            Content = table, HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            VerticalScrollBarVisibility = ScrollBarVisibility.Disabled, Focusable = false,
        };
        sv.PreviewMouseWheel += (_, e) =>
        {
            e.Handled = true;
            Scroller.RaiseEvent(new MouseWheelEventArgs(e.MouseDevice, e.Timestamp, e.Delta) { RoutedEvent = MouseWheelEvent });
        };
        return sv;
    }

    void Toast(string message)
    {
        if (string.IsNullOrEmpty(message)) return;
        ToastText.Text = message;
        ToastBox.BeginAnimation(OpacityProperty, new DoubleAnimation(1, TimeSpan.FromMilliseconds(150)));
        toastTimer.Stop();
        toastTimer.Start();
    }

    // ---- window ----

    protected override void OnClosing(CancelEventArgs e)
    {
        if (!Quitting)
        {
            e.Cancel = true;
            Hide();
        }
        base.OnClosing(e);
    }

    [DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int size);

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        // A dark title bar (Windows 10 20H1+), coloured like the page on Windows 11. Ignored where unsupported.
        var hwnd = new WindowInteropHelper(this).Handle;
        int dark = 1, caption = 0x000c0d0b, text = 0x00e8ece6;  // COLORREF is 0x00BBGGRR: #0b0d0c and #e6ece8
        DwmSetWindowAttribute(hwnd, 20, ref dark, sizeof(int));
        DwmSetWindowAttribute(hwnd, 35, ref caption, sizeof(int));
        DwmSetWindowAttribute(hwnd, 36, ref text, sizeof(int));
    }

    /// <summary>For `--snapshot`: the window content is exactly `width` wide and as tall as it needs.</summary>
    public void PrepareSnapshot(double width)
    {
        Scroller.VerticalScrollBarVisibility = ScrollBarVisibility.Hidden;
        UpdateLayout();
        Width = width + (ActualWidth - Root.ActualWidth);
        UpdateLayout();
    }

    public void SavePng(string path)
    {
        UpdateLayout();
        var at = Main.TranslatePoint(new Point(0, 0), Root);
        // DesiredSize, not ActualHeight: a short page is stretched to the window, a PNG should not be.
        double w = Root.ActualWidth, h = Math.Ceiling(at.Y - Main.Margin.Top + Main.DesiredSize.Height);
        var dpi = VisualTreeHelper.GetDpi(this);
        var visual = new DrawingVisual();
        using (var dc = visual.RenderOpen())
        {
            dc.DrawRectangle(B("Bg"), null, new Rect(0, 0, w, h));
            // The brush's coordinates already include Main's offset (its margin and centring) in the page.
            var brush = new VisualBrush(Main)
            {
                Stretch = Stretch.None, ViewboxUnits = BrushMappingMode.Absolute, Viewbox = new Rect(0, 0, w, h),
                AlignmentX = AlignmentX.Left, AlignmentY = AlignmentY.Top,
            };
            dc.DrawRectangle(brush, null, new Rect(0, 0, w, h));
        }
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(w * dpi.DpiScaleX), (int)Math.Ceiling(h * dpi.DpiScaleY),
            dpi.PixelsPerInchX, dpi.PixelsPerInchY, PixelFormats.Pbgra32);
        bitmap.Render(visual);
        var png = new PngBitmapEncoder();
        png.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = File.Create(path);
        png.Save(file);
    }
}

/// <summary>A table as a Grid: a background strip per row (rule, wash, click target) under padded cells.</summary>
sealed class Table
{
    readonly MainWindow w;
    int row = -1;
    bool body, clickable;

    public Grid Grid { get; } = new();
    public Thickness Pad { get; private set; }

    public Table(MainWindow w, params GridLength[] columns)
    {
        this.w = w;
        foreach (var c in columns) Grid.ColumnDefinitions.Add(new() { Width = c });
        Pad = w.CellPad;
    }

    public void Head(params string[] titles)
    {
        Grid.RowDefinitions.Add(new() { Height = GridLength.Auto });
        row++;
        Place(new Border { BorderBrush = w.B("LineStrong"), BorderThickness = new(0, 0, 0, 1) }, 0, Grid.ColumnDefinitions.Count);
        for (var i = 0; i < titles.Length; i++)
            Place(new Border { Padding = w.HeadPad, Child = w.Txt(titles[i].ToUpper(Strings.Culture), "Dim", 11) }, i, 1);
    }

    /// <summary>Starts a row. `rule`: the 1px line above it; `click`: the whole row is one button.</summary>
    public void Row(bool rule = true, Brush? wash = null, Action? click = null, string? name = null, Thickness? pad = null)
    {
        Grid.RowDefinitions.Add(new() { Height = GridLength.Auto });
        row++;
        var line = body && rule;
        body = true;
        var span = Grid.ColumnDefinitions.Count;
        Place(new Border { Background = wash, BorderBrush = w.B("Line"), BorderThickness = new(0, line ? 1 : 0, 0, 0) }, 0, span);
        clickable = click != null;
        if (click != null)
        {
            var b = new Button { Style = (Style)w.FindResource("RowButton"), Margin = new(0, line ? 1 : 0, 0, 0) };
            AutomationProperties.SetName(b, name);
            b.Click += (_, _) => click();
            Place(b, 0, span);
        }
        Pad = pad ?? w.CellPad;
    }

    public void Cell(FrameworkElement content, int col, int span = 1, Thickness? pad = null)
    {
        content.VerticalAlignment = VerticalAlignment.Top;
        // In a clickable row the clicks go through the cells to the row's button.
        Place(new Border { Padding = pad ?? Pad, Child = content, IsHitTestVisible = !clickable }, col, span);
    }

    void Place(UIElement e, int col, int span)
    {
        Grid.SetRow(e, row);
        Grid.SetColumn(e, col);
        Grid.SetColumnSpan(e, span);
        Grid.Children.Add(e);
    }
}

/// <summary>The thin segmented meter: cells of 7px with 1.4px gaps, filled up to the % free.</summary>
sealed class Bar(double free, Brush fill, double width) : FrameworkElement
{
    const double Period = 8.4, Cell = 7, Height_ = 6;
    static readonly Brush Track = Frozen(Color.FromRgb(0x1f, 0x25, 0x23));

    static Brush Frozen(Color c)
    {
        var b = new SolidColorBrush(c);
        b.Freeze();
        return b;
    }

    protected override Size MeasureOverride(Size available) => new(width, Height_);

    protected override void OnRender(DrawingContext dc)
    {
        var to = width * Math.Clamp(free, 0, 100) / 100;
        for (double x = 0; x < width; x += Period)
        {
            var cell = Math.Min(Cell, width - x);
            dc.DrawRectangle(Track, null, new Rect(x, 0, cell, Height_));
            var filled = Math.Clamp(to - x, 0, cell);
            if (filled > 0) dc.DrawRectangle(fill, null, new Rect(x, 0, filled, Height_));
        }
    }

    protected override System.Windows.Automation.Peers.AutomationPeer OnCreateAutomationPeer() =>
        new System.Windows.Automation.Peers.FrameworkElementAutomationPeer(this);
}
