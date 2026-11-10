using System.Text.Json.Serialization;

namespace Licamvel.App.Models;

/// <summary>
/// Error controlado de la API (HTTP != 2xx, sin conexión, timeout, etc.).
/// El mensaje ya viene listo para mostrarse al usuario.
/// </summary>
public class ApiException : Exception
{
    public int? StatusCode { get; }

    public ApiException(string message, int? statusCode = null, Exception? inner = null)
        : base(message, inner)
    {
        StatusCode = statusCode;
    }
}

// ------------------------------------------------------------------ Auth / Cliente
public class ClienteRegister
{
    [JsonPropertyName("nombre_c")] public string NombreC { get; set; } = string.Empty;
    [JsonPropertyName("apellido_c")] public string ApellidoC { get; set; } = string.Empty;
    [JsonPropertyName("telefono")] public string? Telefono { get; set; }
    [JsonPropertyName("correo")] public string Correo { get; set; } = string.Empty;
    [JsonPropertyName("direccion")] public string? Direccion { get; set; }
    [JsonPropertyName("password")] public string Password { get; set; } = string.Empty;
}

public class ClienteLogin
{
    [JsonPropertyName("correo")] public string Correo { get; set; } = string.Empty;
    [JsonPropertyName("password")] public string Password { get; set; } = string.Empty;
}

public class TokenResponse
{
    [JsonPropertyName("access_token")] public string AccessToken { get; set; } = string.Empty;
    [JsonPropertyName("token_type")] public string TokenType { get; set; } = "bearer";
}

/// <summary>Respuesta de POST /auth/register (ClienteResponse en la API).</summary>
public class ClienteResponse
{
    [JsonPropertyName("ID_cliente")] public int IdCliente { get; set; }
    [JsonPropertyName("nombre_c")] public string NombreC { get; set; } = string.Empty;
    [JsonPropertyName("apellido_c")] public string ApellidoC { get; set; } = string.Empty;
    [JsonPropertyName("telefono")] public string? Telefono { get; set; }
    [JsonPropertyName("correo")] public string Correo { get; set; } = string.Empty;
    [JsonPropertyName("direccion")] public string? Direccion { get; set; }
}

// ------------------------------------------------------------------ Catálogo
public class Categoria
{
    [JsonPropertyName("ID_categoria")] public int IdCategoria { get; set; }
    [JsonPropertyName("nombre_categoria")] public string NombreCategoria { get; set; } = string.Empty;
    [JsonPropertyName("tiempo_entrega")] public int TiempoEntrega { get; set; }
}

public class Vela
{
    [JsonPropertyName("ID_vela")] public int IdVela { get; set; }
    [JsonPropertyName("nombre_vela")] public string NombreVela { get; set; } = string.Empty;
    [JsonPropertyName("precio_vela")] public decimal PrecioVela { get; set; }
    [JsonPropertyName("stock")] public int Stock { get; set; }
    [JsonPropertyName("ID_categoria")] public int IdCategoria { get; set; }
}

// ------------------------------------------------------------------ Pedidos
public class DetallePedidoCreate
{
    [JsonPropertyName("ID_vela")] public int IdVela { get; set; }
    [JsonPropertyName("cantidad_velas")] public int CantidadVelas { get; set; }
}

public class PedidoCreate
{
    [JsonPropertyName("metodo_pago")] public string MetodoPago { get; set; } = string.Empty;
    [JsonPropertyName("detalles")] public List<DetallePedidoCreate> Detalles { get; set; } = new();
}

public class DetallePedidoResponse
{
    [JsonPropertyName("ID_detalle")] public int IdDetalle { get; set; }
    [JsonPropertyName("ID_vela")] public int IdVela { get; set; }
    [JsonPropertyName("cantidad_velas")] public int CantidadVelas { get; set; }
    [JsonPropertyName("precio_unitario")] public decimal PrecioUnitario { get; set; }
}

public class PedidoResponse
{
    [JsonPropertyName("ID_pedido")] public int IdPedido { get; set; }
    [JsonPropertyName("fecha_pedido")] public DateTime FechaPedido { get; set; }
    [JsonPropertyName("metodo_pago")] public string MetodoPago { get; set; } = string.Empty;
    [JsonPropertyName("estado_pedido")] public string EstadoPedido { get; set; } = string.Empty;
    [JsonPropertyName("total")] public decimal Total { get; set; }
    [JsonPropertyName("ID_cliente")] public int IdCliente { get; set; }
    [JsonPropertyName("detalles")] public List<DetallePedidoResponse> Detalles { get; set; } = new();
}
public class GoogleLoginRequest
{
    [JsonPropertyName("id_token")]
    public string IdToken { get; set; } = string.Empty;
}
