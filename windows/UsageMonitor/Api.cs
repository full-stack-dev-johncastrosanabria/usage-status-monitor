using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace UsageMonitor;

// The payload of the local server; see `to_json` in src/usage_monitor/snapshot.py.
sealed record Row(string Label, double Used, double Free, DateTimeOffset? Reset, string? Group, bool Blocking);
sealed record Usage(string? Plan, Row[]? Rows, double Score, string? Error);
sealed record Account(int N, string Email, bool Current, string? Plan, Row[]? Rows, double Score, string? Error);
sealed record Balance(string Currency, double Total, double Granted, double ToppedUp);
sealed record Credits(bool Available, Balance[]? Balances, string? Error);
sealed record Model(string Id, string Label, bool More);
sealed record Settings(string? Model, string? Effort, Model[]? Models, string[]? Efforts, string? Error);
sealed record Payload(
    DateTimeOffset Updated, Account[] Claude, Usage Codex, Usage Antigravity, Credits Deepseek, int? Best,
    double AlertAt, double Every, Settings? Settings, bool AutoSwitch, string Lang,
    Dictionary<string, string> Languages, bool Demo,
    Usage? Copilot = null,  // missing from servers older than 0.2
    Connect? Connect = null);
/// <summary>How the last "connect account" went: idle, waiting, connected, duplicate, cancelled or failed.</summary>
sealed record Connect(string Status, string? Email = null, int? Number = null, string? Error = null);

/// <summary>An error the server answered with; its message is already translated.</summary>
sealed class ApiException(string message) : Exception(message);

sealed class Api(int port)
{
    static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };

    // No proxy: the server only accepts requests whose Host is 127.0.0.1:<port>.
    // A refresh or a language change waits for every provider, hence the long timeout.
    readonly HttpClient http = new(new SocketsHttpHandler { UseProxy = false })
    {
        BaseAddress = new Uri($"http://127.0.0.1:{port}"),
        Timeout = TimeSpan.FromSeconds(90),
    };

    public int Port => port;

    public Task<Payload> Get() => Send(new HttpRequestMessage(HttpMethod.Get, "/api/data"));

    public Task<Payload> Post(string path, object body)
    {
        // StringContent, not JsonContent: the server reads Content-Length and would see a chunked body as empty.
        var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json"),
        };
        request.Headers.Add("X-Usage-Monitor", "1");  // required on writes, it rules out other websites
        return Send(request);
    }

    async Task<Payload> Send(HttpRequestMessage request)
    {
        using var response = await http.SendAsync(request);
        var text = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            using var doc = JsonDocument.Parse(text);
            var error = doc.RootElement.TryGetProperty("error", out var e) ? e.GetString() : null;
            throw new ApiException(error ?? response.ReasonPhrase ?? response.StatusCode.ToString());
        }
        return JsonSerializer.Deserialize<Payload>(text, Json) ?? throw new JsonException("empty answer");
    }
}

/// <summary>The `usage server` this app starts when nothing answers on the port.</summary>
static class Backend
{
    public static async Task<bool> Answers(int port)
    {
        using var client = new TcpClient();
        using var limit = new CancellationTokenSource(TimeSpan.FromMilliseconds(500));
        try
        {
            await client.ConnectAsync(IPAddress.Loopback, port, limit.Token);
            return true;
        }
        catch (Exception e) when (e is SocketException or OperationCanceledException)
        {
            return false;
        }
    }

    /// <summary>Next to this exe (a packaged build), then on the PATH, then where `uv tool install` puts it.</summary>
    public static string? Locate()
    {
        var path = (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries);
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return new[] { AppContext.BaseDirectory }.Concat(path).Append(Path.Combine(home, ".local", "bin"))
            .Select(dir => Path.Combine(dir.Trim('"'), "usage.exe"))
            .FirstOrDefault(File.Exists);
    }

    public static Process? Start(string exe, int port) =>
        Process.Start(new ProcessStartInfo(exe, $"server --port {port}") { UseShellExecute = false, CreateNoWindow = true });
}
