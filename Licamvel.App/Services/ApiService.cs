using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Licamvel.App.Models;

namespace Licamvel.App.Services;

/// <summary>Contrato del servicio; permite inyectar mocks en pruebas.</summary>
public interface IApiService
{
    Task<TokenResponse> LoginAsync(string correo, string password);
    Task<ClienteResponse> RegisterAsync(ClienteRegister cliente);
    Task<TokenResponse> LoginWithGoogleAsync(string googleIdToken);
    Task<List<Categoria>> GetCategoriasAsync();
    Task<List<Vela>> GetVelasAsync(int? categoriaId = null);
    Task<PedidoResponse> CrearPedidoAsync(PedidoCreate pedido);
    Task<bool> HasSessionAsync();
    void Logout();
}

public class ApiService : IApiService
{
    public const string TokenKey = "licamvel_jwt";

    private readonly HttpClient _http;

    // Pydantic v2 serializa Decimal como string ("12.50"): hay que permitir leerlo.
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never
    };

    public ApiService(HttpClient http)
    {
        _http = http;
    }

    // ------------------------------------------------------------ Auth
    public async Task<TokenResponse> LoginAsync(string correo, string password)
    {
        var body = new ClienteLogin { Correo = correo, Password = password };
        var token = await SendAsync<TokenResponse>(HttpMethod.Post, "/auth/login", body, requiresAuth: false);

        if (string.IsNullOrWhiteSpace(token.AccessToken))
            throw new ApiException("El servidor no devolvió un token válido.");

        try
        {
            await SecureStorage.Default.SetAsync(TokenKey, token.AccessToken);
        }
        catch (Exception ex)
        {
            throw new ApiException("No se pudo guardar la sesión de forma segura en el dispositivo.", null, ex);
        }

        return token;
    }

    public async Task<TokenResponse> LoginWithGoogleAsync(string googleIdToken)
        {
            var body = new GoogleLoginRequest { IdToken = googleIdToken };
            var token = await SendAsync<TokenResponse>(HttpMethod.Post, "/auth/google", body, requiresAuth: false);

            if (string.IsNullOrWhiteSpace(token.AccessToken))
                throw new ApiException("El servidor no devolvió un token de acceso válido.");

            try
            {
                await SecureStorage.Default.SetAsync(TokenKey, token.AccessToken);
            }
            catch (Exception ex)
            {
                throw new ApiException("No se pudo guardar la sesión de forma segura en el dispositivo.", null, ex);
            }

            return token;
        }
        
    public Task<ClienteResponse> RegisterAsync(ClienteRegister cliente) =>
        SendAsync<ClienteResponse>(HttpMethod.Post, "/auth/register", cliente, requiresAuth: false);

    public async Task<bool> HasSessionAsync()
    {
        var token = await GetTokenAsync();
        return !string.IsNullOrWhiteSpace(token);
    }

    public void Logout()
    {
        SecureStorage.Default.Remove(TokenKey);
    }

    // ------------------------------------------------------------ Catálogo
    public Task<List<Categoria>> GetCategoriasAsync() =>
        SendAsync<List<Categoria>>(HttpMethod.Get, "/categorias", null, requiresAuth: false);

    public Task<List<Vela>> GetVelasAsync(int? categoriaId = null)
    {
        var url = categoriaId.HasValue ? $"/velas?categoria_id={categoriaId.Value}" : "/velas";
        return SendAsync<List<Vela>>(HttpMethod.Get, url, null, requiresAuth: false);
    }

    // ------------------------------------------------------------ Pedidos
    public Task<PedidoResponse> CrearPedidoAsync(PedidoCreate pedido) =>
        SendAsync<PedidoResponse>(HttpMethod.Post, "/pedidos", pedido, requiresAuth: true);

    // ------------------------------------------------------------ Infraestructura HTTP
    private static async Task<string?> GetTokenAsync()
    {
        try
        {
            return await SecureStorage.Default.GetAsync(TokenKey);
        }
        catch
        {
            // SecureStorage puede fallar si el almacén del dispositivo se corrompió.
            return null;
        }
    }

    private async Task<T> SendAsync<T>(HttpMethod method, string url, object? body, bool requiresAuth)
    {
        using var request = new HttpRequestMessage(method, url);

        if (body is not null)
            request.Content = JsonContent.Create(body, body.GetType(), options: JsonOptions);

        if (requiresAuth)
        {
            var token = await GetTokenAsync();
            if (string.IsNullOrWhiteSpace(token))
                throw new ApiException("Tu sesión no está iniciada. Inicia sesión nuevamente.", 401);

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }

        try
        {
            using var response = await _http.SendAsync(request);

            if (!response.IsSuccessStatusCode)
            {
                var errorBody = await response.Content.ReadAsStringAsync();

                // Token vencido o inválido: limpiar la sesión local.
                if (requiresAuth && response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
                    Logout();

                throw new ApiException(
                    ExtractErrorMessage(errorBody, response),
                    (int)response.StatusCode);
            }

            var result = await response.Content.ReadFromJsonAsync<T>(JsonOptions);
            if (result is null)
                throw new ApiException("El servidor devolvió una respuesta vacía.", (int)response.StatusCode);

            return result;
        }
        catch (ApiException)
        {
            throw;
        }
        catch (TaskCanceledException ex)
        {
            throw new ApiException("El servidor tardó demasiado en responder. Intenta nuevamente.", null, ex);
        }
        catch (HttpRequestException ex)
        {
            throw new ApiException("No se pudo conectar con el servidor. Verifica tu conexión y que la API esté activa.", null, ex);
        }
        catch (JsonException ex)
        {
            throw new ApiException("La respuesta del servidor no tiene el formato esperado.", null, ex);
        }
    }

    /// <summary>
    /// FastAPI devuelve {"detail": "texto"} en errores HTTPException
    /// y {"detail": [ {loc, msg, ...} ]} en errores de validación (422).
    /// </summary>
    private static string ExtractErrorMessage(string body, HttpResponseMessage response)
    {
        var fallback = $"Error {(int)response.StatusCode}: {response.ReasonPhrase}";

        if (string.IsNullOrWhiteSpace(body))
            return fallback;

        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.ValueKind != JsonValueKind.Object ||
                !doc.RootElement.TryGetProperty("detail", out var detail))
                return fallback;

            if (detail.ValueKind == JsonValueKind.String)
                return detail.GetString() ?? fallback;

            if (detail.ValueKind == JsonValueKind.Array)
            {
                var messages = new List<string>();
                foreach (var item in detail.EnumerateArray())
                {
                    if (item.ValueKind != JsonValueKind.Object) continue;

                    var msg = item.TryGetProperty("msg", out var m) ? m.GetString() : null;
                    var field = string.Empty;

                    if (item.TryGetProperty("loc", out var loc) && loc.ValueKind == JsonValueKind.Array)
                    {
                        var last = loc.EnumerateArray().LastOrDefault();
                        field = last.ValueKind == JsonValueKind.String ? last.GetString() ?? "" : "";
                    }

                    if (!string.IsNullOrWhiteSpace(msg))
                        messages.Add(string.IsNullOrWhiteSpace(field) ? msg! : $"{field}: {msg}");
                }

                if (messages.Count > 0)
                    return string.Join(Environment.NewLine, messages);
            }
        }
        catch (JsonException)
        {
            // Cuerpo no JSON: se usa el mensaje por defecto.
        }

        return fallback;
    }
}