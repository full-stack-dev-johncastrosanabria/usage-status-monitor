using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Threading;
using Forms = System.Windows.Forms;
using static UsageMonitor.Strings;

namespace UsageMonitor;

/// <summary>
/// Starts the local server if nothing answers, shows the panel and keeps a tray icon with the % free.
/// Hidden option: `--snapshot file.png [--width px]` renders the window once to a PNG and exits.
/// </summary>
partial class App : Application
{
    const int DefaultPort = 8787;  // the server's default (`port` in config.toml)
    MainWindow? window;
    Process? server;  // only when this app started it
    Forms.NotifyIcon? tray;
    readonly DispatcherTimer poll = new() { Interval = TimeSpan.FromSeconds(30) };

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        ShutdownMode = ShutdownMode.OnExplicitShutdown;
        // USAGE_MONITOR_PORT points at a server someone else runs (a demo, a test): never start one then.
        var env = Environment.GetEnvironmentVariable("USAGE_MONITOR_PORT");
        var port = int.TryParse(env, out var p) && p is > 0 and < 65536 ? p : DefaultPort;
        var api = new Api(port);

        if (Arg(e.Args, "--snapshot") is { } shot)
        {
            var width = double.TryParse(Arg(e.Args, "--width"), out var w) && w >= 320 ? w : 1240;
            Shutdown(await Snapshot(api, Path.GetFullPath(shot), width));
            return;
        }

        window = new MainWindow(api);
        window.Changed += UpdateTray;
        tray = new Forms.NotifyIcon { Icon = LoadIcon(), Text = "usage-monitor", Visible = true, ContextMenuStrip = new() };
        tray.MouseClick += (_, a) => { if (a.Button == Forms.MouseButtons.Left) Open(); };
        UpdateTray();
        window.Show();

        if (env == null && !await Backend.Answers(port)) await StartServer(port);
        await window.Load();
        poll.Tick += async (_, _) => await window.Load();
        poll.Start();
    }

    async Task StartServer(int port)
    {
        if (Backend.Locate() is not { } exe)
        {
            window!.Problem = "missing";
            return;
        }
        try
        {
            server = Backend.Start(exe, port);
        }
        catch (Win32Exception)
        {
            window!.Problem = "startFailed";
            return;
        }
        // It takes a moment to listen; the first load waits for it (up to ~15 s) instead of showing "offline".
        for (var i = 0; i < 60 && server is { HasExited: false } && !await Backend.Answers(port); i++)
            await Task.Delay(250);
    }

    static string? Arg(string[] args, string name)
    {
        var i = Array.IndexOf(args, name);
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
    }

    static async Task<int> Snapshot(Api api, string file, double width)
    {
        if (Missing() is { Length: > 0 } gaps)
        {
            Console.Error.WriteLine("missing translations: " + string.Join(", ", gaps));
            return 2;
        }
        var w = new MainWindow(api)
        {
            WindowStartupLocation = WindowStartupLocation.Manual, Left = -20000, Top = -20000, Height = 1400,
            ShowInTaskbar = false, ShowActivated = false, Quitting = true,
        };
        w.Show();
        w.PrepareSnapshot(width);
        var ok = await w.Load();
        if (ok) w.SavePng(file);
        w.Close();
        return ok ? 0 : 1;
    }

    void Open()
    {
        window!.Show();
        if (window.WindowState == WindowState.Minimized) window.WindowState = WindowState.Normal;
        window.Activate();
    }

    void UpdateTray()
    {
        if (tray is null || window is null) return;
        var d = window.Data;
        var cur = d?.Claude.FirstOrDefault(c => c.Current);
        var text = !window.Online ? $"usage-monitor · {T(window.Problem ?? "offline")}"
            : cur?.Error == null && cur != null ? $"usage-monitor · #{cur.N} · {T("freeAria", ("p", (int)Math.Round(cur.Score, MidpointRounding.AwayFromZero)))}"
            : "usage-monitor";
        tray.Text = text.Length > 127 ? text[..127] : text;  // the limit of a tray tooltip

        var menu = tray.ContextMenuStrip!;
        menu.Items.Clear();
        menu.Items.Add(T("trayOpen"), null, (_, _) => Open());
        menu.Items.Add(T("traySwitch"), null, (_, _) => _ = window.SwitchTo(null)).Enabled = window.Online && d?.Best != null;
        menu.Items.Add(T("trayRefresh"), null, (_, _) => _ = window.Refresh()).Enabled = window.Online;
        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add(T("trayQuit"), null, (_, _) => Quit());
    }

    static System.Drawing.Icon LoadIcon()
    {
        try
        {
            // assets/icon.ico, embedded by the project file when it exists
            if (GetResourceStream(new Uri("pack://application:,,,/icon.ico"))?.Stream is { } s)
                return new System.Drawing.Icon(s, Forms.SystemInformation.SmallIconSize);
        }
        catch (IOException)
        {
        }
        return System.Drawing.SystemIcons.Application;
    }

    void Quit()
    {
        if (window != null) window.Quitting = true;
        Shutdown();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        poll.Stop();
        tray?.Dispose();  // otherwise the icon lingers in the tray until the mouse passes over it
        try
        {
            if (server is { HasExited: false }) server.Kill(entireProcessTree: true);  // `usage.exe` launches Python
        }
        catch (Exception ex) when (ex is InvalidOperationException or Win32Exception)
        {
        }
        base.OnExit(e);
    }
}
