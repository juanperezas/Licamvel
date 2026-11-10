using Licamvel.App.Services;
using Licamvel.App.ViewModels;
using Licamvel.App.Views;
using Microsoft.Extensions.Logging;

namespace Licamvel.App;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
                fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
            });

        // ---------------------------------------------------------- HttpClient + ApiService
        builder.Services.AddHttpClient<IApiService, ApiService>(client =>
        {
            client.BaseAddress = new Uri(GetBaseUrl());
            client.Timeout = TimeSpan.FromSeconds(30);
            client.DefaultRequestHeaders.Accept.Add(
                new System.Net.Http.Headers.MediaTypeWithQualityHeaderValue("application/json"));
        });

        // ---------------------------------------------------------- ViewModels
        builder.Services.AddTransient<LoginViewModel>();

        // ---------------------------------------------------------- Views
        builder.Services.AddTransient<LoginPage>();

#if DEBUG
        builder.Logging.AddDebug();
#endif

        return builder.Build();
    }

    /// <summary>
    /// Android emulador: 10.0.2.2 apunta al localhost de la PC anfitriona.
    /// Windows / otras plataformas: localhost.
    /// </summary>
    private static string GetBaseUrl() =>
        DeviceInfo.Platform == DevicePlatform.Android
            ? "http://10.0.2.2:8000"
            : "http://localhost:8000";
}